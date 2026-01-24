"""
PostgreSQL → Elasticsearch 데이터 마이그레이션 스크립트 (최적화 버전)
.
📌 최적화 사항:
  1. Keyset Pagination: OFFSET 대신 WHERE update_id > last_id 사용 (O(n) → O(1))
  2. 배치 크기 증가: 1,000 → 10,000
  3. DB 연결 재사용: 매 배치마다 연결/해제 → 단일 연결 유지
  4. 진행률 표시 개선: ETA 표시
"""

import psycopg2
import requests
import json
from datetime import datetime
import sys

# 설정
PG_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "logisflow",
    "user": "postgres",
    "password": "logisflow1234"
}

ES_URL = "http://localhost:9200"
ES_INDEX = "shipment-updates"
BATCH_SIZE = 10000  # 📌 1,000 → 10,000으로 증가


def get_pg_connection():
    """PostgreSQL 연결"""
    return psycopg2.connect(**PG_CONFIG)


def count_updates(conn):
    """전체 업데이트 수 확인 (연결 재사용)"""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM shipment_updates")
    count = cur.fetchone()[0]
    cur.close()
    return count


def fetch_updates_keyset(conn, last_id: int, limit: int):
    """📌 Keyset Pagination: OFFSET 대신 WHERE 조건 사용"""
    cur = conn.cursor()
    
    # OFFSET 대신 WHERE update_id > last_id 사용 (O(1) 성능)
    query = """
        SELECT update_id, shipment_id, status_code, notes, timestamp
        FROM shipment_updates
        WHERE update_id > %s
        ORDER BY update_id
        LIMIT %s
    """
    cur.execute(query, (last_id, limit))
    rows = cur.fetchall()
    cur.close()
    
    return rows


def bulk_index_to_es(docs: list):
    """Elasticsearch Bulk API로 인덱싱"""
    if not docs:
        return 0
    
    # Bulk API 형식으로 변환
    bulk_body = ""
    for doc in docs:
        action = {"index": {"_index": ES_INDEX, "_id": str(doc["update_id"])}}
        bulk_body += json.dumps(action) + "\n"
        bulk_body += json.dumps(doc) + "\n"
    
    try:
        resp = requests.post(
            f"{ES_URL}/_bulk",
            headers={"Content-Type": "application/x-ndjson"},
            data=bulk_body,
            timeout=60  # 📌 타임아웃 추가
        )
        
        if resp.status_code == 200:
            result = resp.json()
            if result.get("errors"):
                print(f"⚠️ 일부 문서 인덱싱 실패")
            return len(docs)
        else:
            print(f"❌ Bulk 인덱싱 실패: {resp.status_code}")
            return 0
    except Exception as e:
        print(f"❌ ES 오류: {e}")
        return 0


def format_time(seconds):
    """시간 포맷팅"""
    if seconds < 60:
        return f"{seconds:.0f}초"
    elif seconds < 3600:
        return f"{seconds // 60:.0f}분 {seconds % 60:.0f}초"
    else:
        return f"{seconds // 3600:.0f}시간 {(seconds % 3600) // 60:.0f}분"


def migrate():
    """메인 마이그레이션 함수 (최적화 버전)"""
    print("=" * 60)
    print("🔄 PostgreSQL → Elasticsearch 마이그레이션 (최적화)")
    print("=" * 60)
    
    # 📌 단일 DB 연결 유지
    conn = get_pg_connection()
    
    # 1. 전체 건수 확인
    total = count_updates(conn)
    print(f"\n📊 PostgreSQL shipment_updates: {total:,}건")
    
    if total == 0:
        print("❌ 마이그레이션할 데이터가 없습니다.")
        conn.close()
        return
    
    # 2. ES 인덱스 확인
    try:
        resp = requests.get(f"{ES_URL}/{ES_INDEX}")
        if resp.status_code != 200:
            print(f"❌ ES 인덱스 '{ES_INDEX}'가 없습니다. setup_elasticsearch.py를 먼저 실행하세요.")
            conn.close()
            return
    except:
        print("❌ Elasticsearch에 연결할 수 없습니다.")
        conn.close()
        return
    
    print(f"\n🚀 마이그레이션 시작 (배치 크기: {BATCH_SIZE:,})")
    print("   📌 최적화: Keyset Pagination + 대용량 배치")
    
    # 3. 배치 처리 (Keyset Pagination)
    migrated = 0
    last_id = 0  # 📌 OFFSET 대신 마지막 ID 추적
    start_time = datetime.now()
    
    while True:
        # 📌 Keyset Pagination으로 조회
        rows = fetch_updates_keyset(conn, last_id, BATCH_SIZE)
        
        if not rows:
            break
        
        # 마지막 ID 업데이트
        last_id = rows[-1][0]
        
        # 문서 변환
        docs = []
        for row in rows:
            update_id, shipment_id, status_code, notes, timestamp = row
            
            if isinstance(timestamp, datetime):
                ts_str = timestamp.isoformat()
            else:
                ts_str = str(timestamp)
            
            docs.append({
                "update_id": update_id,
                "shipment_id": shipment_id,
                "status_code": status_code,
                "notes": notes or "",
                "timestamp": ts_str
            })
        
        # ES로 인덱싱
        indexed = bulk_index_to_es(docs)
        migrated += indexed
        
        # 📌 ETA 계산 및 진행률 표시
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = migrated / elapsed if elapsed > 0 else 0
        remaining = total - migrated
        eta = remaining / rate if rate > 0 else 0
        progress = min(100, (migrated / total) * 100)
        
        print(f"\r  📦 {migrated:,}/{total:,} ({progress:.1f}%) | {rate:,.0f}건/초 | ETA: {format_time(eta)}", end="")
    
    # 4. 인덱스 새로고침
    print("\n\n  🔄 인덱스 새로고침 중...")
    requests.post(f"{ES_URL}/{ES_INDEX}/_refresh")
    
    # 5. 결과 확인
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # ES 문서 수 확인
    resp = requests.get(f"{ES_URL}/{ES_INDEX}/_count")
    es_count = resp.json().get("count", 0) if resp.status_code == 200 else 0
    
    # 📌 연결 종료
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ 마이그레이션 완료!")
    print("=" * 60)
    print(f"   PostgreSQL: {total:,}건")
    print(f"   Elasticsearch: {es_count:,}건")
    print(f"   소요 시간: {format_time(elapsed)}")
    print(f"   처리 속도: {migrated / elapsed:,.0f}건/초")
    print("\n다음 단계:")
    print("   python scripts/benchmark_q4.py")


if __name__ == "__main__":
    migrate()

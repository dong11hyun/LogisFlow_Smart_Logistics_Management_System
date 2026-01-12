"""
PostgreSQL → Elasticsearch 데이터 마이그레이션 스크립트

PostgreSQL의 shipment_updates 데이터를 Elasticsearch로 동기화
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
BATCH_SIZE = 1000  # 한 번에 처리할 건수


def get_pg_connection():
    """PostgreSQL 연결"""
    return psycopg2.connect(**PG_CONFIG)


def count_updates():
    """전체 업데이트 수 확인"""
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM shipment_updates")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


def fetch_updates(offset: int, limit: int):
    """PostgreSQL에서 업데이트 조회"""
    conn = get_pg_connection()
    cur = conn.cursor()
    
    query = """
        SELECT update_id, shipment_id, status_code, notes, timestamp
        FROM shipment_updates
        ORDER BY update_id
        OFFSET %s LIMIT %s
    """
    cur.execute(query, (offset, limit))
    rows = cur.fetchall()
    
    cur.close()
    conn.close()
    
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
            data=bulk_body
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


def migrate():
    """메인 마이그레이션 함수"""
    print("=" * 60)
    print("🔄 PostgreSQL → Elasticsearch 마이그레이션")
    print("=" * 60)
    
    # 1. 전체 건수 확인
    total = count_updates()
    print(f"\n📊 PostgreSQL shipment_updates: {total:,}건")
    
    if total == 0:
        print("❌ 마이그레이션할 데이터가 없습니다.")
        return
    
    # 2. ES 인덱스 확인
    try:
        resp = requests.get(f"{ES_URL}/{ES_INDEX}")
        if resp.status_code != 200:
            print(f"❌ ES 인덱스 '{ES_INDEX}'가 없습니다. setup_elasticsearch.py를 먼저 실행하세요.")
            return
    except:
        print("❌ Elasticsearch에 연결할 수 없습니다.")
        return
    
    print(f"\n🚀 마이그레이션 시작 (배치 크기: {BATCH_SIZE})")
    
    # 3. 배치 처리
    migrated = 0
    offset = 0
    start_time = datetime.now()
    
    while offset < total:
        # PostgreSQL에서 조회
        rows = fetch_updates(offset, BATCH_SIZE)
        
        if not rows:
            break
        
        # 문서 변환
        docs = []
        for row in rows:
            update_id, shipment_id, status_code, notes, timestamp = row
            
            # timestamp를 ISO 형식으로 변환
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
        offset += BATCH_SIZE
        
        # 진행률 표시
        progress = min(100, (offset / total) * 100)
        print(f"  📦 진행: {migrated:,}/{total:,} ({progress:.1f}%)")
    
    # 4. 인덱스 새로고침
    requests.post(f"{ES_URL}/{ES_INDEX}/_refresh")
    
    # 5. 결과 확인
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # ES 문서 수 확인
    resp = requests.get(f"{ES_URL}/{ES_INDEX}/_count")
    es_count = resp.json().get("count", 0) if resp.status_code == 200 else 0
    
    print("\n" + "=" * 60)
    print("✅ 마이그레이션 완료!")
    print("=" * 60)
    print(f"   PostgreSQL: {total:,}건")
    print(f"   Elasticsearch: {es_count:,}건")
    print(f"   소요 시간: {elapsed:.2f}초")
    print(f"   처리 속도: {migrated / elapsed:.0f}건/초")
    print("\n다음 단계:")
    print("   python scripts/benchmark_q4.py")


if __name__ == "__main__":
    migrate()

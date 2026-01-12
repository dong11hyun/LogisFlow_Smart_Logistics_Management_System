"""
Elasticsearch 인덱스 초기화 스크립트

사용법:
1. Elasticsearch가 실행 중인지 확인: docker ps | findstr elasticsearch
2. 스크립트 실행: python scripts/setup_elasticsearch.py
"""

import requests
import json
import sys

ES_URL = "http://localhost:9200"
INDEX_NAME = "shipment-updates"


def check_es_connection():
    """Elasticsearch 연결 확인"""
    try:
        resp = requests.get(ES_URL)
        if resp.status_code == 200:
            info = resp.json()
            print(f"✅ Elasticsearch 연결 성공!")
            print(f"   버전: {info.get('version', {}).get('number', 'unknown')}")
            print(f"   클러스터: {info.get('cluster_name', 'unknown')}")
            return True
        else:
            print(f"❌ Elasticsearch 응답 오류: {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Elasticsearch에 연결할 수 없습니다.")
        print("   Docker에서 Elasticsearch가 실행 중인지 확인하세요:")
        print("   docker ps | findstr elasticsearch")
        return False


def delete_index():
    """기존 인덱스 삭제"""
    try:
        resp = requests.delete(f"{ES_URL}/{INDEX_NAME}")
        if resp.status_code == 200:
            print(f"🗑️ 기존 인덱스 '{INDEX_NAME}' 삭제됨")
        elif resp.status_code == 404:
            print(f"ℹ️ 인덱스 '{INDEX_NAME}'가 존재하지 않음 (신규 생성 예정)")
        else:
            print(f"⚠️ 인덱스 삭제 실패: {resp.text}")
    except Exception as e:
        print(f"⚠️ 인덱스 삭제 중 오류: {e}")


def create_index():
    """인덱스 생성 (매핑 포함)"""
    mapping = {
        "settings": {
            "number_of_shards": 3,
            "number_of_replicas": 0,
            "refresh_interval": "1s"
        },
        "mappings": {
            "properties": {
                "update_id": {"type": "long"},
                "shipment_id": {"type": "integer"},
                "status_code": {"type": "keyword"},
                "notes": {"type": "text"},
                "timestamp": {
                    "type": "date",
                    "format": "yyyy-MM-dd'T'HH:mm:ss.SSSSSS||yyyy-MM-dd'T'HH:mm:ss||epoch_millis"
                }
            }
        }
    }
    
    try:
        resp = requests.put(
            f"{ES_URL}/{INDEX_NAME}",
            headers={"Content-Type": "application/json"},
            json=mapping
        )
        
        if resp.status_code in [200, 201]:
            print(f"✅ 인덱스 '{INDEX_NAME}' 생성 완료!")
            print(f"   샤드: 3개")
            print(f"   레플리카: 0개")
            return True
        else:
            print(f"❌ 인덱스 생성 실패: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ 인덱스 생성 중 오류: {e}")
        return False


def verify_index():
    """인덱스 확인"""
    try:
        resp = requests.get(f"{ES_URL}/{INDEX_NAME}")
        if resp.status_code == 200:
            print(f"✅ 인덱스 확인 완료!")
            
            # 문서 수 확인
            count_resp = requests.get(f"{ES_URL}/{INDEX_NAME}/_count")
            if count_resp.status_code == 200:
                count = count_resp.json().get("count", 0)
                print(f"   현재 문서 수: {count:,}개")
            return True
        else:
            print(f"❌ 인덱스 확인 실패: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 인덱스 확인 중 오류: {e}")
        return False


def insert_test_data():
    """테스트 데이터 삽입"""
    from datetime import datetime, timedelta
    
    test_data = [
        {
            "update_id": 1,
            "shipment_id": 1,
            "status_code": "PENDING",
            "notes": "주문 접수됨",
            "timestamp": (datetime.now() - timedelta(days=3)).isoformat()
        },
        {
            "update_id": 2,
            "shipment_id": 1,
            "status_code": "PICKED_UP",
            "notes": "집화 완료",
            "timestamp": (datetime.now() - timedelta(days=2)).isoformat()
        },
        {
            "update_id": 3,
            "shipment_id": 1,
            "status_code": "DELIVERED",
            "notes": "배송 완료",
            "timestamp": (datetime.now() - timedelta(days=1)).isoformat()
        },
        {
            "update_id": 4,
            "shipment_id": 2,
            "status_code": "PENDING",
            "notes": "주문 접수됨",
            "timestamp": (datetime.now() - timedelta(hours=12)).isoformat()
        },
        {
            "update_id": 5,
            "shipment_id": 2,
            "status_code": "IN_TRANSIT",
            "notes": "배송 중",
            "timestamp": (datetime.now() - timedelta(hours=6)).isoformat()
        }
    ]
    
    success_count = 0
    for doc in test_data:
        try:
            resp = requests.post(
                f"{ES_URL}/{INDEX_NAME}/_doc/{doc['update_id']}",
                headers={"Content-Type": "application/json"},
                json=doc
            )
            if resp.status_code in [200, 201]:
                success_count += 1
        except Exception as e:
            print(f"⚠️ 문서 삽입 실패: {e}")
    
    print(f"✅ 테스트 데이터 {success_count}/{len(test_data)}개 삽입 완료")
    
    # 인덱스 새로고침 (즉시 검색 가능하도록)
    requests.post(f"{ES_URL}/{INDEX_NAME}/_refresh")


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 LogisFlow Elasticsearch 인덱스 설정")
    print("=" * 60)
    
    # 1. 연결 확인
    if not check_es_connection():
        sys.exit(1)
    
    print()
    
    # 2. 기존 인덱스 삭제
    delete_index()
    
    # 3. 새 인덱스 생성
    if not create_index():
        sys.exit(1)
    
    print()
    
    # 4. 테스트 데이터 삽입
    insert_test_data()
    
    print()
    
    # 5. 인덱스 확인
    verify_index()
    
    print()
    print("=" * 60)
    print("✅ Elasticsearch 설정 완료!")
    print("=" * 60)
    print("\n다음 단계:")
    print("1. 서버 재시작: uvicorn app.main:app --reload --port 8000")
    print("2. API 테스트: curl http://localhost:8000/shipments/1/timeline?source=elasticsearch")
    print("3. 벤치마크: python scripts/benchmark_q4.py")

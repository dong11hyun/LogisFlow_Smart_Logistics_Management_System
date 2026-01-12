# =============================================================================
# LogisFlow Elasticsearch Client
# =============================================================================
# Q4 방안 2: Elasticsearch 조회 최적화

from elasticsearch import Elasticsearch, AsyncElasticsearch
from app.config import get_settings
from typing import List, Dict, Any, Optional
from datetime import datetime

settings = get_settings()

# 동기 클라이언트 (일반 조회용)
_es_client: Optional[Elasticsearch] = None

# 비동기 클라이언트 (FastAPI 비동기 엔드포인트용)
_async_es_client: Optional[AsyncElasticsearch] = None


def get_es_client() -> Elasticsearch:
    """Elasticsearch 동기 클라이언트 반환"""
    global _es_client
    if _es_client is None:
        _es_client = Elasticsearch(settings.ELASTICSEARCH_URL)
    return _es_client


async def get_async_es_client() -> AsyncElasticsearch:
    """Elasticsearch 비동기 클라이언트 반환"""
    global _async_es_client
    if _async_es_client is None:
        _async_es_client = AsyncElasticsearch(settings.ELASTICSEARCH_URL)
    return _async_es_client


async def close_es_client():
    """앱 종료 시 ES 클라이언트 연결 해제"""
    global _es_client, _async_es_client
    if _es_client:
        _es_client.close()
        _es_client = None
    if _async_es_client:
        await _async_es_client.close()
        _async_es_client = None


async def get_timeline_from_es(shipment_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Elasticsearch에서 화물 타임라인 조회 (비동기)
    
    Q4 방안 2: ES 조회 최적화
    - 인덱스: shipment-updates
    - 정렬: timestamp DESC
    """
    es = await get_async_es_client()
    
    query = {
        "query": {
            "term": {
                "shipment_id": shipment_id
            }
        },
        "sort": [
            {"timestamp": {"order": "desc"}}
        ],
        "size": limit
    }
    
    try:
        result = await es.search(
            index=settings.ELASTICSEARCH_INDEX,
            body=query
        )
        
        hits = result.get("hits", {}).get("hits", [])
        timeline = []
        
        for hit in hits:
            source = hit["_source"]
            timeline.append({
                "update_id": source.get("update_id", 0),
                "status_code": source.get("status_code"),
                "notes": source.get("notes"),
                "timestamp": source.get("timestamp")
            })
        
        return timeline
        
    except Exception as e:
        print(f"❌ [ES Error] Failed to query timeline: {e}")
        return []


def get_timeline_from_es_sync(shipment_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Elasticsearch에서 화물 타임라인 조회 (동기)
    
    동기 함수(get_timeline)에서 호출용
    """
    es = get_es_client()
    
    query = {
        "query": {
            "term": {
                "shipment_id": shipment_id
            }
        },
        "sort": [
            {"timestamp": {"order": "desc"}}
        ],
        "size": limit
    }
    
    try:
        result = es.search(
            index=settings.ELASTICSEARCH_INDEX,
            body=query
        )
        
        hits = result.get("hits", {}).get("hits", [])
        timeline = []
        
        for hit in hits:
            source = hit["_source"]
            timeline.append({
                "update_id": source.get("update_id", 0),
                "status_code": source.get("status_code"),
                "notes": source.get("notes"),
                "timestamp": source.get("timestamp")
            })
        
        return timeline
        
    except Exception as e:
        print(f"❌ [ES Error] Failed to query timeline (sync): {e}")
        return []


async def index_status_update(
    update_id: int,
    shipment_id: int,
    status_code: str,
    notes: str,
    timestamp: str
) -> bool:
    """
    상태 업데이트를 Elasticsearch에 인덱싱
    
    Kafka Consumer에서 호출하여 ES 동기화
    """
    es = await get_async_es_client()
    
    doc = {
        "update_id": update_id,
        "shipment_id": shipment_id,
        "status_code": status_code,
        "notes": notes,
        "timestamp": timestamp
    }
    
    try:
        await es.index(
            index=settings.ELASTICSEARCH_INDEX,
            id=str(update_id),  # update_id를 문서 ID로 사용
            body=doc
        )
        return True
    except Exception as e:
        print(f"❌ [ES Error] Failed to index update: {e}")
        return False


async def check_es_connection() -> bool:
    """Elasticsearch 연결 확인"""
    try:
        es = await get_async_es_client()
        return await es.ping()
    except Exception:
        return False

# =============================================================================
# LogisFlow Kafka Producer (Async Strategy)
# =============================================================================

from aiokafka import AIOKafkaProducer
import json
import asyncio
from app.config import get_settings

settings = get_settings()

# 전역 Producer 인스턴스
producer = None

async def get_kafka_producer():
    """Kafka Producer 싱글톤 반환 및 연결"""
    global producer
    if producer is None:
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await producer.start()
    return producer

async def close_kafka_producer():
    """앱 종료 시 연결 해제"""
    global producer
    if producer:
        await producer.stop()
        producer = None

async def send_status_update(shipment_id: int, status_code: str, timestamp: str):
    """
    Q3 전략 3: 비동기 메시지 발행
    
    API는 DB에 로그만 INSERT하고, 이 함수를 통해 Kafka로 이벤트를 쏘고 끝냄.
    Consumer가 나중에 이 메시지를 받아 shipments 테이블을 업데이트함.
    """
    producer = await get_kafka_producer()
    
    message = {
        "shipment_id": shipment_id,
        "status_code": status_code,
        "timestamp": timestamp,
        "event_type": "STATUS_UPDATE"
    }
    
    # Fire-and-Forget (기다리지 않음) 또는 await (메시지 전송 보장)
    # 여기서는 빠른 응답을 위해 await하지만, Consumer 처리는 기다리지 않음
    await producer.send_and_wait(
        settings.KAFKA_TOPIC_STATUS_UPDATES,
        message
    )

# =============================================================================
# LogisFlow Kafka Consumer (Async Strategy)
# =============================================================================

from aiokafka import AIOKafkaConsumer
import json
import asyncio
from sqlalchemy.orm import Session
from app.config import get_settings
from app.database import SessionLocal
from app.models import Shipment
from datetime import datetime

settings = get_settings()

async def consume_status_updates():
    """
    Q3 전략 3: Kafka Consumer
    
    1. Kafka 토픽("shipment-status-updates") 구독
    2. 메시지 수신 (shipment_id, status 등)
    3. shipments 테이블 current_status 업데이트 (비동기 처리)
    """
    # value_deserializer를 제거하고 루프 안에서 직접 파싱 (에러 핸들링을 위해)
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_STATUS_UPDATES,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="logisflow-backend-group",
        auto_offset_reset="earliest"
    )
    
    await consumer.start()
    print("🚀 [Kafka Consumer] Started consuming messages...")
    
    try:
        async for msg in consumer:
            try:
                # 1. 메시지 디코딩 & JSON 파싱
                value_str = msg.value.decode('utf-8')
                if not value_str:
                    continue
                    
                data = json.loads(value_str)
                print(f"📩 [Kafka] Received: {data}")
                
                # 2. DB 업데이트 로직
                await process_message(data)
                
            except json.JSONDecodeError:
                print(f"⚠️ [Kafka Skip] Invalid JSON: {msg.value}")
            except Exception as e:
                print(f"❌ [Kafka Skip] Error processing message: {e}")
            
    except Exception as e:
        print(f"❌ [Kafka Consumer Crash] Fatal Error: {e}")
    finally:
        await consumer.stop()

async def process_message(data):
    """메시지 처리 및 DB 업데이트"""
    db: Session = SessionLocal()
    try:
        shipment_id = data["shipment_id"]
        status_code = data["status_code"]
        timestamp_str = data["timestamp"]
        
        # ISO 포맷 문자열 -> datetime 객체
        timestamp = datetime.fromisoformat(timestamp_str)
        
        # 화물 조회
        shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
        
        if shipment:
            # 상태 업데이트 (비정규화 컬럼 동기화)
            shipment.current_status = status_code
            shipment.last_updated_at = timestamp
            
            db.commit()
            print(f"✅ [DB Updated] Shipment {shipment_id} -> {status_code}")
        else:
            print(f"⚠️ [DB Skip] Shipment {shipment_id} not found")
            
    except Exception as e:
        print(f"❌ [Process Error] {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # 단독 실행 모드 (테스트용)
    asyncio.run(consume_status_updates())

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
    """메시지 처리 및 DB 업데이트 + Elasticsearch 동기화"""
    from app.models import ShipmentUpdate  # 여기서 import (순환 참조 방지)
    
    db: Session = SessionLocal()
    update_id = None
    
    try:
        shipment_id = data["shipment_id"]
        status_code = data["status_code"]
        timestamp_str = data["timestamp"]
        event_type = data.get("event_type", "STATUS_UPDATE")
        notes = data.get("notes", "")
        
        # ISO 포맷 문자열 -> datetime 객체
        timestamp = datetime.fromisoformat(timestamp_str)
        
        # 화물 조회
        shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
        
        if not shipment:
            print(f"⚠️ [DB Skip] Shipment {shipment_id} not found")
            return
        
        if event_type == "INSERT_AND_UPDATE":
            # async_pure 전략: INSERT + UPDATE 모두 처리
            
            # 1. shipment_updates에 INSERT
            new_update = ShipmentUpdate(
                shipment_id=shipment_id,
                status_code=status_code,
                notes=notes,
                timestamp=timestamp
            )
            db.add(new_update)
            db.flush()  # update_id 생성
            update_id = new_update.update_id
            
            # 2. shipments 테이블 UPDATE
            shipment.current_status = status_code
            shipment.last_updated_at = timestamp
            
            db.commit()
            print(f"✅ [DB INSERT+UPDATE] Shipment {shipment_id} -> {status_code}")
            
        else:
            # 기존 async 전략: UPDATE만 (INSERT는 API에서 이미 처리됨)
            shipment.current_status = status_code
            shipment.last_updated_at = timestamp
            
            db.commit()
            print(f"✅ [DB Updated] Shipment {shipment_id} -> {status_code}")
        
        # =================================================================
        # Elasticsearch 동기화 (Q4 방안 2)
        # =================================================================
        try:
            from app.elasticsearch_client import index_status_update
            
            # update_id가 없으면 (기존 async 전략) 0 사용
            if update_id is None:
                update_id = 0
            
            await index_status_update(
                update_id=update_id,
                shipment_id=shipment_id,
                status_code=status_code,
                notes=notes,
                timestamp=timestamp_str
            )
            print(f"✅ [ES Indexed] Shipment {shipment_id} -> {status_code}")
            
        except Exception as es_error:
            # ES 실패해도 DB는 이미 성공했으므로 계속 진행
            print(f"⚠️ [ES Sync Failed] {es_error}")
            
    except Exception as e:
        print(f"❌ [Process Error] {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # 단독 실행 모드 (테스트용)
    asyncio.run(consume_status_updates())

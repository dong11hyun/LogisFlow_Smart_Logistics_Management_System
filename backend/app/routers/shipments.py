# =============================================================================
# LogisFlow Shipments Router
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
import time

from app.database import get_db
from app.models import Shipment, ShipmentUpdate
from app.schemas import (
    ShipmentResponse, 
    ShipmentListResponse,
    StatusUpdateRequest,
    StatusUpdateResponse,
    TimelineResponse,
    TimelineEntry
)

router = APIRouter(prefix="/shipments", tags=["Shipments"])


# =============================================================================
# 화물 목록 조회
# =============================================================================

@router.get("", response_model=ShipmentListResponse)
def get_shipments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    화물 목록 조회
    
    - skip: 건너뛸 개수
    - limit: 조회 개수 (최대 100)
    - status: 상태 필터 (선택)
    """
    query = db.query(Shipment)
    
    if status:
        query = query.filter(Shipment.current_status == status)
    
    total = query.count()
    items = query.order_by(desc(Shipment.created_at)).offset(skip).limit(limit).all()
    
    return ShipmentListResponse(total=total, items=items)


# =============================================================================
# 화물 상세 조회
# =============================================================================

@router.get("/{shipment_id}", response_model=ShipmentResponse)
def get_shipment(shipment_id: int, db: Session = Depends(get_db)):
    """
    화물 상세 조회
    
    비정규화된 컬럼 덕분에 JOIN 없이 바로 조회!
    """
    shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
    
    if not shipment:
        raise HTTPException(status_code=404, detail="화물을 찾을 수 없습니다")
    
    return shipment


# =============================================================================
# 상태 변경 API (Q3 테스트용!) ⭐
# =============================================================================

@router.post("/{shipment_id}/status", response_model=StatusUpdateResponse)
async def update_status(
    shipment_id: int,
    request: StatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    화물 상태 변경 (Q3 정합성 전략 테스트용)
    
    📌 strategy 옵션:
    - "sync": 동기 트랜잭션 (전략 1)
    - "trigger": DB 트리거 (전략 2) - TODO
    - "async": Kafka 비동기 (전략 3) - TODO
    
    현재는 sync 전략만 구현됨
    """
    start_time = time.time()
    
    # 화물 존재 확인
    shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="화물을 찾을 수 없습니다")
    
    strategy = request.strategy or "sync"
    
    if strategy == "sync":
        # =====================================================
        # 전략 1: 동기 트랜잭션
        # 하나의 트랜잭션에서 INSERT + UPDATE 모두 수행
        # =====================================================
        
        # 1. 상태 로그 INSERT
        new_update = ShipmentUpdate(
            shipment_id=shipment_id,
            status_code=request.status_code.value,
            notes=request.notes
        )
        db.add(new_update)
        
        # 2. 화물 상태 UPDATE (비정규화 컬럼 동기화)
        shipment.current_status = request.status_code.value
        shipment.last_updated_at = new_update.timestamp
        
        # 3. 커밋 (하나의 트랜잭션)
        db.commit()
        db.refresh(new_update)
        
    elif strategy == "trigger":
        # =====================================================
        # 전략 2: DB 트리거
        # INSERT만 수행하면 트리거가 알아서 shipments 테이블 업데이트
        # =====================================================
        
        # 1. 상태 로그 INSERT (이것만 하면 됨!)
        new_update = ShipmentUpdate(
            shipment_id=shipment_id,
            status_code=request.status_code.value,
            notes=request.notes
        )
        db.add(new_update)
        
        # 2. 커밋
        db.commit()
        db.refresh(new_update)
        
        # 주의: 여기서는 shipment.current_status가 아직 갱신되지 않았을 수 있음 (DB 사이드 효과)
        # 하지만 트리거는 동일 트랜잭션 내에서 실행되므로, 커밋 후 조회하면 반영되어 있음

        
    elif strategy == "async":
        # =====================================================
        # 전략 3: Kafka 비동기 (DB INSERT + Kafka)
        # 1. 상태 로그 INSERT (DB) - 여전히 동기 대기
        # 2. Kafka 메시지 발행 (이벤트)
        # 3. shipments 테이블 업데이트는 Consumer가 나중에 처리
        # =====================================================
        from app.kafka_producer import send_status_update
        from datetime import datetime
        
        # 1. 상태 로그 INSERT
        new_update = ShipmentUpdate(
            shipment_id=shipment_id,
            status_code=request.status_code.value,
            notes=request.notes
        )
        db.add(new_update)
        db.commit()
        db.refresh(new_update)
        
        # 2. Kafka 메시지 발행
        # timestamp는 JSON 직렬화를 위해 문자열로 변환
        await send_status_update(
            shipment_id=shipment_id,
            status_code=request.status_code.value,
            timestamp=new_update.timestamp.isoformat()
        )
        
        # 주의: shipments 테이블은 아직 업데이트되지 않음! (Eventual Consistency)

    elif strategy == "async_pure":
        # =====================================================
        # 전략 4: 완전 비동기 (Kafka ONLY)
        # DB 작업 없이 Kafka로만 메시지 발행!
        # Consumer가 INSERT + UPDATE 모두 처리
        # =====================================================
        from app.kafka_producer import send_status_update_pure
        from datetime import datetime
        
        current_timestamp = datetime.now()
        notes_value = request.notes or ""
        
        # Kafka로만 발행 (DB 대기 없음!)
        await send_status_update_pure(
            shipment_id=shipment_id,
            status_code=request.status_code.value,
            notes=notes_value,
            timestamp=current_timestamp.isoformat()
        )
        
        # 가짜 응답 객체 생성 (실제 ID는 Consumer에서 생성됨)
        class FakeUpdate:
            pass
        
        new_update = FakeUpdate()
        new_update.update_id = 0  # 임시 ID
        new_update.shipment_id = shipment_id
        new_update.status_code = request.status_code.value
        new_update.notes = notes_value
        new_update.timestamp = current_timestamp

    elif strategy == "async_fire":
        # =====================================================
        # 전략 5: 완전 Fire-and-Forget (SELECT 쿼리도 없음!)
        # DB 작업 완전 제거, 오직 Kafka 전송만!
        # 가장 빠른 응답 속도 (실제 비동기 효과 측정용)
        # =====================================================
        from app.kafka_producer import send_status_update_pure
        from datetime import datetime
        
        current_timestamp = datetime.now()
        notes_value = request.notes or ""
        
        # Kafka로만 발행 (SELECT/INSERT 없음!)
        await send_status_update_pure(
            shipment_id=shipment_id,
            status_code=request.status_code.value,
            notes=notes_value,
            timestamp=current_timestamp.isoformat()
        )
        
        # 가짜 응답 객체 생성
        class FakeUpdate:
            pass
        
        new_update = FakeUpdate()
        new_update.update_id = 0
        new_update.shipment_id = shipment_id
        new_update.status_code = request.status_code.value
        new_update.notes = notes_value
        new_update.timestamp = current_timestamp
        
        # shipment 변수가 없으므로 여기서 바로 응답 반환
        processing_time = (time.time() - start_time) * 1000
        return StatusUpdateResponse(
            update_id=new_update.update_id,
            shipment_id=new_update.shipment_id,
            status_code=new_update.status_code,
            notes=new_update.notes,
            timestamp=new_update.timestamp,
            processing_time_ms=round(processing_time, 2),
            strategy_used=strategy
        )
        
    else:
        raise HTTPException(status_code=400, detail=f"알 수 없는 전략: {strategy}")
    
    processing_time = (time.time() - start_time) * 1000  # ms
    
    return StatusUpdateResponse(
        update_id=new_update.update_id,
        shipment_id=new_update.shipment_id,
        status_code=new_update.status_code,
        notes=new_update.notes,
        timestamp=new_update.timestamp,
        processing_time_ms=round(processing_time, 2),
        strategy_used=strategy
    )


# =============================================================================
# 타임라인 조회 API (Q4 테스트용!) ⭐
# =============================================================================

@router.get("/{shipment_id}/timeline", response_model=TimelineResponse)
def get_timeline(
    shipment_id: int,
    source: str = Query("postgresql", description="데이터 소스: postgresql 또는 elasticsearch"),
    db: Session = Depends(get_db)
):
    """
    화물 상태 변경 타임라인 조회 (Q4 저장소 비교 테스트용)
    
    📌 source 옵션:
    - "postgresql": PostgreSQL 파티션 테이블에서 조회 (방안 1)
    - "elasticsearch": Elasticsearch에서 조회 (방안 2) - TODO
    """
    start_time = time.time()
    
    # 화물 존재 확인
    shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="화물을 찾을 수 없습니다")
    
    if source == "postgresql":
        # =====================================================
        # 방안 1: PostgreSQL 파티션 테이블에서 조회
        # =====================================================
        updates = db.query(ShipmentUpdate)\
            .filter(ShipmentUpdate.shipment_id == shipment_id)\
            .order_by(desc(ShipmentUpdate.timestamp))\
            .all()
        
        timeline = [
            TimelineEntry(
                update_id=u.update_id,
                status_code=u.status_code,
                notes=u.notes,
                timestamp=u.timestamp
            )
            for u in updates
        ]
        
    elif source == "elasticsearch":
        # 방안 2: Elasticsearch (5단계에서 구현 예정)
        raise HTTPException(status_code=501, detail="Elasticsearch 조회는 아직 구현되지 않았습니다")
        
    else:
        raise HTTPException(status_code=400, detail=f"알 수 없는 소스: {source}")
    
    query_time = (time.time() - start_time) * 1000  # ms
    
    return TimelineResponse(
        shipment_id=shipment_id,
        current_status=shipment.current_status,
        timeline=timeline,
        total_updates=len(timeline),
        query_time_ms=round(query_time, 2),
        source=source
    )

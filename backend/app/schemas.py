# =============================================================================
# LogisFlow Pydantic Schemas (API 요청/응답)
# =============================================================================

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class StatusCode(str, Enum):
    """상태 코드 Enum"""
    PENDING = "PENDING"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_DELIVERY = "OUT_DELIVERY"
    DELIVERED = "DELIVERED"
    RETURNED = "RETURNED"


# =============================================================================
# Shipment Schemas
# =============================================================================

class ShipmentBase(BaseModel):
    """화물 기본 스키마"""
    company_id: int
    origin_warehouse_id: int
    destination_warehouse_id: int


class ShipmentCreate(ShipmentBase):
    """화물 생성 요청"""
    pass


class ShipmentResponse(ShipmentBase):
    """화물 응답"""
    shipment_id: int
    created_at: datetime
    current_status: str
    last_updated_at: datetime
    origin_warehouse_name: Optional[str] = None
    destination_warehouse_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class ShipmentListResponse(BaseModel):
    """화물 목록 응답"""
    total: int
    items: List[ShipmentResponse]


# =============================================================================
# Status Update Schemas
# =============================================================================

class StatusUpdateRequest(BaseModel):
    """상태 변경 요청 (Q3 테스트용)"""
    status_code: StatusCode
    notes: Optional[str] = Field(None, max_length=255)
    
    # Q3 전략 선택 옵션
    strategy: Optional[str] = Field(
        default="sync",
        description="정합성 전략: sync(동기), trigger(트리거), async(비동기)"
    )


class StatusUpdateResponse(BaseModel):
    """상태 변경 응답"""
    update_id: int
    shipment_id: int
    status_code: str
    notes: Optional[str]
    timestamp: datetime
    
    # 성능 측정용
    processing_time_ms: Optional[float] = None
    strategy_used: Optional[str] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# Timeline Schemas (Q4 테스트용)
# =============================================================================

class TimelineEntry(BaseModel):
    """타임라인 항목"""
    update_id: int
    status_code: str
    notes: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True


class TimelineResponse(BaseModel):
    """타임라인 조회 응답"""
    shipment_id: int
    current_status: str
    timeline: List[TimelineEntry]
    total_updates: int
    
    # 성능 측정용
    query_time_ms: Optional[float] = None
    source: Optional[str] = Field(
        default="postgresql",
        description="데이터 소스: postgresql 또는 elasticsearch"
    )


# =============================================================================
# Health Check
# =============================================================================

class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str = "healthy"
    version: str
    database: str = "connected"
    kafka: str = "connected"
    elasticsearch: str = "connected"

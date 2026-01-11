# =============================================================================
# LogisFlow Health Check Router
# =============================================================================

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.config import get_settings
from app.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])
settings = get_settings()


@router.get("", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """
    시스템 헬스체크
    
    모든 서비스 연결 상태 확인:
    - PostgreSQL
    - Kafka (TODO)
    - Elasticsearch (TODO)
    """
    # PostgreSQL 연결 확인
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    # TODO: Kafka, Elasticsearch 연결 확인 추가
    
    return HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        version=settings.APP_VERSION,
        database=db_status,
        kafka="not_checked",
        elasticsearch="not_checked"
    )

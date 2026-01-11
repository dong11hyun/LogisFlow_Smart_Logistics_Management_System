# =============================================================================
# LogisFlow FastAPI Main Application
# =============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import health, shipments

settings = get_settings()

# =============================================================================
# FastAPI 앱 생성
# =============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## LogisFlow 스마트 물류 플랫폼 API
    
    ### 주요 기능
    - 화물 조회 및 상태 관리
    - Q3 정합성 전략 테스트 (sync/trigger/async)
    - Q4 저장소 비교 테스트 (postgresql/elasticsearch)
    
    ### 테스트 엔드포인트
    - `POST /shipments/{id}/status` - 상태 변경 (Q3)
    - `GET /shipments/{id}/timeline` - 타임라인 조회 (Q4)
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# =============================================================================
# CORS 설정
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# 라우터 등록
# =============================================================================

app.include_router(health.router)
app.include_router(shipments.router)


# =============================================================================
# 루트 엔드포인트
# =============================================================================

@app.get("/")
def root():
    """API 루트"""
    return {
        "message": "LogisFlow API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }

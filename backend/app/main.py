# =============================================================================
# LogisFlow FastAPI Main Application
# =============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import get_settings
from app.routers import health, shipments
from app.kafka_producer import get_kafka_producer, close_kafka_producer
from app.kafka_consumer import consume_status_updates
import asyncio

# Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시: Kafka Producer 연결
    await get_kafka_producer()
    
    # 시작 시: Kafka Consumer 백그라운드 실행
    consumer_task = asyncio.create_task(consume_status_updates())
    
    yield
    
    # 종료 시: Kafka Producer 연결 해제
    await close_kafka_producer()
    
    # 종료 시: Consumer 태스크 취소 (우아한 종료는 추가 로직 필요)
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass

# =============================================================================
# FastAPI 앱 생성
# =============================================================================

# Rate Limiter 설정 (Redis 사용)
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)

app = FastAPI(
    lifespan=lifespan,
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

# Rate Limiter 등록
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
@limiter.limit("10/minute") # 테스트를 위한 Rate Limit 설정
def root(request: Request):
    """API 루트"""
    return {
        "message": "LogisFlow API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }

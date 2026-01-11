# =============================================================================
# LogisFlow Database Connection
# =============================================================================

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

# SQLAlchemy 엔진 생성
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # 연결 유효성 검사
    echo=settings.DEBUG  # SQL 로그 출력 (DEBUG 모드)
)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모델 베이스 클래스
Base = declarative_base()


def get_db():
    """DB 세션 의존성 주입용"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

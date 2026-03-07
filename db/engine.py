"""
SMALL AX AGENT — DB 엔진 + 세션 팩토리 (async)
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from .models import Base
from config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """테이블 생성 + RAG 지식베이스 시딩 (앱 시작 시 1회)"""
    import asyncio
    import logging
    logger = logging.getLogger(__name__)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # RAG 시딩은 동기 작업이므로 스레드 풀에서 실행
    loop = asyncio.get_event_loop()
    try:
        from rag import rag_seed
        seeded = await loop.run_in_executor(None, rag_seed)
        if seeded:
            logger.info("RAG knowledge base seeded successfully")
    except Exception as e:
        logger.warning(f"RAG seed skipped (non-fatal): {e}")


async def get_db():
    """FastAPI dependency — DB 세션 주입"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

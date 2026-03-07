"""
SMALL AX AGENT — FastAPI 메인 앱
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import init_db
from api.routes.sessions import router as session_router
from api.routes.chat import router as chat_router
from api.routes.export import router as export_router

# ── 로깅 설정 ────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── 앱 라이프사이클 ───────────────────────────────────────

async def _seed_rag_background() -> None:
    """RAG 시딩을 백그라운드에서 실행 — 서버 시작을 블로킹하지 않음"""
    loop = asyncio.get_event_loop()
    try:
        from rag import rag_seed
        seeded = await loop.run_in_executor(None, rag_seed)
        if seeded:
            logger.info("✅ RAG knowledge base seeded in background")
    except Exception as e:
        logger.warning(f"Background RAG seed failed (non-fatal): {e}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("🚀 SMALL AX AGENT starting...")
    await init_db()
    logger.info("✅ DB initialized")
    asyncio.create_task(_seed_rag_background())  # 헬스체크 블로킹 없이 백그라운드 실행
    yield
    logger.info("👋 SMALL AX AGENT shutting down")


# ── FastAPI 앱 ────────────────────────────────────────────

app = FastAPI(
    title="SMALL AX AGENT API",
    description="AI 자동화 설계 에이전트 백엔드",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 라우터 등록 ───────────────────────────────────────────
app.include_router(session_router)
app.include_router(chat_router)
app.include_router(export_router)


# ── 헬스체크 ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": settings.primary_model,
        "fast_model": settings.fast_model,
        "debug": settings.debug,
    }


@app.get("/")
async def root():
    return {
        "name": "SMALL AX AGENT",
        "version": "1.0.0",
        "docs": "/docs",
        "websocket": "ws://localhost:8000/api/ws/{session_id}",
    }

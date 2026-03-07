"""
SMALL AX AGENT — FastAPI 메인 앱
"""

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 SMALL AX AGENT starting...")
    await init_db()
    logger.info("✅ DB initialized")
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

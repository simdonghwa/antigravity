"""
SMALL AX AGENT — 서버 실행 진입점

사용법:
    python run.py

또는:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

import uvicorn
from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )

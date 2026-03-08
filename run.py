"""
SMALL AX AGENT — 서버 실행 진입점

사용법:
    python run.py

또는:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import sys
import uvicorn

if __name__ == "__main__":
    # Railway는 PORT 환경변수를 동적으로 주입함 — pydantic 우회하고 직접 읽기
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"

    print(f"Starting server on 0.0.0.0:{port} (debug={debug})", flush=True)

    try:
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=port,
            reload=False,           # 프로덕션 — reload 절대 사용 안 함
            log_level="debug" if debug else "info",
        )
    except Exception as e:
        print(f"STARTUP FAILED: {e}", file=sys.stderr, flush=True)
        sys.exit(1)

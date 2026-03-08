"""
SMALL AX AGENT — 중앙 설정 관리
pydantic-settings 기반 환경변수 타입 안전 로딩
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── LLM ─────────────────────────────────────────────────
    anthropic_api_key: str = Field(..., description="Anthropic API Key")
    openai_api_key: str = Field(default="", description="OpenAI API Key (임베딩용)")

    primary_model: str = "claude-sonnet-4-6"
    fast_model: str = "claude-haiku-4-5-20251001"
    embedding_model: str = "text-embedding-3-small"

    # ── Database ─────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./ax_agent.db"
    chroma_persist_dir: str = "./chroma_db"

    # ── Server ───────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    # ── Session ──────────────────────────────────────────────
    session_secret_key: str = "dev-secret-key-change-in-prod"
    session_expire_hours: int = 72

    # ── Agent Tuning ─────────────────────────────────────────
    max_interview_turns: int = 12
    max_retry_count: int = 3
    verifier_pass_threshold: int = 75
    pipeline_timeout_seconds: int = 300

    # ── Email 알림 (선택) ─────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    approval_email: str = ""           # 승인 요청 수신 이메일
    approval_base_url: str = "http://localhost:3000"  # 원클릭 승인 링크 베이스

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_username and self.approval_email)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

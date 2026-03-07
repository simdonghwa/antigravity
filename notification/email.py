"""
SMALL AX AGENT — 이메일 승인 알림 모듈
표준 라이브러리 smtplib 사용 (추가 패키지 불필요)

기능:
  - 설계 완료 시 승인자에게 HTML 이메일 발송
  - 원클릭 승인/거절 링크 (HMAC 서명 토큰)
  - SMTP 미설정 시 콘솔 출력 fallback
"""

from __future__ import annotations
import asyncio
import hashlib
import hmac
import logging
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Literal

from config import settings

logger = logging.getLogger(__name__)

# ── 토큰 생성 / 검증 ─────────────────────────────────────────

def generate_approval_token(session_id: str, action: Literal["approve", "reject"]) -> str:
    """
    HMAC-SHA256 서명 토큰 생성.
    형식: {session_id}.{action}.{timestamp}.{signature}
    유효기간: 48시간
    """
    ts = str(int(time.time()))
    payload = f"{session_id}.{action}.{ts}"
    sig = hmac.HMAC(
        settings.session_secret_key.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    return f"{payload}.{sig}"


def verify_approval_token(token: str, session_id: str) -> Literal["approve", "reject"] | None:
    """
    토큰 검증. 성공 시 action 반환, 실패 시 None.
    유효기간 48시간.
    """
    try:
        parts = token.split(".")
        if len(parts) != 4:
            return None
        sid, action, ts, sig = parts
        if sid != session_id:
            return None
        if action not in ("approve", "reject"):
            return None
        if int(time.time()) - int(ts) > 48 * 3600:
            return None
        payload = f"{sid}.{action}.{ts}"
        expected = hmac.new(
            settings.session_secret_key.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected):
            return None
        return action  # type: ignore[return-value]
    except Exception:
        return None


# ── HTML 이메일 본문 ─────────────────────────────────────────

def _build_html(
    session_id: str,
    design_summary: str,
    approve_url: str,
    reject_url: str,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
         background:#f8fafc; color:#1e293b; margin:0; padding:0; }}
  .wrap {{ max-width:600px; margin:32px auto; background:#fff;
           border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,.08); }}
  .header {{ background:linear-gradient(135deg,#3b82f6,#6366f1);
             padding:32px; color:#fff; }}
  .header h1 {{ margin:0; font-size:1.4rem; }}
  .header p  {{ margin:8px 0 0; opacity:.85; font-size:.9rem; }}
  .body {{ padding:28px 32px; }}
  .summary {{ background:#f1f5f9; border-radius:8px; padding:16px;
              font-size:.85rem; line-height:1.8; margin-bottom:24px;
              border-left:4px solid #3b82f6; }}
  .btn-row {{ display:flex; gap:16px; margin-bottom:24px; }}
  .btn {{ display:inline-block; padding:14px 28px; border-radius:8px;
          font-weight:700; font-size:1rem; text-decoration:none; text-align:center; }}
  .btn-approve {{ background:#22c55e; color:#fff; }}
  .btn-reject  {{ background:#ef4444; color:#fff; }}
  .footer {{ padding:16px 32px; background:#f8fafc; font-size:.75rem;
             color:#94a3b8; border-top:1px solid #e2e8f0; }}
  pre {{ background:#1e293b; color:#e2e8f0; padding:12px; border-radius:6px;
         font-size:.75rem; overflow-x:auto; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>🤖 AI 자동화 설계 검토 요청</h1>
    <p>세션 ID: {session_id[:8]}…</p>
  </div>
  <div class="body">
    <div class="summary">{design_summary.replace(chr(10), '<br>')}</div>
    <div class="btn-row">
      <a href="{approve_url}" class="btn btn-approve">✅ 승인</a>
      <a href="{reject_url}" class="btn btn-reject">❌ 거절</a>
    </div>
    <p style="font-size:.8rem;color:#64748b;">
      링크 유효 기간: 48시간<br>
      승인하면 n8n / Make 내보내기 파일을 즉시 다운로드할 수 있습니다.
    </p>
  </div>
  <div class="footer">AX Agent — AI 자동화 설계 도우미</div>
</div>
</body>
</html>"""


# ── 이메일 발송 ───────────────────────────────────────────────

async def send_approval_email(
    session_id: str,
    design_summary: str,
    to_email: str | None = None,
) -> bool:
    """
    승인 요청 이메일 비동기 발송.
    SMTP 미설정 시 콘솔에 링크 출력 (개발 fallback).
    Returns True if sent successfully.
    """
    to_email = to_email or settings.approval_email
    if not to_email:
        logger.warning("approval_email 미설정 — 이메일 발송 건너뜀")
        return False

    approve_token = generate_approval_token(session_id, "approve")
    reject_token  = generate_approval_token(session_id, "reject")
    base = settings.approval_base_url.rstrip("/")
    approve_url = f"{base}/api/approve/{session_id}?token={approve_token}&action=approve"
    reject_url  = f"{base}/api/approve/{session_id}?token={reject_token}&action=reject"

    # SMTP 미설정 → 콘솔 fallback
    if not settings.email_enabled:
        logger.info(
            f"\n{'='*60}\n"
            f"[EMAIL FALLBACK] 승인 요청 (세션: {session_id[:8]})\n"
            f"승인: {approve_url}\n"
            f"거절: {reject_url}\n"
            f"{'='*60}"
        )
        return True

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _send_smtp, session_id, design_summary,
        approve_url, reject_url, to_email,
    )


def _send_smtp(
    session_id: str,
    design_summary: str,
    approve_url: str,
    reject_url: str,
    to_email: str,
) -> bool:
    """동기 SMTP 전송 (thread pool에서 실행)."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[AX Agent] 자동화 설계 검토 요청 ({session_id[:8]})"
        msg["From"] = settings.smtp_from or settings.smtp_username
        msg["To"] = to_email

        # 텍스트 파트 (fallback)
        text_body = (
            f"자동화 설계 검토 요청\n\n"
            f"{design_summary}\n\n"
            f"승인: {approve_url}\n"
            f"거절: {reject_url}\n"
        )
        msg.attach(MIMEText(text_body, "plain", "utf-8"))

        # HTML 파트
        html_body = _build_html(session_id, design_summary, approve_url, reject_url)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.sendmail(msg["From"], [to_email], msg.as_string())

        logger.info(f"승인 이메일 발송 완료 → {to_email}")
        return True

    except Exception as e:
        logger.error(f"이메일 발송 실패: {e}")
        return False

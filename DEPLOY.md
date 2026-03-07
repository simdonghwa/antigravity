# SMALL AX AGENT — 배포 가이드

## 구성

| 역할 | 플랫폼 | 비용 |
|------|--------|------|
| 프론트엔드 (Next.js) | Vercel | 무료 Hobby |
| 백엔드 (FastAPI) | Railway | $5/월 Starter |

---

## 1단계 — Railway (백엔드)

### 1-1. 레포지토리 연결
1. [railway.app](https://railway.app) 로그인 → **New Project → Deploy from GitHub repo**
2. 이 레포지토리 선택

### 1-2. Dockerfile 지정
Railway 대시보드 → **Settings → Build** → Dockerfile Path: `Dockerfile.backend`
(또는 `railway.toml`이 자동 감지됨)

### 1-3. 환경변수 설정
**Variables** 탭에 아래 항목 입력 (`.env.production.example` 참고):

```
ANTHROPIC_API_KEY=sk-ant-...
SESSION_SECRET_KEY=<openssl rand -hex 32>
CORS_ORIGINS=https://your-app.vercel.app
DEBUG=false
APPROVAL_BASE_URL=https://your-app.vercel.app
```

### 1-4. Volume 마운트 (데이터 영속)
**Settings → Volumes** → `/data` 경로 볼륨 추가
그리고 Variables에:
```
DATABASE_URL=sqlite+aiosqlite:////data/ax_agent.db
CHROMA_PERSIST_DIR=/data/chroma_db
```

### 1-5. 도메인 확인
Deploy 완료 후 **Settings → Networking → Public Domain** 복사
예: `https://ax-backend-production.up.railway.app`

---

## 2단계 — Vercel (프론트엔드)

### 2-1. 프로젝트 임포트
1. [vercel.com](https://vercel.com) 로그인 → **Add New Project → Import Git Repository**
2. 이 레포지토리 선택

### 2-2. 빌드 설정
Vercel이 Next.js를 자동 감지함. `vercel.json`으로 설정 자동 적용.

### 2-3. 환경변수 설정
**Settings → Environment Variables**:

```
NEXT_PUBLIC_API_URL = https://ax-backend-production.up.railway.app
```

### 2-4. 배포
**Deploy** 클릭 → 완료 후 `https://your-app.vercel.app` 접속

---

## 3단계 — Railway CORS 업데이트

Vercel URL 확정 후 Railway Variables 업데이트:
```
CORS_ORIGINS=https://your-app.vercel.app
APPROVAL_BASE_URL=https://your-app.vercel.app
```
→ Railway 자동 재배포됨

---

## 이메일 승인 알림 설정 (선택)

Gmail 기준:
1. Google 계정 → 보안 → 앱 비밀번호 생성
2. Railway Variables에 추가:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=앱비밀번호16자리
APPROVAL_EMAIL=수신할이메일@gmail.com
```

---

## 로컬 Docker 테스트

```bash
# .env 파일 확인 후 실행
docker compose up --build

# 프론트: http://localhost:3000
# 백엔드: http://localhost:8000/docs
```

---

## 주의사항

- **SQLite 한계**: Railway 재배포 시 볼륨이 없으면 데이터 초기화됨. Volume 설정 필수.
- **ChromaDB**: 첫 배포 시 MiniLM 모델(79MB) 이미지에 포함되어 있음 (Dockerfile.backend 빌드 타임 pre-download).
- **ANTHROPIC_API_KEY**: 절대 GitHub에 커밋하지 말 것. `.gitignore`에 `.env` 포함되어 있음.

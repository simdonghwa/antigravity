# [기획안] 소상공인 경영 인사이트 플랫폼 (SaaS)

## 1. 개요 (Overview)
*   **서비스 명**: 캐시노트 체크포인트 (가칭)
*   **목표**: 소상공인을 대상으로 매출/운영 현황(인사이트)과 맞춤형 지원사업 정보를 제공하고, 정기적인 리포트를 통해 체계적인 사업 관리를 돕는 프리미엄 경영 관리 대시보드.
*   **핵심 가치**: 데이터 기반의 경영 현황 파악, 정부 지원사업 매칭, 간편한 서류 증빙 및 계약 관리.
*   **운영 전략**: 효율적인 비용 구조를 위해 무료 OCR(Google Apps Script), 메신저 기반 운영(Slack), 자동화 CRM(Braze)을 적극 활용.

---

## 2. 서비스 운영 프로세스 (Service Flow)

### 2.1. 전체 흐름
**진입 → 본인 인증 → 온보딩 → (제한적) 대시보드 → 서류 제출 → 승인(자동화/Slack) → (전체) 대시보드 & 리포트**

### 2.2. 단계별 상세 프로세스

1.  **초기 진입 및 로그인**
    *   사용자: 문자 링크 접속 -> 사업자번호/전화번호 입력.
    *   Braze: 진입 이벤트(`session_start`) 수집, 미로그인 이탈 시 리마인드 메시지 발송 준비.

2.  **서비스 온보딩**
    *   캐러셀 형태의 서비스 안내 (주간 동향, 월간 인사이트, 체크포인트 리포트).
    *   핵심 가치 전달 후 '시작하기' 버튼 클릭.

3.  **대시보드 (검수 전 - 제한 모드)**
    *   메인 화면 진입 시 일부 콘텐츠만 열람 가능 (주간 동향 등).
    *   핵심 리포트 및 심층 분석 데이터는 **'잠금(Lock)'** 처리.
    *   잠금 해제를 위한 **[서류 제출하기]** 버튼 강조.

4.  **서류 제출 및 OCR (핵심 기술)**
    *   **사용자 Action**: 사업자등록증, 계좌사본 2종 이미지 업로드.
    *   **Backend (Google Apps Script)**:
        *   이미지를 Google Drive 임시 폴더에 저장.
        *   Google Docs 변환 기능을 이용해 텍스트 추출 (무료 OCR).
        *   (필요 시) Claude API를 통해 텍스트 파싱하여 정형 데이터(JSON)로 변환.
    *   **Frontend**:
        *   추출된 정보(사업자 번호, 계좌번호 등)를 입력 필드에 자동 채움.
        *   사용자가 최종 확인 후 '제출' 버튼 클릭.

5.  **운영 및 승인 (Slack Ops)**
    *   **System**: 제출 완료 시 Slack `#승인요청` 채널에 알림 전송 (이미지 링크, 추출 정보 포함).
    *   **관리자**: Slack 내에서 서류 확인 후 `[승인]` 또는 `[반려]` 버튼 클릭 (Slack ID로 어드민 권한 처리).
    *   **System**: 승인 시 사용자 상태(`IS_VERIFIED`) 업데이트 및 Braze 이벤트 전송.

6.  **전체 서비스 이용 (Full Access)**
    *   **Braze**: 승인 완료 알림톡 자동 발송 ("사장님, 모든 리포트가 열렸습니다!").
    *   사용자: 대시보드 내 잠금 해제, 분기별 상세 리포트 열람 가능.

---

## 3. 상세 기능 명세 (Functional Requirements)

### A. 로그인 (Login)
*   **입력**: [사업자번호], [전화번호], [사업장명]
*   **기능**: 자동 로그인(쿠키/세션), 유효성 검사.

### B. 메인 홈 / 대시보드 (Dashboard)
*   **헤더**: "{사업장명} 사장님" 개인화 인사.
*   **월간 인사이트 요약**:
    *   평균 월매출, 방문자 수 등 핵심 지표 카드 형태 노출.
    *   전월 대비 증감(MoM)을 색상(파랑/빨강)과 화살표로 직관적 표시.
*   **콘텐츠 피드**:
    *   [주간 동향] / [월간 지원사업] 탭 구분.
    *   리스트 썸네일 우측 배치, 읽지 않은 콘텐츠 표시.
*   **잠금(Lock) UI**: 검수 전 상태일 때 콘텐츠 위에 불투명 레이어 및 자물쇠 아이콘 오버레이.

### C. 서류 제출 (Documents)
*   **가이드**: "서비스 이용 및 리포트 열람을 위해 필수 서류가 필요합니다."
*   **기능**:
    *   파일 업로더 (Drag & Drop 또는 파일 선택).
    *   OCR 결과 미리보기 및 수정 기능.
*   **상태 안내**: 승인 대기 중, 반려됨(사유 포함), 승인 완료 칩(Chip) 표시.

### D. 리포트 (Reports)
*   **리스트**: 분기별 리포트 목록 (최신순).
*   **열람 제한**: 신청하지 않은 리포트의 경우 '신청하기' 버튼 노출.

### E. 마이페이지 (My Page)
*   내 정보 수정, 서류 제출 현황 재확인, 로그아웃.

---

## 4. 기술 스택 및 아키텍처 (Tech Stack)

### Frontend
*   **Framework**: Next.js 14+ (App Router)
*   **Styling**: Vanilla CSS (Premium Custom Design, Glassmorphism)
*   **Interaction**: Framer Motion (Page Transition, Micro-interactions)

### Backend & Automation (Cost-Saving Structure)
*   **OCR**: Google Apps Script (Drive API Image-to-Docs conversion)
*   **Database/Storage**: Google Spreadsheet & Drive (초기 단계), 필요 시 Firebase 확장.
*   **Operations**: Slack Webhook & Interactive Messages (간이 어드민).
*   **CRM**: Braze SDK (유저 상태 관리 및 마케팅 자동화).
*   **AI**: Claude API (비정형 텍스트 데이터 구조화 보조).

---

## 5. 디자인 가이드 (Design Code)
*   **컨셉**: 신뢰감을 주는 프리미엄 금융/경영 서비스.
*   **컬러**:
    *   Primary: Deep Navy (신뢰, 전문성)
    *   Accent: Vibrant Blue (성장, 긍정), Alert Red (주의)
    *   Background: Soft Gray / Pale Blue (편안함)
*   **타이포그래피**: 가독성 높은 산세리프 (Pretendard, Inter).
*   **요소**: 그림자(Shadow)와 블러(Blur)를 활용한 입체감, 라운드 처리된 카드 UI.

---
*작성일: 2026-01-17*
*작성자: Antigravity*

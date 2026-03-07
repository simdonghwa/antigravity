# [Project Plan] SMB Management Insight Platform (SaaS)

## 1. Overview
*   **Service Name**: Cashnote Checkpoint (Tentative)
*   **Goal**: To build a premium management dashboard for small business owners, providing insights, market trends, and tailored government support information, helping them manage their business systematically through regular reports.
*   **Core Value**: Data-driven management insights, efficient government support matching, and simplified document submission/verification.
*   **Operational Strategy**: Maximizing cost efficiency by utilizing Free OCR (Google Apps Script), Messenger-based Ops (Slack), and Automated CRM (Braze).

---

## 2. Service Logic & Flow

### 2.1. Overall Flow
**Entry → Authenticaton → Onboarding → (Limited) Dashboard → Document Submission → Approval (Slack/Auto) → (Full) Dashboard & Reports**

### 2.2. Detailed Step-by-Step Process

1.  **Entry & Login**
    *   User: Access via SMS link -> Input Business No / Phone No.
    *   Braze: Collect entry event (`session_start`), prepare reminder messages for drop-offs.

2.  **Onboarding**
    *   Carousel-style service introduction (Weekly Trends, Monthly Insights, Checkpoint Reports).
    *   Deliver core value proposition then prompt 'Get Started'.

3.  **Dashboard (Pre-verification - Limited Mode)**
    *   Limited access to content upon main entry (e.g., generic weekly trends).
    *   Core reports and deep insights are **'Locked'**.
    *   Prominent **[Submit Documents]** button to unlock features.

4.  **Document Submission & OCR (Core Tech)**
    *   **User Action**: Upload Business Registration & Bank Account Copy images.
    *   **Backend (Google Apps Script)**:
        *   Save image to specific Google Drive temporary folder.
        *   Convert image to Google Doc to extract text (Free OCR).
        *   (If needed) Parse unstructured text via Claude API into JSON.
    *   **Frontend**:
        *   Auto-fill input fields with extracted info (Biz No, Account No, etc.).
        *   User reviews and clicks 'Submit'.

5.  **Operations & Approval (Slack Ops)**
    *   **System**: Send notification to Slack `#approval-request` channel upon submission (includes image link & extracted data).
    *   **Admin**: Click `[Approve]` or `[Reject]` button directly within Slack (authenticated via Slack ID).
    *   **System**: On approval, update user state (`IS_VERIFIED`) and trigger Braze event.

6.  **Full Service Access**
    *   **Braze**: Send automated approval notification ("Boss, your reports are unlocked!").
    *   User: Dashboard unlocked, access to quarterly detailed reports enabled.

---

## 3. Functional Requirements

### A. Login
*   **Inputs**: [Business No], [Phone No], [Business Name].
*   **Features**: Auto-login (Cookie/Session), validation logic.

### B. Main Home / Dashboard
*   **Header**: Personalized greeting "{Business Name} CEO".
*   **Monthly Insight Summary**:
    *   Key metrics cards (Avg Sales, Visitor Count).
    *   MoM (Month-over-Month) changes indicated by color (Blue/Red) and arrows.
*   **Content Feed**:
    *   Tabs: [Weekly Trends] / [Monthly Support].
    *   List view with right-aligned thumbnails, unread indicators.
*   **Lock UI**: Overlay with blur effect and lock icon for locked content when unverified.

### C. Document Submission
*   **Guide**: "Required documents are needed to access reports and service."
*   **Features**:
    *   File Uploader (Drag & Drop or Select).
    *   OCR Result Preview & Edit.
*   **Status Indicators**: Pending, Rejected (with reason), Verified (Chip UI).

### D. Reports
*   **List**: Quarterly report list (Newest first).
*   **Access Control**: 'Request' button shown for unrequested reports.

### E. My Page
*   Edit info, view document submission status, logout.

---

## 4. Tech Stack & Architecture

### Frontend
*   **Framework**: Next.js 14+ (App Router)
*   **Styling**: Vanilla CSS (Premium Custom Design, Glassmorphism)
*   **Interaction**: Framer Motion (Page Transition, Micro-interactions)

### Backend & Automation (Cost-Saving Structure)
*   **OCR**: Google Apps Script (Drive API Image-to-Docs conversion).
*   **Database/Storage**: Google Spreadsheet & Drive (MVP Phase), firebase if needed.
*   **Operations**: Slack Webhook & Interactive Messages (mini-admin).
*   **CRM**: Braze SDK (User state management & Marketing automation).
*   **AI**: Claude API (Parsing unstructured text).

---

## 5. Design Guidelines
*   **Concept**: Premium Financial/Management Service promoting trust.
*   **Colors**:
    *   Primary: Deep Navy (Trust, Professionalism)
    *   Accent: Vibrant Blue (Growth), Alert Red (Caution)
    *   Background: Soft Gray / Pale Blue (Comfort)
*   **Typography**: Clean Sans-serif (Pretendard, Inter).
*   **Elements**: Dimensional UI using Shadows and Blurs, rounded card UI.

---
*Date: 2026-01-17*
*Author: Antigravity*

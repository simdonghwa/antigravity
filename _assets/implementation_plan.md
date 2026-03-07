# Project: SMB Insight Dashboard (Small Business Management Service)

## 1. Overview
This web service is a management dashboard for small business owners ("Bosses"), offering insights, trend reports, and support business information. It includes a strict onboarding and document verification flow before granting full access to premium contents.

## 2. Tech Stack
- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript
- **Styling:** Vanilla CSS (CSS Modules) - *Focusing on premium, custom styling*
- **Animation:** Framer Motion (page transitions, interactions)
- **Icons:** Lucide React
- **Charts:** Recharts or Chart.js (for Dashboard)
- **OCR & Backend Automation:** Google Apps Script (Google Docs OCR Hack)
- **CRM & Messaging:** Braze
- **Operations & Notifications:** Slack API
- **AI/analysis:** Claude API (via API Proxy if needed)

## 3. Directory Structure
```
src/
├── app/
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # Redirect to login or home
│   ├── (auth)/
│   │   └── login/              # Login Page (Business No, Phone)
│   ├── (onboarding)/
│   │   └── intro/              # Service Guide Carousel
│   ├── (main)/                 # Main App Layout (Bottom Nav)
│   │   ├── home/               # Main Dashboard & Content Feed
│   │   ├── report/             # Quarterly Reports
│   │   └── my/                 # Document Submission & Status
│   └── (features)/
│       └── document/           # Document Upload Flow
├── components/
│   ├── common/                 # Buttons, Cards, Modals, Inputs
│   ├── layout/                 # Navbar, BottomNav, Header
│   ├── domain/
│   │   ├── dashboard/          # Insight Charts, Summary Cards
│   │   ├── contents/           # Content List, Content Detail
│   │   └── documents/          # Uploaders, Status Chips
├── styles/
│   ├── globals.css             # Reset, Variables (Colors, Fonts)
│   └── animations.css          # Keyframes
├── lib/                        # Utils, Constants
└── types/                      # TypeScript Interfaces
```

## 4. Detailed Feature Specifications

### A. Authentication & User (Auth)
- **Login:**
  - Input: Business Registration Number, Phone Number, Business Name.
  - Action: "Start" button.
- **User State:**
  - `IS_VERIFIED`: Boolean (Documents approved).
  - `HAS_SUBMITTED`: Boolean (Documents uploaded but pending).

### B. Onboarding
- **Carousel UI:**
  - Slide 1: Service Welcome.
  - Slide 2: Checkpoint Report Guide.
  - Slide 3: Market Trends (Weekly).
  - Slide 4: Business Insights (Monthly).
  - Slide 5: Support Business Guide.
- **Action:** "Skip" or "Done".

### C. Main Home (Dashboard)
- **Header:** "Hello, {BusinessName} CEO!"
- **Monthly Insight (Dashboard):**
  - **Cards:** Avg Monthly Sales, Close Rate, Card Sales (MoM).
  - **Visuals:**
    - Increase: Blue Text + Up Triangle.
    - Decrease: Red Text + Down Triangle.
  - **Chart:** Vertical Bar Chart (Revisit Rate: Last Month vs This Month).
- **Content Area (Feed):**
  - Tabs: "Weekly Trends" | "Monthly Support".
  - **List Item:** Title (Bold), Summary (2 lines), Thumbnail (Right aligned).
  - **Locked State:** If `!IS_VERIFIED`, overlay content with Blur/Glass effect + Lock Icon.
    - Click Action: Redirect to Document Submission.
  - **Pagination:** Load 5 items -> "Load More" or Infinite Scroll.

### D. Reports
- **List View:** Quarterly Reports (e.g., "2024 Q3 Checkpoint Report").
- **Status:**
  - If requested: "View Report" button.
  - If not requested: "Request Needed" (Red/Yellow alert box).

### E. My Page / Document Center
- **Status Overview:** List of required docs (Business Reg, Account Copy, etc.).
- **Upload Flow (Cost-Efficient OCR):**
  - **Step 1:** User uploads image (Business Registration, Account Copy).
  - **Step 2:** File sent to **Google Apps Script (GAS)** Webhook.
  - **Step 3 (GAS Side):**
    - Save image to Google Drive.
    - Convert Image to Google Doc (Native Ocr).
    - Extract text body from Google Doc.
    - (Optional) Send text to **Claude** or Regex parser to structure data (Biz No, Name, Bank, Account No).
  - **Step 4:** Return structured data to Client.
  - **Step 5:** Pre-fill inputs with OCR result.
  - **Verification Dialogue:** "Is this information correct?" (Yes/No).
    - If "No", User manually corrects.

### F. Operations & Notifications
- **Slack Integration:**
  - Notify Admin channel when a new document is submitted.
  - Notify when a "Verification Request" is pending.
  - Daily summary of "New Contracts".
- **Braze Integration:**
  - Send "Welcome" email/LMS upon Sign-up.
  - Send "Reminder" if documents are pending for > 3 days.
  - Deliver "Monthly Insight" content links via Braze campaigns.

## 5. Design System & Aesthetics
- **Theme:** Premium Mobile-First Web App.
- **Color Palette:**
  - Primary: Deep Navy/Blue (Trust).
  - Secondary: Soft Blue (Backgrounds).
  - Accents: Vibrant Blue (Growth), Alert Red (Decrease/Action needed).
  - Surface: Glassmorphism (Translucent white borders, blurs).
- **Typography:** Modern Sans-serif (Inter or Pretendard).
- **Interactions:**
  - Soft hover states on cards.
  - Smooth slide transitions between tabs.
  - Skeleton loading states.

## 6. Implementation Steps
1.  **Setup:** Initialize Next.js, configure CSS variables (Theming).
2.  **Components:** Build low-level UI (Card, Button, Badge, Input).
3.  **Layout:** Create Mobile Wrapper and Bottom Navigation.
4.  **Pages - Login & Onboarding:** Implement slide & inputs.
5.  **Pages - Main Dashboard:** Build Chart widgets and Feed list.
6.  **Feature - Lock Mechanism:** Implement the blur overlay logic.
7.  **Pages - Document & Reports:** Build detailed list views.
8.  **Polish:** Animations, Transitions, SEO tags.

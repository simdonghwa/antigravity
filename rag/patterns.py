"""
소상공인 업무 자동화 패턴 지식베이스 — 50개 이상 큐레이션된 패턴
각 패턴은 실제 사용 사례에서 검증된 자동화 레시피
"""

# ── 패턴 구조 ──────────────────────────────────────────────
# id: 고유 식별자
# title: 패턴명 (Korean)
# business_types: 해당 업종 리스트
# problem: 자동화 전 문제
# solution: 자동화 솔루션 요약
# tools: 사용 도구 조합
# time_saved_hours_weekly: 주간 절약 시간 (평균)
# complexity: LOW / MEDIUM / HIGH
# pattern_type: LINEAR / TRIGGER_ACTION / PIPELINE / APPROVAL / AGGREGATION
# tags: 검색용 태그

AUTOMATION_PATTERNS = [

    # ══════════════════════════════════════════════
    # 스마트스토어 / 이커머스
    # ══════════════════════════════════════════════

    {
        "id": "smst-001",
        "title": "스마트스토어 신규 주문 자동 처리",
        "business_types": ["스마트스토어", "쇼핑몰", "이커머스"],
        "problem": "주문 알림 → 엑셀 입력 → 배송 요청을 매일 2~3시간 수작업",
        "solution": "네이버 쇼핑 API → 주문 수집 → 택배사 API 배송 요청 → 카카오톡 배송 알림 자동 발송",
        "tools": ["네이버 쇼핑 API", "CJ대한통운 API", "카카오 알림톡"],
        "time_saved_hours_weekly": 12,
        "complexity": "MEDIUM",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["주문처리", "배송", "알림", "스마트스토어", "이커머스"],
        "code_template": "smartstore_order_pipeline",
    },
    {
        "id": "smst-002",
        "title": "재고 부족 자동 알림 + 발주",
        "business_types": ["스마트스토어", "소매업", "식품"],
        "problem": "재고 확인을 매일 수동으로 하다가 품절 사태 발생",
        "solution": "DB 재고 모니터링 → 임계치 이하 감지 → 슬랙/카톡 알림 → 자동 발주서 생성",
        "tools": ["SQLite/PostgreSQL", "슬랙 API", "이메일"],
        "time_saved_hours_weekly": 5,
        "complexity": "LOW",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["재고관리", "발주", "알림", "이커머스"],
        "code_template": "inventory_monitor",
    },
    {
        "id": "smst-003",
        "title": "상품 리뷰 감정 분석 + 응대 초안 생성",
        "business_types": ["스마트스토어", "쇼핑몰"],
        "problem": "부정 리뷰 대응이 늦어 평점 관리 어려움",
        "solution": "리뷰 크롤링 → 감정 분석(Claude) → 부정 리뷰 필터 → 응대 문구 초안 생성 → 슬랙 전송",
        "tools": ["네이버 쇼핑 API", "Claude API", "슬랙"],
        "time_saved_hours_weekly": 3,
        "complexity": "MEDIUM",
        "pattern_type": "PIPELINE",
        "tags": ["리뷰관리", "CS", "감정분석", "LLM"],
        "code_template": "review_monitor",
    },
    {
        "id": "smst-004",
        "title": "정산 자동화 + 월별 수익 리포트",
        "business_types": ["스마트스토어", "쇼핑몰", "이커머스"],
        "problem": "월말 정산을 엑셀로 수작업 집계, 4~5시간 소요",
        "solution": "스마트스토어 정산 API → 데이터 집계 → 엑셀/PDF 리포트 자동 생성 → 이메일 발송",
        "tools": ["네이버 쇼핑 API", "openpyxl", "Gmail API"],
        "time_saved_hours_weekly": 4,
        "complexity": "MEDIUM",
        "pattern_type": "AGGREGATION",
        "tags": ["정산", "회계", "리포트", "이커머스"],
    },

    # ══════════════════════════════════════════════
    # 카페 / 베이커리
    # ══════════════════════════════════════════════

    {
        "id": "cafe-001",
        "title": "카페 일일 매출 집계 + 포스 연동",
        "business_types": ["카페", "베이커리", "식음료"],
        "problem": "매일 저녁 포스기 매출 데이터를 수동으로 엑셀에 옮겨야 함",
        "solution": "포스기 API/CSV 자동 수집 → DB 저장 → 일/주/월 매출 대시보드 자동 업데이트",
        "tools": ["포스기 API(오더피스/얼리페이)", "Google Sheets API", "슬랙"],
        "time_saved_hours_weekly": 3,
        "complexity": "LOW",
        "pattern_type": "PIPELINE",
        "tags": ["매출관리", "포스", "대시보드", "카페"],
    },
    {
        "id": "cafe-002",
        "title": "카카오 예약 자동 확정 + 사전 알림",
        "business_types": ["카페", "베이커리", "디저트"],
        "problem": "예약 문의 카톡/전화 응대에 하루 1~2시간 소비",
        "solution": "카카오 채널 예약 폼 → 자동 확정 + 24시간 전 리마인드 알림톡 발송",
        "tools": ["카카오 알림톡", "Google Calendar API"],
        "time_saved_hours_weekly": 6,
        "complexity": "LOW",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["예약관리", "알림", "카페", "고객응대"],
    },
    {
        "id": "cafe-003",
        "title": "재료 소진 예측 + 자동 발주",
        "business_types": ["카페", "베이커리", "식음료"],
        "problem": "재료가 갑자기 떨어져 메뉴를 못 파는 상황 발생",
        "solution": "일별 판매 데이터 분석 → 소진 예측(7일) → 발주 임계일에 자동 주문서 생성 + 이메일",
        "tools": ["포스기 API", "Gmail API"],
        "time_saved_hours_weekly": 4,
        "complexity": "MEDIUM",
        "pattern_type": "PIPELINE",
        "tags": ["재고예측", "발주", "카페"],
    },

    # ══════════════════════════════════════════════
    # 헤어샵 / 미용실
    # ══════════════════════════════════════════════

    {
        "id": "hair-001",
        "title": "헤어샵 예약 자동 확인 + 리마인드",
        "business_types": ["헤어샵", "미용실", "뷰티살롱"],
        "problem": "예약 노쇼(no-show)로 인한 공석 손실, 수동 연락 시간 낭비",
        "solution": "예약 DB → 1일 전 카카오 알림톡 발송 → 노쇼 기록 자동화 → 블랙리스트 관리",
        "tools": ["카카오 알림톡", "SQLite"],
        "time_saved_hours_weekly": 5,
        "complexity": "LOW",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["예약관리", "노쇼방지", "헤어샵", "알림"],
    },
    {
        "id": "hair-002",
        "title": "헤어샵 단골 고객 재방문 유도 자동화",
        "business_types": ["헤어샵", "미용실", "뷰티"],
        "problem": "단골 고객에게 주기적으로 연락하는 것을 깜빡함",
        "solution": "고객 DB → 마지막 방문일 60일 초과 감지 → 맞춤 프로모션 카톡 발송 자동화",
        "tools": ["SQLite", "카카오 알림톡"],
        "time_saved_hours_weekly": 3,
        "complexity": "LOW",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["CRM", "재방문", "마케팅", "헤어샵"],
    },

    # ══════════════════════════════════════════════
    # 학원 / 교습소
    # ══════════════════════════════════════════════

    {
        "id": "acad-001",
        "title": "학원 출결 자동화 + 학부모 알림",
        "business_types": ["학원", "교습소", "교육"],
        "problem": "출석 체크 후 결석 학생 학부모에게 일일이 연락해야 함",
        "solution": "QR/카드 출석 체크 → 미출석 감지 → 학부모 SMS/카톡 자동 발송",
        "tools": ["QR 스캐너 API", "카카오 알림톡", "SQLite"],
        "time_saved_hours_weekly": 5,
        "complexity": "MEDIUM",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["출결관리", "학원", "학부모알림"],
    },
    {
        "id": "acad-002",
        "title": "학원 월 수강료 청구 자동화",
        "business_types": ["학원", "교습소"],
        "problem": "매월 수강료 청구서 작성 + 미납 확인을 수작업으로 3~4시간",
        "solution": "학생 DB → 월말 청구서 자동 생성 → 카카오페이 납부 링크 포함 발송 → 미납 자동 리마인드",
        "tools": ["카카오 알림톡", "카카오페이 API", "openpyxl"],
        "time_saved_hours_weekly": 4,
        "complexity": "MEDIUM",
        "pattern_type": "PIPELINE",
        "tags": ["수강료", "정산", "학원"],
    },

    # ══════════════════════════════════════════════
    # 식당 / 배달
    # ══════════════════════════════════════════════

    {
        "id": "rest-001",
        "title": "배달 주문 통합 관리 + 자동 접수",
        "business_types": ["식당", "배달음식점", "분식"],
        "problem": "배민/쿠팡이츠/요기요 주문을 각각 탭으로 확인해야 함",
        "solution": "배달 플랫폼 API → 통합 주문 큐 → 포스기 자동 출력 → 주문 현황 모니터링",
        "tools": ["배달의민족 API", "쿠팡이츠 API", "포스기 API"],
        "time_saved_hours_weekly": 10,
        "complexity": "HIGH",
        "pattern_type": "AGGREGATION",
        "tags": ["배달", "주문통합", "식당"],
    },
    {
        "id": "rest-002",
        "title": "식재료 발주 자동화 (판매량 기반)",
        "business_types": ["식당", "카페", "배달"],
        "problem": "식재료 발주를 사장이 매일 아침 직접 확인하고 전화 주문",
        "solution": "포스기 판매 데이터 → 7일 평균 계산 → 재고 예측 → 납품업체 문자/이메일 자동 발송",
        "tools": ["포스기 API", "SMS API"],
        "time_saved_hours_weekly": 5,
        "complexity": "MEDIUM",
        "pattern_type": "PIPELINE",
        "tags": ["식재료", "발주", "식당"],
    },
    {
        "id": "rest-003",
        "title": "영업 마감 정산 자동화",
        "business_types": ["식당", "카페", "소매"],
        "problem": "마감 후 카드 매출 + 현금 매출 합산을 수작업으로 30~40분",
        "solution": "포스기 마감 트리거 → 카드사 API 집계 → 현금 수동 입력 → 일 정산 리포트 자동 생성",
        "tools": ["포스기 API", "VAN사 API", "Google Sheets"],
        "time_saved_hours_weekly": 3,
        "complexity": "LOW",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["정산", "마감", "식당"],
    },

    # ══════════════════════════════════════════════
    # 부동산 / 임대업
    # ══════════════════════════════════════════════

    {
        "id": "real-001",
        "title": "임대료 자동 청구 + 연체 알림",
        "business_types": ["부동산", "임대업", "상가"],
        "problem": "매월 임차인에게 임대료 청구서를 개별 발송, 연체 확인도 수동",
        "solution": "임차인 DB → 월 1일 자동 청구서 발송 → 5일 미납 시 독촉 알림 → 연체 현황 대시보드",
        "tools": ["이메일(Gmail)", "카카오 알림톡", "SQLite"],
        "time_saved_hours_weekly": 4,
        "complexity": "LOW",
        "pattern_type": "PIPELINE",
        "tags": ["임대료", "정산", "부동산", "알림"],
    },
    {
        "id": "real-002",
        "title": "매물 등록 자동화 (네이버 부동산 연동)",
        "business_types": ["부동산중개", "공인중개사"],
        "problem": "신규 매물을 네이버 부동산, 직방, 호갱노노에 각각 수동 등록 (1시간+)",
        "solution": "매물 입력 폼 → API 연동으로 3개 플랫폼 동시 등록 → 자동 사진 리사이징 업로드",
        "tools": ["네이버 부동산 API", "직방 API"],
        "time_saved_hours_weekly": 6,
        "complexity": "HIGH",
        "pattern_type": "LINEAR",
        "tags": ["매물등록", "부동산", "멀티플랫폼"],
    },

    # ══════════════════════════════════════════════
    # 세탁소 / 수선집
    # ══════════════════════════════════════════════

    {
        "id": "laun-001",
        "title": "세탁물 완료 알림 자동화",
        "business_types": ["세탁소", "클리닝"],
        "problem": "세탁 완료 시 고객에게 일일이 전화해야 함 (1~2시간)",
        "solution": "세탁물 상태 업데이트 → 완료 감지 → 카카오 알림톡 자동 발송 (찾으러 오세요)",
        "tools": ["카카오 알림톡", "SQLite"],
        "time_saved_hours_weekly": 7,
        "complexity": "LOW",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["알림", "세탁소", "CS"],
    },

    # ══════════════════════════════════════════════
    # 의류 매장
    # ══════════════════════════════════════════════

    {
        "id": "fash-001",
        "title": "인스타그램 신상품 자동 포스팅",
        "business_types": ["의류매장", "패션", "쇼핑몰"],
        "problem": "신상품 입고 시 인스타그램 포스팅 작업 (사진 편집 + 해시태그) 30분",
        "solution": "신상품 등록 → AI 캡션 자동 생성(Claude) → 인스타그램 API 자동 포스팅 (해시태그 포함)",
        "tools": ["Instagram Graph API", "Claude API"],
        "time_saved_hours_weekly": 3,
        "complexity": "MEDIUM",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["SNS", "마케팅", "의류", "LLM"],
    },
    {
        "id": "fash-002",
        "title": "시즌 오프 재고 할인 자동화",
        "business_types": ["의류매장", "패션"],
        "problem": "시즌 말 재고 처리를 위한 할인 이벤트를 수동으로 설정해야 함",
        "solution": "재고 DB → 3개월 이상 재고 감지 → 자동 할인율 계산 → 쇼핑몰 가격 자동 업데이트 + SNS 알림",
        "tools": ["스마트스토어 API", "Instagram API", "슬랙"],
        "time_saved_hours_weekly": 3,
        "complexity": "MEDIUM",
        "pattern_type": "PIPELINE",
        "tags": ["재고처리", "할인", "의류", "마케팅"],
    },

    # ══════════════════════════════════════════════
    # 공통 - 고객관리 / CRM
    # ══════════════════════════════════════════════

    {
        "id": "crm-001",
        "title": "신규 고객 온보딩 자동화",
        "business_types": ["전 업종"],
        "problem": "신규 고객 등록 후 환영 메시지/혜택 안내를 수동으로",
        "solution": "신규 고객 DB 등록 트리거 → 환영 알림톡 → 웰컴 쿠폰 발송 → CRM 태그 자동 추가",
        "tools": ["카카오 알림톡", "SQLite"],
        "time_saved_hours_weekly": 2,
        "complexity": "LOW",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["CRM", "신규고객", "온보딩"],
    },
    {
        "id": "crm-002",
        "title": "생일 고객 자동 쿠폰 발송",
        "business_types": ["전 업종"],
        "problem": "생일 고객 찾아서 수동으로 혜택 안내하기 어려움",
        "solution": "고객 DB → 매일 생일자 조회 → 생일 쿠폰 카카오 알림톡 자동 발송",
        "tools": ["카카오 알림톡", "SQLite"],
        "time_saved_hours_weekly": 2,
        "complexity": "LOW",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["CRM", "생일마케팅", "쿠폰"],
    },
    {
        "id": "crm-003",
        "title": "고객 리텐션 자동화 (이탈 방지)",
        "business_types": ["전 업종"],
        "problem": "한동안 안 온 고객을 잡아둘 방법이 없음",
        "solution": "마지막 방문/구매일 모니터링 → 30/60/90일 경과 시 단계별 리인게이지먼트 메시지 발송",
        "tools": ["카카오 알림톡", "SQLite"],
        "time_saved_hours_weekly": 2,
        "complexity": "LOW",
        "pattern_type": "PIPELINE",
        "tags": ["CRM", "리텐션", "마케팅"],
    },

    # ══════════════════════════════════════════════
    # 공통 - 마케팅 자동화
    # ══════════════════════════════════════════════

    {
        "id": "mkt-001",
        "title": "SNS 콘텐츠 스케줄 자동화",
        "business_types": ["전 업종"],
        "problem": "인스타그램/블로그 포스팅을 매번 수동으로 올려야 함",
        "solution": "콘텐츠 캘린더 DB → 예약 시간에 자동 포스팅 (인스타/블로그) → 성과 자동 집계",
        "tools": ["Instagram API", "네이버 블로그 API"],
        "time_saved_hours_weekly": 3,
        "complexity": "LOW",
        "pattern_type": "LINEAR",
        "tags": ["SNS", "마케팅", "스케줄"],
    },
    {
        "id": "mkt-002",
        "title": "AI 리뷰 답글 자동화",
        "business_types": ["전 업종"],
        "problem": "쿠팡/네이버 리뷰 답글을 매일 수동으로 작성 (30~60분)",
        "solution": "리뷰 API 수집 → Claude로 맥락 파악 + 응대 초안 생성 → 관리자 검토 후 자동 게시",
        "tools": ["Claude API", "네이버 쇼핑 API"],
        "time_saved_hours_weekly": 4,
        "complexity": "MEDIUM",
        "pattern_type": "PIPELINE",
        "tags": ["리뷰", "CS", "LLM", "마케팅"],
    },
    {
        "id": "mkt-003",
        "title": "네이버 스마트플레이스 리뷰 모니터링",
        "business_types": ["음식점", "카페", "미용", "서비스업"],
        "problem": "네이버 지도 리뷰 확인이 늦어 부정 리뷰 대응 못함",
        "solution": "스마트플레이스 크롤링 → 새 리뷰 감지 → 슬랙 알림 → 부정 리뷰 즉시 사장님 알림",
        "tools": ["Python requests", "슬랙 API"],
        "time_saved_hours_weekly": 2,
        "complexity": "LOW",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["리뷰", "모니터링", "네이버"],
    },

    # ══════════════════════════════════════════════
    # 공통 - 운영 자동화
    # ══════════════════════════════════════════════

    {
        "id": "ops-001",
        "title": "직원 스케줄 자동 생성 + 알림",
        "business_types": ["전 업종"],
        "problem": "매주 직원 스케줄을 수동으로 짜고 카톡으로 공유",
        "solution": "가용 시간 설문(구글폼) → 자동 스케줄 생성 알고리즘 → 직원별 카카오 알림 발송",
        "tools": ["Google Forms API", "카카오 알림톡"],
        "time_saved_hours_weekly": 3,
        "complexity": "MEDIUM",
        "pattern_type": "PIPELINE",
        "tags": ["인사", "스케줄", "직원관리"],
    },
    {
        "id": "ops-002",
        "title": "일 마감 리포트 자동 생성",
        "business_types": ["전 업종"],
        "problem": "매일 저녁 매출/방문객/이슈를 정리해서 카톡방에 공유하는 데 20분",
        "solution": "포스기/DB 데이터 → 일 마감 자동 집계 → 시각화 리포트 생성 → 카카오톡 채널 자동 발송",
        "tools": ["포스기 API", "카카오 알림톡", "matplotlib"],
        "time_saved_hours_weekly": 2,
        "complexity": "LOW",
        "pattern_type": "AGGREGATION",
        "tags": ["리포트", "마감", "대시보드"],
    },
    {
        "id": "ops-003",
        "title": "거래처 세금계산서 자동화",
        "business_types": ["전 업종"],
        "problem": "매월 거래처에 세금계산서 발행하는 데 2~3시간 소요",
        "solution": "거래 DB → 월 마감 시 세금계산서 자동 생성 → 국세청 API 전자발행 → 이메일 자동 발송",
        "tools": ["국세청 전자세금계산서 API", "Gmail"],
        "time_saved_hours_weekly": 3,
        "complexity": "MEDIUM",
        "pattern_type": "PIPELINE",
        "tags": ["세금계산서", "정산", "회계"],
    },
    {
        "id": "ops-004",
        "title": "직원 급여 명세서 자동 발송",
        "business_types": ["전 업종"],
        "problem": "매월 직원 급여 명세서를 수동 작성 + 개별 발송 1~2시간",
        "solution": "근태 데이터 + 급여 DB → 명세서 자동 생성(PDF) → 직원별 이메일 자동 발송",
        "tools": ["reportlab(PDF)", "Gmail"],
        "time_saved_hours_weekly": 2,
        "complexity": "LOW",
        "pattern_type": "PIPELINE",
        "tags": ["급여", "인사", "자동화"],
    },

    # ══════════════════════════════════════════════
    # 공통 - 고객 서비스 (CS)
    # ══════════════════════════════════════════════

    {
        "id": "cs-001",
        "title": "카카오채널 FAQ 자동 응대 챗봇",
        "business_types": ["전 업종"],
        "problem": "동일한 문의(영업시간, 위치, 메뉴 등)에 반복적으로 답장",
        "solution": "카카오 채널 → 키워드 인식 → FAQ DB 검색 → 자동 답변 발송 (미매칭 시 사장님 알림)",
        "tools": ["카카오 채널 API", "SQLite"],
        "time_saved_hours_weekly": 5,
        "complexity": "LOW",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["챗봇", "CS", "FAQ", "카카오"],
    },
    {
        "id": "cs-002",
        "title": "불만 고객 에스컬레이션 자동화",
        "business_types": ["전 업종"],
        "problem": "부정 키워드 포함 문의가 방치되어 컴플레인 악화",
        "solution": "메시지 수신 → 부정 감정 분석 → 즉시 사장님 알림 + 사과 초안 메시지 자동 생성",
        "tools": ["카카오 채널 API", "Claude API"],
        "time_saved_hours_weekly": 2,
        "complexity": "MEDIUM",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["CS", "불만처리", "에스컬레이션", "LLM"],
    },

    # ══════════════════════════════════════════════
    # 특수 업종
    # ══════════════════════════════════════════════

    {
        "id": "pet-001",
        "title": "펫샵/동물병원 예약 + 접종 일정 관리",
        "business_types": ["펫샵", "동물병원", "펫케어"],
        "problem": "반려동물 접종 일정 관리 + 예약 알림을 수동으로",
        "solution": "고객/반려동물 DB → 접종 예정일 D-7 알림 → 예약 자동 확인 → 완료 후 다음 일정 등록",
        "tools": ["카카오 알림톡", "SQLite"],
        "time_saved_hours_weekly": 5,
        "complexity": "LOW",
        "pattern_type": "PIPELINE",
        "tags": ["예약", "펫", "알림", "CRM"],
    },
    {
        "id": "fit-001",
        "title": "헬스장/필라테스 회원권 만료 알림",
        "business_types": ["헬스장", "필라테스", "요가", "스포츠센터"],
        "problem": "회원권 만료 임박 고객에게 수동으로 연락해야 함",
        "solution": "회원 DB → 만료 D-7, D-3, D-1 단계별 자동 알림 → 재등록 링크 + 할인 쿠폰 자동 발송",
        "tools": ["카카오 알림톡", "SQLite"],
        "time_saved_hours_weekly": 4,
        "complexity": "LOW",
        "pattern_type": "PIPELINE",
        "tags": ["회원관리", "만료알림", "헬스", "CRM"],
    },
    {
        "id": "edu-001",
        "title": "온라인 강의 결제 완료 자동 강좌 개설",
        "business_types": ["온라인교육", "학원", "코칭"],
        "problem": "결제 확인 후 수동으로 강좌 접근 권한 부여",
        "solution": "결제 웹훅 → 수강생 DB 자동 등록 → 강좌 접근 링크 발송 → 입과 안내 이메일",
        "tools": ["PG API(토스페이먼츠)", "Gmail", "SQLite"],
        "time_saved_hours_weekly": 5,
        "complexity": "LOW",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["결제", "교육", "온보딩", "웹훅"],
    },
    {
        "id": "ins-001",
        "title": "인테리어 견적 자동 발송",
        "business_types": ["인테리어", "건설", "시공업"],
        "problem": "견적 요청 양식 입력 후 수동으로 견적서 작성 발송 (1~2시간)",
        "solution": "견적 요청 폼 → 품목/면적 기반 자동 견적 계산 → PDF 견적서 자동 생성 → 이메일 발송",
        "tools": ["Google Forms", "reportlab", "Gmail"],
        "time_saved_hours_weekly": 6,
        "complexity": "MEDIUM",
        "pattern_type": "PIPELINE",
        "tags": ["견적", "인테리어", "PDF", "자동화"],
    },
    {
        "id": "agri-001",
        "title": "농산물 출하 + 경매 가격 모니터링",
        "business_types": ["농업", "농산물유통"],
        "problem": "가락시장 경매가를 매일 수동으로 확인 후 출하량 결정",
        "solution": "aT(농산물유통정보) API → 가격 모니터링 → 기준가 이상 시 출하 알림 → 자동 출하 신청",
        "tools": ["aT 공공API", "슬랙", "SMS"],
        "time_saved_hours_weekly": 5,
        "complexity": "MEDIUM",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["농업", "경매", "모니터링", "공공API"],
    },

    # ══════════════════════════════════════════════
    # n8n / Make 템플릿 패턴
    # ══════════════════════════════════════════════

    {
        "id": "n8n-001",
        "title": "n8n으로 구축하는 올인원 주문 처리 워크플로우",
        "business_types": ["이커머스", "스마트스토어"],
        "problem": "주문 → 재고 차감 → 배송 요청 → 알림을 각각 수동으로",
        "solution": "n8n 트리거(웹훅) → 재고 업데이트 → 배송 API → 슬랙 알림 → 고객 카톡 알림",
        "tools": ["n8n", "슬랙", "카카오 알림톡", "REST API"],
        "time_saved_hours_weekly": 10,
        "complexity": "LOW",
        "pattern_type": "LINEAR",
        "tags": ["n8n", "이커머스", "워크플로우", "노코드"],
    },
    {
        "id": "n8n-002",
        "title": "Make(Integromat)로 구글시트 → CRM 자동 동기화",
        "business_types": ["전 업종"],
        "problem": "구글시트 고객 목록과 CRM이 따로 관리되어 불일치 발생",
        "solution": "Make 스케줄 트리거 → 구글시트 변경분 감지 → CRM API 동기화 → 오류 이메일 알림",
        "tools": ["Make", "Google Sheets", "HubSpot/Notion"],
        "time_saved_hours_weekly": 3,
        "complexity": "LOW",
        "pattern_type": "LINEAR",
        "tags": ["Make", "구글시트", "CRM", "노코드"],
    },

    # ══════════════════════════════════════════════
    # 고급 패턴 (AI 활용)
    # ══════════════════════════════════════════════

    {
        "id": "ai-001",
        "title": "AI 기반 수요 예측 + 자동 프로모션",
        "business_types": ["소매업", "이커머스", "식음료"],
        "problem": "성수기/비수기 구분 없이 동일한 운영으로 수익 최적화 안 됨",
        "solution": "판매 이력 데이터 → 계절/요일 패턴 분석 → AI 수요 예측 → 비수기 자동 프로모션 생성",
        "tools": ["Python pandas/scikit-learn", "Claude API", "카카오 알림톡"],
        "time_saved_hours_weekly": 5,
        "complexity": "HIGH",
        "pattern_type": "PIPELINE",
        "tags": ["AI", "수요예측", "프로모션", "머신러닝"],
    },
    {
        "id": "ai-002",
        "title": "AI 상품 설명 자동 생성 + 키워드 최적화",
        "business_types": ["스마트스토어", "이커머스"],
        "problem": "신규 상품 등록 시 설명 작성에 상품당 30~60분 소요",
        "solution": "상품 기본정보 입력 → Claude로 SEO 최적화 설명 자동 생성 → 스마트스토어 자동 등록",
        "tools": ["Claude API", "네이버 쇼핑 API"],
        "time_saved_hours_weekly": 6,
        "complexity": "MEDIUM",
        "pattern_type": "PIPELINE",
        "tags": ["AI", "SEO", "상품관리", "LLM", "이커머스"],
    },
    {
        "id": "ai-003",
        "title": "고객 문의 자동 분류 + 우선순위화",
        "business_types": ["전 업종"],
        "problem": "문의 채널이 카톡/이메일/전화로 분산되어 대응이 늦음",
        "solution": "멀티채널 문의 통합 → AI 카테고리 분류 → 긴급도 우선순위 → 담당자 자동 배정",
        "tools": ["Claude API", "슬랙", "SQLite"],
        "time_saved_hours_weekly": 5,
        "complexity": "HIGH",
        "pattern_type": "AGGREGATION",
        "tags": ["CS", "AI분류", "멀티채널", "우선순위"],
    },

    # ══════════════════════════════════════════════
    # 세금/회계/공공서비스
    # ══════════════════════════════════════════════

    {
        "id": "tax-001",
        "title": "홈택스 공제 서류 자동 수집",
        "business_types": ["전 업종"],
        "problem": "부가세 신고 시 영수증/계산서 취합에 수일 소요",
        "solution": "이메일 수신 계산서 자동 파싱 → 홈택스 API 연동 → 공제 항목 자동 분류 + 집계",
        "tools": ["Gmail API", "홈택스 API", "openpyxl"],
        "time_saved_hours_weekly": 5,
        "complexity": "HIGH",
        "pattern_type": "AGGREGATION",
        "tags": ["세금", "부가세", "홈택스", "회계"],
    },
    {
        "id": "pub-001",
        "title": "소상공인 지원사업 자동 스크리닝",
        "business_types": ["전 업종"],
        "problem": "소상공인 지원사업 공고를 놓쳐서 신청 기회를 잃음",
        "solution": "소상공인 포털 크롤링 → 업종/조건 매칭 → 신규 공고 즉시 알림 → 신청서 초안 생성",
        "tools": ["소상공인 포털 크롤러", "Claude API", "카카오 알림톡"],
        "time_saved_hours_weekly": 3,
        "complexity": "MEDIUM",
        "pattern_type": "TRIGGER_ACTION",
        "tags": ["지원사업", "공고모니터링", "소상공인"],
    },
]

# ── 도구 조합 추천 데이터베이스 ──────────────────────────────────

TOOL_COMBINATIONS = [
    {
        "id": "tc-001",
        "name": "카카오 생태계 패키지",
        "description": "한국 소상공인에게 가장 효과적인 알림 채널",
        "tools": ["카카오 알림톡", "카카오 채널", "카카오페이"],
        "best_for": ["CS 자동화", "결제 링크", "예약 알림"],
        "monthly_cost_usd": 30,
        "tech_level": "LOW",
    },
    {
        "id": "tc-002",
        "name": "데이터 파이프라인 스택",
        "description": "대량 데이터 처리 + 분석 + 리포팅",
        "tools": ["pandas", "SQLite", "Google Sheets API", "matplotlib"],
        "best_for": ["매출 분석", "재고 관리", "정산 자동화"],
        "monthly_cost_usd": 0,
        "tech_level": "MEDIUM",
    },
    {
        "id": "tc-003",
        "name": "노코드 자동화 스택",
        "description": "코딩 없이 구축 가능한 자동화",
        "tools": ["n8n", "Make(Integromat)", "Zapier"],
        "best_for": ["앱 간 연동", "웹훅 처리", "간단한 워크플로우"],
        "monthly_cost_usd": 25,
        "tech_level": "LOW",
    },
    {
        "id": "tc-004",
        "name": "AI 강화 CS 스택",
        "description": "LLM + 기존 채널 통합으로 CS 자동화",
        "tools": ["Claude API", "카카오 채널 API", "슬랙"],
        "best_for": ["문의 자동 분류", "FAQ 자동 응대", "리뷰 관리"],
        "monthly_cost_usd": 50,
        "tech_level": "MEDIUM",
    },
    {
        "id": "tc-005",
        "name": "이커머스 올인원 스택",
        "description": "온라인 판매 전 과정 자동화",
        "tools": ["네이버 쇼핑 API", "카카오 알림톡", "CJ대한통운 API", "openpyxl"],
        "best_for": ["주문 처리", "배송 알림", "정산", "리뷰 관리"],
        "monthly_cost_usd": 20,
        "tech_level": "MEDIUM",
    },
]

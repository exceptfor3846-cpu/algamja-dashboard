# -*- coding: utf-8 -*-
"""
주요 한국 주식 종목명 → 티커 매핑 테이블
(KOSPI: .KS, KOSDAQ: .KQ)
종목명 검색 기능에 사용 — Yahoo Finance는 한글 검색 미지원이라 로컬 목록 사용
"""

# {한글명: (티커, 거래소명)}
KOSPI_STOCKS = {
    "삼성전자":          ("005930.KS", "KOSPI"),
    "SK하이닉스":        ("000660.KS", "KOSPI"),
    "LG에너지솔루션":    ("373220.KS", "KOSPI"),
    "삼성바이오로직스":  ("207940.KS", "KOSPI"),
    "현대차":            ("005380.KS", "KOSPI"),
    "셀트리온":          ("068270.KS", "KOSPI"),
    "기아":              ("000270.KS", "KOSPI"),
    "KB금융":            ("105560.KS", "KOSPI"),
    "POSCO홀딩스":       ("005490.KS", "KOSPI"),
    "신한지주":          ("055550.KS", "KOSPI"),
    "삼성SDI":           ("006400.KS", "KOSPI"),
    "하나금융지주":      ("086790.KS", "KOSPI"),
    "현대모비스":        ("012330.KS", "KOSPI"),
    "우리금융지주":      ("316140.KS", "KOSPI"),
    "LG화학":            ("051910.KS", "KOSPI"),
    "삼성물산":          ("028260.KS", "KOSPI"),
    "카카오":            ("035720.KS", "KOSPI"),
    "NAVER":             ("035420.KS", "KOSPI"),
    "네이버":            ("035420.KS", "KOSPI"),
    "SK이노베이션":      ("096770.KS", "KOSPI"),
    "삼성전기":          ("009150.KS", "KOSPI"),
    "LG전자":            ("066570.KS", "KOSPI"),
    "포스코퓨처엠":      ("003670.KS", "KOSPI"),
    "SK텔레콤":          ("017670.KS", "KOSPI"),
    "삼성생명":          ("032830.KS", "KOSPI"),
    "현대글로비스":      ("086280.KS", "KOSPI"),
    "고려아연":          ("010130.KS", "KOSPI"),
    "에쓰오일":          ("010950.KS", "KOSPI"),
    "한화에어로스페이스":("012450.KS", "KOSPI"),
    "KT&G":              ("033780.KS", "KOSPI"),
    "두산에너빌리티":    ("034020.KS", "KOSPI"),
    "한국전력":          ("015760.KS", "KOSPI"),
    "한화솔루션":        ("009830.KS", "KOSPI"),
    "LG":                ("003550.KS", "KOSPI"),
    "롯데케미칼":        ("011170.KS", "KOSPI"),
    "SK":                ("034730.KS", "KOSPI"),
    "넷마블":            ("251270.KS", "KOSPI"),
    "엔씨소프트":        ("036570.KS", "KOSPI"),
    "현대제철":          ("004020.KS", "KOSPI"),
    "삼성화재":          ("000810.KS", "KOSPI"),
    "HMM":               ("011200.KS", "KOSPI"),
    "한국조선해양":      ("009540.KS", "KOSPI"),
    "현대중공업":        ("329180.KS", "KOSPI"),
    "대한항공":          ("003490.KS", "KOSPI"),
    "롯데쇼핑":          ("023530.KS", "KOSPI"),
    "이마트":            ("139480.KS", "KOSPI"),
    "하이브":            ("352820.KS", "KOSPI"),
    "금호석유":          ("011780.KS", "KOSPI"),
    "포스코인터내셔널":  ("047050.KS", "KOSPI"),
    "현대해상":          ("001450.KS", "KOSPI"),
    "DB손해보험":        ("005830.KS", "KOSPI"),
    "NH투자증권":        ("005940.KS", "KOSPI"),
    "미래에셋증권":      ("006800.KS", "KOSPI"),
    "키움증권":          ("039490.KS", "KOSPI"),
    "한국항공우주":      ("047810.KS", "KOSPI"),
    "두산밥캣":          ("241560.KS", "KOSPI"),
    "한화":              ("000880.KS", "KOSPI"),
    "크래프톤":          ("259960.KS", "KOSPI"),
    "카카오뱅크":        ("323410.KS", "KOSPI"),
    "카카오페이":        ("377300.KS", "KOSPI"),
    "SK바이오팜":        ("326030.KS", "KOSPI"),
    "삼성증권":          ("016360.KS", "KOSPI"),
    "CJ제일제당":        ("097950.KS", "KOSPI"),
    "한진칼":            ("180640.KS", "KOSPI"),
    "GS":                ("078930.KS", "KOSPI"),
    "한국가스공사":      ("036460.KS", "KOSPI"),
    "한국타이어앤테크놀로지": ("161390.KS", "KOSPI"),
    "OCI홀딩스":         ("010060.KS", "KOSPI"),
    "SK바이오사이언스":  ("302440.KS", "KOSPI"),
    "롯데웰푸드":        ("280360.KS", "KOSPI"),
    "현대건설":          ("000720.KS", "KOSPI"),
    "GS건설":            ("006360.KS", "KOSPI"),
    "HDC현대산업개발":   ("294870.KS", "KOSPI"),
    "효성":              ("004800.KS", "KOSPI"),
    "풍산":              ("103140.KS", "KOSPI"),
    "LIG넥스원":         ("079550.KS", "KOSPI"),
    "한화오션":          ("042660.KS", "KOSPI"),
    "삼성중공업":        ("010140.KS", "KOSPI"),
    "대우조선해양":      ("042660.KS", "KOSPI"),
    "KT":                ("030200.KS", "KOSPI"),
    "LG유플러스":        ("032640.KS", "KOSPI"),
    "롯데지주":          ("004990.KS", "KOSPI"),
    "한국콜마":          ("161890.KS", "KOSPI"),
    "아모레퍼시픽":      ("090430.KS", "KOSPI"),
    "LG생활건강":        ("051900.KS", "KOSPI"),
    "코스맥스":          ("192820.KS", "KOSPI"),
    "이노션":            ("214320.KS", "KOSPI"),
    "제일기획":          ("030000.KS", "KOSPI"),
    "삼성엔지니어링":    ("028050.KS", "KOSPI"),
    "SK에코플랜트":      ("SK에코플랜트", "KOSPI"),
    "영풍":              ("000670.KS", "KOSPI"),
    "CJ":                ("001040.KS", "KOSPI"),
    "LS ELECTRIC":       ("010120.KS", "KOSPI"),
    "LS일렉트릭":        ("010120.KS", "KOSPI"),
    "한국금융지주":      ("071050.KS", "KOSPI"),
    "메리츠금융지주":    ("138040.KS", "KOSPI"),
    "메리츠화재":        ("000060.KS", "KOSPI"),
    "두산퓨얼셀":        ("336260.KS", "KOSPI"),
    "에코프로에이치엔":  ("383310.KS", "KOSPI"),
    "HD현대":            ("267250.KS", "KOSPI"),
    "HD현대일렉트릭":    ("267260.KS", "KOSPI"),
    "HD현대마린솔루션":  ("443060.KS", "KOSPI"),
    "한화시스템":        ("272210.KS", "KOSPI"),
}

KOSDAQ_STOCKS = {
    "에코프로":          ("086520.KQ", "KOSDAQ"),
    "에코프로비엠":      ("247540.KQ", "KOSDAQ"),
    "HLB":               ("028300.KQ", "KOSDAQ"),
    "알테오젠":          ("196170.KQ", "KOSDAQ"),
    "레인보우로보틱스":  ("277810.KQ", "KOSDAQ"),
    "엘앤에프":          ("066970.KQ", "KOSDAQ"),
    "리가켐바이오":      ("141080.KQ", "KOSDAQ"),
    "씨젠":              ("096530.KQ", "KOSDAQ"),
    "카카오게임즈":      ("293490.KQ", "KOSDAQ"),
    "에스엠":            ("041510.KQ", "KOSDAQ"),
    "SM엔터테인먼트":    ("041510.KQ", "KOSDAQ"),
    "JYP Ent.":          ("035900.KQ", "KOSDAQ"),
    "JYP엔터테인먼트":   ("035900.KQ", "KOSDAQ"),
    "셀트리온헬스케어":  ("091990.KQ", "KOSDAQ"),
    "HPSP":              ("403870.KQ", "KOSDAQ"),
    "천보":              ("278280.KQ", "KOSDAQ"),
    "솔브레인":          ("357780.KQ", "KOSDAQ"),
    "리노공업":          ("058470.KQ", "KOSDAQ"),
    "오스코텍":          ("039200.KQ", "KOSDAQ"),
    "파마리서치":        ("208340.KQ", "KOSDAQ"),
    "케이엠더블유":      ("032500.KQ", "KOSDAQ"),
    "원익IPS":           ("240810.KQ", "KOSDAQ"),
    "에스티팜":          ("237690.KQ", "KOSDAQ"),
    "CJ ENM":            ("035760.KQ", "KOSDAQ"),
    "펄어비스":          ("263750.KQ", "KOSDAQ"),
    "위메이드":          ("112040.KQ", "KOSDAQ"),
    "NHN":               ("181710.KQ", "KOSDAQ"),
    "에이비엘바이오":    ("298380.KQ", "KOSDAQ"),
    "제넥신":            ("095700.KQ", "KOSDAQ"),
    "이오테크닉스":      ("039030.KQ", "KOSDAQ"),
    "테크윙":            ("089030.KQ", "KOSDAQ"),
    "컴투스":            ("078340.KQ", "KOSDAQ"),
    "HLB바이오스텝":     ("278650.KQ", "KOSDAQ"),
    "셀트리온제약":      ("068760.KQ", "KOSDAQ"),
    "고바이오랩":        ("372910.KQ", "KOSDAQ"),
    "클래시스":          ("214150.KQ", "KOSDAQ"),
    "에스디바이오센서":  ("137310.KQ", "KOSDAQ"),
    "포스코DX":          ("022100.KQ", "KOSDAQ"),
    "삼천당제약":        ("000250.KQ", "KOSDAQ"),
    "유한양행":          ("000100.KS", "KOSPI"),   # 실제 KOSPI
    "한미약품":          ("128940.KS", "KOSPI"),   # 실제 KOSPI
    "동아에스티":        ("170900.KS", "KOSPI"),   # 실제 KOSPI
    "덴티움":            ("145720.KQ", "KOSDAQ"),
    "레고켐바이오":      ("141080.KQ", "KOSDAQ"),
    "비씨엔씨":          ("365330.KQ", "KOSDAQ"),
    "인텔리안테크":      ("189300.KQ", "KOSDAQ"),
    "더블유씨피":        ("393890.KQ", "KOSDAQ"),
    "테스":              ("095610.KQ", "KOSDAQ"),
    "코미코":            ("183300.KQ", "KOSDAQ"),
    "엑스포넨셜":        ("388790.KQ", "KOSDAQ"),
    "두산테스나":        ("131970.KQ", "KOSDAQ"),
    "피에스케이":        ("319660.KQ", "KOSDAQ"),
    "NICE평가정보":       ("030190.KQ", "KOSDAQ"),
}

# 전체 통합 목록
ALL_STOCKS = {**KOSPI_STOCKS, **KOSDAQ_STOCKS}


def search_korean_stock(query: str, suffix: str = '') -> list:
    """
    한글 종목명으로 검색 (부분 일치)
    suffix: '.KS' = KOSPI만, '.KQ' = KOSDAQ만, '' = 전체
    반환: [{"ticker": str, "name": str, "exchange": str}, ...]
    """
    query = query.strip()
    if not query:
        return []

    results = []
    seen = set()

    for name, (ticker, exchange) in ALL_STOCKS.items():
        if suffix and not ticker.endswith(suffix):
            continue
        if query.lower() in name.lower():
            if ticker not in seen:
                results.append({"ticker": ticker, "name": name, "exchange": exchange})
                seen.add(ticker)

    # 정확 일치를 먼저
    results.sort(key=lambda x: (0 if x["name"] == query else 1, x["name"]))
    return results[:10]

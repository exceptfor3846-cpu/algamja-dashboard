"""
가격 조회 모듈 - yfinance(주식/선물/환율), CoinGecko(비트코인)
Windows 한글 경로 SSL 인증서 문제도 여기서 처리
"""
import os
import sys
import shutil
import tempfile
from datetime import datetime


# ─────────────────────────────────────────────
#  SSL 인증서 경로 수정 (Windows 한글 경로 대응)
#  yfinance 내부의 curl_cffi는 경로에 비ASCII 문자가
#  있으면 CA 번들을 찾지 못해 curl error 77이 발생.
#  certifi의 cacert.pem을 ASCII 경로(temp)에 복사 후
#  CURL_CA_BUNDLE / SSL_CERT_FILE 환경변수를 설정.
# ─────────────────────────────────────────────
def _fix_ssl_cert_path():
    try:
        import certifi
        orig = certifi.where()

        if orig.isascii():
            os.environ.setdefault("CURL_CA_BUNDLE", orig)
            os.environ.setdefault("SSL_CERT_FILE", orig)
            return

        if sys.platform == "win32":
            import ctypes
            buf = ctypes.create_unicode_buffer(512)
            ctypes.windll.kernel32.GetShortPathNameW(orig, buf, 512)
            short = buf.value
            if short and short.isascii():
                os.environ["CURL_CA_BUNDLE"] = short
                os.environ["SSL_CERT_FILE"] = short
                print(f"[ssl_fix] 단축 경로 적용: {short}")
                return

        dest_dir = os.path.join(tempfile.gettempdir(), "algamja_certs")
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, "cacert.pem")
        shutil.copy2(orig, dest)
        os.environ["CURL_CA_BUNDLE"] = dest
        os.environ["SSL_CERT_FILE"] = dest
        print(f"[ssl_fix] 임시 경로에 복사 완료: {dest}")

    except Exception as e:
        print(f"[ssl_fix] 경고: {e}")


_fix_ssl_cert_path()  # yfinance import 전에 반드시 실행

import yfinance as yf  # noqa: E402
import requests        # noqa: E402

from database import get_db, _save_daily_index  # noqa: E402


ASSET_LIST = ["S&P500", "NASDAQ", "KOSPI", "KOSDAQ", "비트코인", "환율(원/달러)", "금", "은"]

ASSET_SYMBOLS = {
    "S&P500":       "^GSPC",
    "NASDAQ":       "^IXIC",
    "KOSPI":        "^KS11",
    "KOSDAQ":       "^KQ11",
    "금":           "GC=F",
    "은":           "SI=F",
    "환율(원/달러)": "KRW=X",
}


def _yfinance_price(symbol: str):
    try:
        hist = yf.Ticker(symbol).history(period="5d")
        if not hist.empty:
            return round(float(hist["Close"].dropna().iloc[-1]), 2)
    except Exception as e:
        print(f"[yfinance] {symbol}: {e}")
    return None


def _bitcoin_price():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=10,
        )
        if r.ok:
            return round(r.json()["bitcoin"]["usd"], 2)
    except Exception as e:
        print(f"[coingecko] {e}")
    return None


def fetch_price(asset: str):
    """고정 자산 또는 개별종목 티커 모두 처리"""
    if asset == "비트코인":
        return _bitcoin_price()
    symbol = ASSET_SYMBOLS.get(asset)
    if symbol:
        return _yfinance_price(symbol)
    # 고정 자산 목록에 없으면 → 티커로 직접 조회 (개별종목)
    return _yfinance_price(asset)


def search_ticker_by_name(query: str, suffix: str = '') -> list:
    """
    종목명으로 검색 → [{ticker, name, exchange}] 반환
    - KOSPI/KOSDAQ(.KS/.KQ): 로컬 한국 종목 사전 사용 (Yahoo Finance는 한글 미지원)
    - 그 외: Yahoo Finance 검색
    """
    from korean_stocks import search_korean_stock

    # 1) 한국 주식: 로컬 사전 검색 (한글 입력 지원)
    if suffix in (".KS", ".KQ"):
        results = search_korean_stock(query, suffix)
        if results:
            return results
        # 로컬에 없으면 종목코드 직접 시도 (예: "005930" 입력)
        ticker_candidate = query.upper()
        if not ticker_candidate.endswith(suffix):
            ticker_candidate += suffix
        test = validate_ticker(ticker_candidate)
        if test.get("valid"):
            return [{"ticker": ticker_candidate, "name": ticker_candidate, "exchange": suffix.replace(".", "")}]
        return []

    # 2) 해외 주식: Yahoo Finance 검색 (영어 쿼리)
    _headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://finance.yahoo.com/",
    }
    for base_url in [
        "https://query1.finance.yahoo.com/v1/finance/search",
        "https://query2.finance.yahoo.com/v1/finance/search",
    ]:
        try:
            r = requests.get(
                base_url,
                params={"q": query, "quotesCount": 10, "newsCount": 0, "enableFuzzyQuery": False},
                headers=_headers,
                timeout=10,
            )
            if not r.ok:
                continue
            results = []
            for q in r.json().get("quotes", []):
                symbol = q.get("symbol", "")
                if q.get("quoteType") != "EQUITY":
                    continue
                if suffix and not symbol.endswith(suffix):
                    continue
                name     = q.get("longname") or q.get("shortname") or symbol
                exchange = q.get("exchDisp", "")
                results.append({"ticker": symbol, "name": name, "exchange": exchange})
            return results
        except Exception as e:
            print(f"[search_ticker] {base_url}: {e}")
    return []


def validate_ticker(ticker: str) -> dict:
    """티커 유효성 검사 - 이름과 현재가 반환"""
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        price = getattr(info, "last_price", None)
        if price is None:
            hist = t.history(period="5d")
            if not hist.empty:
                price = round(float(hist["Close"].dropna().iloc[-1]), 2)
        name = getattr(info, "exchange", ticker)
        if price:
            return {"valid": True, "price": round(float(price), 2), "exchange": name}
    except Exception:
        pass
    return {"valid": False}


def update_all_prices():
    print(f"[{datetime.now():%H:%M:%S}] 가격 업데이트 시작...")
    conn = get_db()
    try:
        # 1) 고정 자산 업데이트
        for asset in ASSET_LIST:
            price = fetch_price(asset)
            if price is not None:
                conn.execute(
                    "INSERT OR REPLACE INTO prices (asset_market, current_price, updated_at) VALUES (?,?,?)",
                    (asset, price, datetime.now().isoformat()),
                )
                print(f"  {asset}: {price:,.2f}")

        # 2) 예측 테이블에 있는 개별종목 업데이트
        # ticker 컬럼이 있으면 해당 티커로 가격 조회, 없으면 asset_market을 티커로 사용
        # 가격은 항상 asset_market(표시명) 기준으로 저장 → 대시보드 조인에 사용
        placeholders = ",".join("?" * len(ASSET_LIST))
        custom_rows = conn.execute(
            f"SELECT DISTINCT asset_market, ticker FROM predictions "
            f"WHERE asset_market NOT IN ({placeholders})",
            ASSET_LIST,
        ).fetchall()

        for row in custom_rows:
            display_name = row["asset_market"]
            ticker       = row["ticker"] or display_name  # ticker 없으면 asset_market을 티커로 사용
            price = _yfinance_price(ticker)
            if price is not None:
                conn.execute(
                    "INSERT OR REPLACE INTO prices (asset_market, current_price, updated_at) VALUES (?,?,?)",
                    (display_name, price, datetime.now().isoformat()),
                )
                label = f"{display_name}({ticker})" if ticker != display_name else display_name
                print(f"  {label}: {price:,.2f}")

        conn.commit()
        _save_daily_index(conn)
    except Exception as e:
        print(f"[update_prices] {e}")
    finally:
        conn.close()

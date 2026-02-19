"""
알감자지수 대시보드 - 메인 애플리케이션
Flask + SQLite + APScheduler + Telegram Bot
"""

import os
import sys
import shutil
import sqlite3
import tempfile
import threading
from datetime import datetime, date


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

        # 경로가 이미 ASCII 전용이면 그대로 사용
        if orig.isascii():
            os.environ.setdefault("CURL_CA_BUNDLE", orig)
            os.environ.setdefault("SSL_CERT_FILE", orig)
            return

        # Windows: 8.3 단축 경로 시도
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

        # 단축 경로도 한글이면 temp 디렉토리에 복사
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


from functools import wraps
from flask import Flask, render_template, request, jsonify, session
import yfinance as yf
import requests
from apscheduler.schedulers.background import BackgroundScheduler

# ─────────────────────────────────────────────
#  설정 로드 (config.py)
# ─────────────────────────────────────────────
try:
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, ADMIN_PASSWORD, SECRET_KEY
    print("[config] config.py 로드 완료")
except ImportError:
    import os
    TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
    ADMIN_PASSWORD      = os.environ.get("ADMIN_PASSWORD", "algamja2024")
    SECRET_KEY          = os.environ.get("SECRET_KEY", "algamja-secret-key-2024")
    if TELEGRAM_BOT_TOKEN:
        print("[config] 환경 변수에서 설정 로드 완료")
    else:
        print("[config] ⚠️ config.py 없음, 환경 변수도 미설정 — 텔레그램 비활성화")

DATABASE = "algamja.db"

ASSET_LIST = ["S&P500", "NASDAQ", "KOSPI", "KOSDAQ", "비트코인", "환율(원/달러)", "금"]

ASSET_SYMBOLS = {
    "S&P500":      "^GSPC",
    "NASDAQ":      "^IXIC",
    "KOSPI":       "^KS11",
    "KOSDAQ":      "^KQ11",
    "금":          "GC=F",
    "환율(원/달러)": "KRW=X",
}

app            = Flask(__name__)
app.secret_key = SECRET_KEY
scheduler      = BackgroundScheduler(daemon=True)


def require_admin(f):
    """관리자 세션 확인 데코레이터"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"error": "관리자 권한이 필요합니다"}), 403
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
#  데이터베이스
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS predictions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_market TEXT    NOT NULL,
            mention_date TEXT    NOT NULL,
            mention_price REAL   NOT NULL,
            direction    TEXT    NOT NULL,
            hit          INTEGER DEFAULT 0,
            miss         INTEGER DEFAULT 0,
            created_at   TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS prices (
            asset_market TEXT PRIMARY KEY,
            current_price REAL,
            updated_at   TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_index (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         TEXT    UNIQUE NOT NULL,
            algamja_index REAL   NOT NULL,
            recorded_at  TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('update_interval', '5')")
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  가격 조회
# ─────────────────────────────────────────────
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
    if asset == "비트코인":
        return _bitcoin_price()
    symbol = ASSET_SYMBOLS.get(asset)
    return _yfinance_price(symbol) if symbol else None


def update_all_prices():
    print(f"[{datetime.now():%H:%M:%S}] 가격 업데이트 시작...")
    conn = get_db()
    try:
        for asset in ASSET_LIST:
            price = fetch_price(asset)
            if price is not None:
                conn.execute(
                    "INSERT OR REPLACE INTO prices (asset_market, current_price, updated_at) VALUES (?,?,?)",
                    (asset, price, datetime.now().isoformat()),
                )
                print(f"  {asset}: {price:,.2f}")
        conn.commit()
        _save_daily_index(conn)
    except Exception as e:
        print(f"[update_prices] {e}")
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  알감자지수 이력 저장
# ─────────────────────────────────────────────
def _save_daily_index(conn):
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(hit),0) h, COALESCE(SUM(miss),0) m FROM predictions"
        ).fetchone()
        total = row["h"] + row["m"]
        if total > 0:
            idx   = round(row["h"] / total * 100, 2)
            today = date.today().isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO daily_index (date, algamja_index) VALUES (?,?)",
                (today, idx),
            )
            conn.commit()
    except Exception as e:
        print(f"[daily_index] {e}")


def save_daily_index():
    conn = get_db()
    try:
        _save_daily_index(conn)
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  텔레그램 전송
# ─────────────────────────────────────────────
def send_telegram(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("[telegram] ⚠️ 봇 토큰 또는 채널 ID가 설정되지 않았습니다 (config.py 확인)")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHANNEL_ID, "text": text},
            timeout=10,
        )
        if r.ok:
            print(f"[telegram] ✅ 채널 전송 성공")
        else:
            resp = r.json()
            print(f"[telegram] ❌ 전송 실패 ({r.status_code}): {resp.get('description', r.text)}")
        return r.ok
    except Exception as e:
        print(f"[telegram] ❌ 예외: {e}")
        return False


def send_dashboard_report():
    conn = get_db()
    try:
        assets = conn.execute(
            """SELECT asset_market,
                      COALESCE(SUM(hit),0)  h,
                      COALESCE(SUM(miss),0) m
               FROM predictions
               GROUP BY asset_market
               ORDER BY asset_market"""
        ).fetchall()

        overall = conn.execute(
            "SELECT COALESCE(SUM(hit),0) h, COALESCE(SUM(miss),0) m FROM predictions"
        ).fetchone()

        total   = overall["h"] + overall["m"]
        algamja = round(overall["h"] / total * 100, 1) if total else 0
        now     = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines = [
            "📊 알감자지수 대시보드",
            f"업데이트: {now}",
            "",
            "자산시장       | 방향성  | 적중률",
            "─" * 34,
        ]

        for a in assets:
            t    = a["h"] + a["m"]
            rate = f"{round(a['h']/t*100)}%" if t else "N/A"
            dir_row = conn.execute(
                "SELECT direction FROM predictions WHERE asset_market=? ORDER BY mention_date DESC LIMIT 1",
                (a["asset_market"],)
            ).fetchone()
            dir_s = (("📈 UP" if dir_row["direction"] == "UP" else "📉 DOWN") if dir_row else "  -  ")
            lines.append(f"{a['asset_market']:<12} | {dir_s:<7} | {rate}")

        lines.append("")
        lines.append(f"🥔 종합 알감자지수: {algamja}%")

        msg = "\n".join(lines)
        print(f"[report] 텔레그램 전송 시도 → 채널 {TELEGRAM_CHANNEL_ID}")
        send_telegram(msg)
    except Exception as e:
        print(f"[report] ❌ 오류: {e}")
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  스케줄러
# ─────────────────────────────────────────────
def _scheduled_job():
    update_all_prices()
    send_dashboard_report()


def get_interval() -> int:
    conn = get_db()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key='update_interval'").fetchone()
        return int(row["value"]) if row else 5
    finally:
        conn.close()


def reset_scheduler():
    try:
        for job in scheduler.get_jobs():
            job.remove()
        minutes = get_interval()
        scheduler.add_job(_scheduled_job, "interval", minutes=minutes, id="main")
        print(f"[scheduler] 업데이트 주기: {minutes}분")
    except Exception as e:
        print(f"[scheduler] {e}")


# ─────────────────────────────────────────────
#  Flask 라우트
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/predictions", methods=["GET"])
def api_get_predictions():
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT p.id, p.asset_market, p.mention_date, p.mention_price,
                      p.direction, p.hit, p.miss, p.created_at,
                      pr.current_price, pr.updated_at AS price_updated
               FROM predictions p
               LEFT JOIN prices pr ON p.asset_market = pr.asset_market
               ORDER BY p.mention_date DESC, p.id DESC"""
        ).fetchall()

        stats = conn.execute(
            "SELECT COALESCE(SUM(hit),0) h, COALESCE(SUM(miss),0) m FROM predictions"
        ).fetchone()

        total   = stats["h"] + stats["m"]
        algamja = round(stats["h"] / total * 100, 2) if total else 0

        return jsonify({
            "predictions": [dict(r) for r in rows],
            "total_hit":     stats["h"],
            "total_miss":    stats["m"],
            "algamja_index": algamja,
        })
    finally:
        conn.close()


@app.route("/api/predictions", methods=["POST"])
@require_admin
def api_add_prediction():
    d = request.json or {}
    for f in ("asset_market", "mention_date", "mention_price", "direction"):
        if f not in d:
            return jsonify({"error": f"{f} 필드가 필요합니다"}), 400

    if d["asset_market"] not in ASSET_LIST:
        return jsonify({"error": "유효하지 않은 자산시장"}), 400
    if d["direction"] not in ("UP", "DOWN"):
        return jsonify({"error": "방향성은 UP 또는 DOWN이어야 합니다"}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO predictions (asset_market, mention_date, mention_price, direction) VALUES (?,?,?,?)",
            (d["asset_market"], d["mention_date"], float(d["mention_price"]), d["direction"]),
        )
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/predictions/<int:pid>", methods=["PUT"])
@require_admin
def api_update_prediction(pid):
    d = request.json or {}
    for f in ("asset_market", "mention_date", "mention_price", "direction"):
        if f not in d:
            return jsonify({"error": f"{f} 필드가 필요합니다"}), 400
    if d["asset_market"] not in ASSET_LIST:
        return jsonify({"error": "유효하지 않은 자산시장"}), 400
    if d["direction"] not in ("UP", "DOWN"):
        return jsonify({"error": "방향성은 UP 또는 DOWN이어야 합니다"}), 400
    conn = get_db()
    try:
        conn.execute(
            "UPDATE predictions SET asset_market=?, mention_date=?, mention_price=?, direction=? WHERE id=?",
            (d["asset_market"], d["mention_date"], float(d["mention_price"]), d["direction"], pid),
        )
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/predictions/<int:pid>", methods=["DELETE"])
@require_admin
def api_delete_prediction(pid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM predictions WHERE id=?", (pid,))
        conn.commit()
        save_daily_index()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/predictions/<int:pid>/result", methods=["POST"])
@require_admin
def api_set_result(pid):
    """적중/실패 숫자 직접 입력"""
    d    = request.json or {}
    hit  = d.get("hit")
    miss = d.get("miss")
    conn = get_db()
    try:
        if hit is not None:
            conn.execute("UPDATE predictions SET hit=?  WHERE id=?", (max(0, int(hit)), pid))
        if miss is not None:
            conn.execute("UPDATE predictions SET miss=? WHERE id=?", (max(0, int(miss)), pid))
        conn.commit()
        _save_daily_index(conn)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/daily-index")
def api_daily_index():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, algamja_index FROM daily_index ORDER BY date"
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/asset-stats")
def api_asset_stats():
    """자산별 누적 적중률 요약"""
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT asset_market,
                      COALESCE(SUM(hit),0)   total_hit,
                      COALESCE(SUM(miss),0)  total_miss,
                      COUNT(*)               total_count
               FROM predictions
               GROUP BY asset_market
               ORDER BY asset_market"""
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    conn = get_db()
    try:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return jsonify({r["key"]: r["value"] for r in rows})
    finally:
        conn.close()


@app.route("/api/settings", methods=["POST"])
@require_admin
def api_update_settings():
    data = request.json or {}
    conn = get_db()
    try:
        for k, v in data.items():
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (k, str(v)))
        conn.commit()
        reset_scheduler()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/refresh", methods=["POST"])
@require_admin
def api_refresh():
    threading.Thread(target=update_all_prices, daemon=True).start()
    return jsonify({"success": True, "message": "가격 업데이트를 시작했습니다"})


# ─────────────────────────────────────────────
#  인증 라우트
# ─────────────────────────────────────────────
@app.route("/api/auth-status")
def api_auth_status():
    return jsonify({"is_admin": bool(session.get("is_admin"))})


@app.route("/api/login", methods=["POST"])
def api_login():
    pw = (request.json or {}).get("password", "")
    if pw == ADMIN_PASSWORD:
        session["is_admin"] = True
        return jsonify({"success": True})
    return jsonify({"error": "비밀번호가 틀렸습니다"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("is_admin", None)
    return jsonify({"success": True})


@app.route("/api/send-report", methods=["POST"])
@require_admin
def api_send_report():
    threading.Thread(target=send_dashboard_report, daemon=True).start()
    return jsonify({"success": True})


# ─────────────────────────────────────────────
#  텔레그램 봇 (별도 스레드)
# ─────────────────────────────────────────────
def run_telegram_bot():
    try:
        import asyncio
        from telegram import Update
        from telegram.ext import Application, CommandHandler

        async def cmd_start(update: Update, context):
            await update.message.reply_text(
                "🥔 알감자지수 봇에 오신 걸 환영합니다!\n\n"
                "📌 명령어 안내\n"
                "/add [자산] [날짜] [가격] [방향]\n"
                "예시: /add S&P500 2024-01-15 4500 UP\n\n"
                f"✅ 사용 가능한 자산:\n{chr(10).join(ASSET_LIST)}"
            )

        async def cmd_add(update: Update, context):
            args = context.args
            if len(args) < 4:
                await update.message.reply_text(
                    "사용법: /add [자산] [날짜 YYYY-MM-DD] [가격] [UP/DOWN]\n"
                    "예시: /add S&P500 2024-01-15 4500 UP"
                )
                return

            asset, date_str, price_str, direction = args[0], args[1], args[2], args[3].upper()

            if asset not in ASSET_LIST:
                await update.message.reply_text(f"유효한 자산: {', '.join(ASSET_LIST)}")
                return
            if direction not in ("UP", "DOWN"):
                await update.message.reply_text("방향성은 UP 또는 DOWN 이어야 합니다")
                return
            try:
                price = float(price_str)
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError as e:
                await update.message.reply_text(f"입력 오류: {e}")
                return

            conn = get_db()
            try:
                conn.execute(
                    "INSERT INTO predictions (asset_market, mention_date, mention_price, direction) VALUES (?,?,?,?)",
                    (asset, date_str, price, direction),
                )
                conn.commit()
                await update.message.reply_text(
                    f"✅ 추가 완료!\n"
                    f"자산: {asset}\n"
                    f"날짜: {date_str}\n"
                    f"가격: {price:,.2f}\n"
                    f"방향: {'📈' if direction=='UP' else '📉'} {direction}"
                )
            except Exception as e:
                await update.message.reply_text(f"DB 오류: {e}")
            finally:
                conn.close()

        async def cmd_status(update: Update, context):
            conn = get_db()
            try:
                stats = conn.execute(
                    "SELECT COALESCE(SUM(hit),0) h, COALESCE(SUM(miss),0) m, COUNT(*) c FROM predictions"
                ).fetchone()
                total = stats["h"] + stats["m"]
                idx   = round(stats["h"] / total * 100, 1) if total else 0
                await update.message.reply_text(
                    f"📊 현재 알감자지수 현황\n"
                    f"총 예측: {stats['c']}건\n"
                    f"✅ 적중: {stats['h']}  ❌ 실패: {stats['m']}\n"
                    f"🥔 알감자지수: {idx}%"
                )
            finally:
                conn.close()

        async def error_handler(update, context):
            from telegram.error import Conflict, NetworkError
            if isinstance(context.error, Conflict):
                print("[telegram] 충돌 감지: 이미 실행 중인 봇 인스턴스가 있습니다.")
                print("[telegram] 이전 인스턴스를 종료하거나 잠시 후 재시도하세요.")
                # stop() 호출 시 run_polling()과 충돌하므로 로그만 출력
            elif isinstance(context.error, NetworkError):
                pass  # 네트워크 오류는 자동 재시도되므로 무시
            else:
                print(f"[telegram] 오류: {context.error}")

        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start",  cmd_start))
        application.add_handler(CommandHandler("add",    cmd_add))
        application.add_handler(CommandHandler("status", cmd_status))
        application.add_error_handler(error_handler)
        print("[telegram] 봇 폴링 시작")
        application.run_polling(drop_pending_updates=True)

    except Exception as e:
        from telegram.error import Conflict
        if isinstance(e, Conflict):
            print("[telegram bot] 충돌: 이미 실행 중인 봇이 있습니다. 텔레그램 봇 기능을 비활성화합니다.")
        else:
            print(f"[telegram bot] 오류: {e}")


# ─────────────────────────────────────────────
#  엔트리포인트
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("🥔 알감자지수 서버 시작 중...")
    init_db()

    # 초기 가격 로딩 (백그라운드)
    threading.Thread(target=update_all_prices, daemon=True).start()

    # 스케줄러 시작
    reset_scheduler()
    scheduler.start()

    # 텔레그램 봇 (별도 스레드)
    threading.Thread(target=run_telegram_bot, daemon=True).start()

    print("✅ 서버 준비 완료 → http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

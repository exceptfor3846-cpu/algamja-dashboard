"""
알감자지수 대시보드 - 메인 진입점
Flask 앱 생성 + Blueprint 등록 + 서버 초기화
세부 기능은 각 모듈에서 관리:
  settings.py     - 설정 로드 (config.py / 환경변수)
  database.py     - SQLite 연결 및 초기화
  prices.py       - 자산 가격 조회 (yfinance, CoinGecko)
  telegram_bot.py - 텔레그램 전송 및 봇 폴링
  scheduler.py    - APScheduler 주기적 업데이트
  routes.py       - 모든 Flask API 라우트
"""
import os
import threading

from flask import Flask

from settings import SECRET_KEY
from database import init_db
from prices import update_all_prices
from scheduler import scheduler, reset_scheduler
from telegram_bot import run_telegram_bot
from routes import bp

# ─────────────────────────────────────────────
#  Flask 앱 생성 및 Blueprint 등록
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.register_blueprint(bp)

# ─────────────────────────────────────────────
#  앱 초기화 (gunicorn / python 모두 실행)
# ─────────────────────────────────────────────
print("🥔 알감자지수 서버 시작 중...")
init_db()
threading.Thread(target=update_all_prices, daemon=True).start()
reset_scheduler()
scheduler.start()
threading.Thread(target=run_telegram_bot, daemon=True).start()

# ─────────────────────────────────────────────
#  직접 실행 시 (python app.py / py app.py)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"✅ 서버 준비 완료 → http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

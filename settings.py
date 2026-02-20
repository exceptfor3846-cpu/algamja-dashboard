"""
설정 로드 모듈 - config.py(로컬) 또는 환경변수(Railway) 에서 불러옴
"""
import os

try:
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, ADMIN_PASSWORD, SECRET_KEY
    print("[config] config.py 로드 완료")
except ImportError:
    TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
    ADMIN_PASSWORD      = os.environ.get("ADMIN_PASSWORD", "algamja2024")
    SECRET_KEY          = os.environ.get("SECRET_KEY", "algamja-secret-key-2024")
    if TELEGRAM_BOT_TOKEN:
        print("[config] 환경 변수에서 설정 로드 완료")
    else:
        print("[config] ⚠️ config.py 없음, 환경 변수도 미설정 — 텔레그램 비활성화")

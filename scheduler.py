"""
스케줄러 모듈 - APScheduler 기반 주기적 가격 업데이트 + 텔레그램 리포트
"""
from apscheduler.schedulers.background import BackgroundScheduler
from database import get_db

scheduler = BackgroundScheduler(daemon=True)


def _scheduled_job():
    """주기적으로 실행되는 작업: 가격 업데이트 → 텔레그램 리포트"""
    from prices import update_all_prices
    from telegram_bot import send_dashboard_report
    update_all_prices()
    send_dashboard_report()


def get_interval() -> int:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key='update_interval'"
        ).fetchone()
        return int(row["value"]) if row else 5
    finally:
        conn.close()


def reset_scheduler():
    """설정된 주기로 스케줄러 재설정"""
    try:
        for job in scheduler.get_jobs():
            job.remove()
        minutes = get_interval()
        scheduler.add_job(_scheduled_job, "interval", minutes=minutes, id="main")
        print(f"[scheduler] 업데이트 주기: {minutes}분")
    except Exception as e:
        print(f"[scheduler] {e}")

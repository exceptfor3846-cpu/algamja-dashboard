"""
텔레그램 모듈 - 메시지 전송, 대시보드 리포트, 봇 폴링
"""
import asyncio
import requests
from datetime import datetime

from database import get_db
from settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID
from prices import ASSET_LIST

DASHBOARD_URL = "https://algamja-dashboard-production.up.railway.app/"


def send_telegram(text: str, parse_mode: str = None) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("[telegram] ⚠️ 봇 토큰 또는 채널 ID가 설정되지 않았습니다 (config.py 확인)")
        return False
    try:
        payload = {"chat_id": TELEGRAM_CHANNEL_ID, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json=payload,
            timeout=10,
        )
        if r.ok:
            print("[telegram] ✅ 채널 전송 성공")
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
        lines.append(
            f'🥔 자세한 알감자지수를 보고싶다면 : '
            f'<a href="{DASHBOARD_URL}">알감자지수 대시보드 바로가기</a>'
        )

        msg = "\n".join(lines)
        print(f"[report] 텔레그램 전송 시도 → 채널 {TELEGRAM_CHANNEL_ID}")
        send_telegram(msg, parse_mode="HTML")
    except Exception as e:
        print(f"[report] ❌ 오류: {e}")
    finally:
        conn.close()


def run_telegram_bot():
    try:
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

            asset, date_str, price_str, direction = (
                args[0], args[1], args[2], args[3].upper()
            )

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
                    f"방향: {'📈' if direction == 'UP' else '📉'} {direction}"
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
            elif isinstance(context.error, NetworkError):
                pass  # 네트워크 오류는 자동 재시도
            else:
                print(f"[telegram] 오류: {context.error}")

        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start",  cmd_start))
        application.add_handler(CommandHandler("add",    cmd_add))
        application.add_handler(CommandHandler("status", cmd_status))
        application.add_error_handler(error_handler)

        async def _run():
            await application.initialize()
            await application.start()
            await application.updater.start_polling(drop_pending_updates=True)
            print("[telegram] 봇 폴링 시작")
            await asyncio.sleep(float("inf"))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()

    except Exception as e:
        from telegram.error import Conflict
        if isinstance(e, Conflict):
            print("[telegram bot] 충돌: 이미 실행 중인 봇이 있습니다. 봇 기능 비활성화.")
        else:
            print(f"[telegram bot] 오류: {e}")

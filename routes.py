"""
Flask 라우트 모듈 - 모든 API 엔드포인트 + 인증 데코레이터
Blueprint로 구성하여 app.py에서 등록
"""
import threading
from functools import wraps

from flask import Blueprint, render_template, request, jsonify, session

from settings import ADMIN_PASSWORD
from database import get_db, save_daily_index, _save_daily_index
from prices import ASSET_LIST, update_all_prices, validate_ticker, search_ticker_by_name
from telegram_bot import send_dashboard_report
from scheduler import reset_scheduler

bp = Blueprint("main", __name__)


def require_admin(f):
    """관리자 세션 확인 데코레이터"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"error": "관리자 권한이 필요합니다"}), 403
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
#  페이지
# ─────────────────────────────────────────────
@bp.route("/health")
def health():
    return "ok", 200


@bp.route("/")
def index():
    return render_template("index.html")


# ─────────────────────────────────────────────
#  예측 API
# ─────────────────────────────────────────────
@bp.route("/api/predictions", methods=["GET"])
def api_get_predictions():
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT p.id, p.asset_market, p.ticker, p.mention_date, p.mention_price,
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
            "predictions":  [dict(r) for r in rows],
            "total_hit":    stats["h"],
            "total_miss":   stats["m"],
            "algamja_index": algamja,
        })
    finally:
        conn.close()


@bp.route("/api/search-ticker-name")
def api_search_ticker_name():
    """종목명 검색 (KOSPI/KOSDAQ용 — 이름 → 티커 목록 반환)"""
    q      = request.args.get("q", "").strip()
    suffix = request.args.get("suffix", "")
    if not q:
        return jsonify([])
    return jsonify(search_ticker_by_name(q, suffix))


@bp.route("/api/validate-ticker", methods=["POST"])
@require_admin
def api_validate_ticker():
    """개별종목 티커 유효성 검사"""
    ticker = (request.json or {}).get("ticker", "").strip().upper()
    if not ticker:
        return jsonify({"valid": False, "error": "티커를 입력하세요"})
    result = validate_ticker(ticker)
    return jsonify(result)


@bp.route("/api/predictions", methods=["POST"])
@require_admin
def api_add_prediction():
    d = request.json or {}
    for field in ("asset_market", "mention_date", "mention_price", "direction"):
        if field not in d:
            return jsonify({"error": f"{field} 필드가 필요합니다"}), 400

    if not d["asset_market"].strip():
        return jsonify({"error": "자산시장을 선택하거나 티커를 입력하세요"}), 400
    if d["direction"] not in ("UP", "DOWN"):
        return jsonify({"error": "방향성은 UP 또는 DOWN이어야 합니다"}), 400

    ticker = (d.get("ticker") or "").strip() or None  # 없으면 NULL로 저장
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO predictions (asset_market, ticker, mention_date, mention_price, direction) VALUES (?,?,?,?,?)",
            (d["asset_market"], ticker, d["mention_date"], float(d["mention_price"]), d["direction"]),
        )
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@bp.route("/api/predictions/<int:pid>", methods=["PUT"])
@require_admin
def api_update_prediction(pid):
    d = request.json or {}
    for field in ("asset_market", "mention_date", "mention_price", "direction"):
        if field not in d:
            return jsonify({"error": f"{field} 필드가 필요합니다"}), 400
    if not d["asset_market"].strip():
        return jsonify({"error": "자산시장을 선택하거나 종목명을 입력하세요"}), 400
    if d["direction"] not in ("UP", "DOWN"):
        return jsonify({"error": "방향성은 UP 또는 DOWN이어야 합니다"}), 400

    ticker = (d.get("ticker") or "").strip() or None
    conn = get_db()
    try:
        conn.execute(
            "UPDATE predictions SET asset_market=?, ticker=?, mention_date=?, mention_price=?, direction=? WHERE id=?",
            (d["asset_market"], ticker, d["mention_date"], float(d["mention_price"]), d["direction"], pid),
        )
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@bp.route("/api/predictions/<int:pid>", methods=["DELETE"])
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


@bp.route("/api/predictions/<int:pid>/result", methods=["POST"])
@require_admin
def api_set_result(pid):
    """적중/실패 숫자 직접 입력"""
    d    = request.json or {}
    hit  = d.get("hit")
    miss = d.get("miss")
    conn = get_db()
    try:
        if hit is not None:
            conn.execute("UPDATE predictions SET hit=?  WHERE id=?", (max(0, int(hit)),  pid))
        if miss is not None:
            conn.execute("UPDATE predictions SET miss=? WHERE id=?", (max(0, int(miss)), pid))
        conn.commit()
        _save_daily_index(conn)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  통계 / 지수 API
# ─────────────────────────────────────────────
@bp.route("/api/daily-index")
def api_daily_index():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, algamja_index FROM daily_index ORDER BY date"
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@bp.route("/api/asset-stats")
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


# ─────────────────────────────────────────────
#  설정 API
# ─────────────────────────────────────────────
@bp.route("/api/settings", methods=["GET"])
def api_get_settings():
    conn = get_db()
    try:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return jsonify({r["key"]: r["value"] for r in rows})
    finally:
        conn.close()


@bp.route("/api/settings", methods=["POST"])
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


@bp.route("/api/refresh", methods=["POST"])
@require_admin
def api_refresh():
    threading.Thread(target=update_all_prices, daemon=True).start()
    return jsonify({"success": True, "message": "가격 업데이트를 시작했습니다"})


# ─────────────────────────────────────────────
#  인증 API
# ─────────────────────────────────────────────
@bp.route("/api/auth-status")
def api_auth_status():
    return jsonify({"is_admin": bool(session.get("is_admin"))})


@bp.route("/api/login", methods=["POST"])
def api_login():
    pw = (request.json or {}).get("password", "")
    if pw == ADMIN_PASSWORD:
        session["is_admin"] = True
        return jsonify({"success": True})
    return jsonify({"error": "비밀번호가 틀렸습니다"}), 401


@bp.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("is_admin", None)
    return jsonify({"success": True})


@bp.route("/api/send-report", methods=["POST"])
@require_admin
def api_send_report():
    threading.Thread(target=send_dashboard_report, daemon=True).start()
    return jsonify({"success": True})

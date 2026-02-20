"""
데이터베이스 모듈 - SQLite 연결, 초기화, 데이터 접근
"""
import os
import sqlite3
from datetime import date


def _resolve_db_path():
    """DATABASE_PATH 환경변수 → 쓰기 가능 여부 확인 → 불가 시 앱 디렉토리 대체"""
    path = os.environ.get("DATABASE_PATH", "algamja.db")
    db_dir = os.path.dirname(os.path.abspath(path))
    try:
        os.makedirs(db_dir, exist_ok=True)
        test = os.path.join(db_dir, ".write_test")
        with open(test, "w") as f:
            f.write("ok")
        os.remove(test)
        return path
    except (PermissionError, OSError):
        fallback = os.path.join(os.path.dirname(os.path.abspath(__file__)), "algamja.db")
        print(f"[db] '{db_dir}' 쓰기 불가 → 앱 디렉토리로 대체: {fallback}")
        return fallback


DATABASE = _resolve_db_path()


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS predictions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_market  TEXT    NOT NULL,
            mention_date  TEXT    NOT NULL,
            mention_price REAL    NOT NULL,
            direction     TEXT    NOT NULL,
            hit           INTEGER DEFAULT 0,
            miss          INTEGER DEFAULT 0,
            created_at    TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS prices (
            asset_market  TEXT PRIMARY KEY,
            current_price REAL,
            updated_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_index (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            date          TEXT    UNIQUE NOT NULL,
            algamja_index REAL    NOT NULL,
            recorded_at   TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('update_interval', '5')")
    conn.commit()
    conn.close()


def _save_daily_index(conn):
    """열린 커넥션을 받아 오늘 날짜 알감자지수를 daily_index 테이블에 저장"""
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
    """새 커넥션을 열어 daily_index를 저장 (외부 호출용)"""
    conn = get_db()
    try:
        _save_daily_index(conn)
    finally:
        conn.close()

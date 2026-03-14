import sqlite3
import hashlib
from datetime import datetime
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_tours (
                hash        TEXT PRIMARY KEY,
                operator    TEXT,
                hotel       TEXT,
                destination TEXT,
                price       REAL,
                nights      INTEGER,
                departure   TEXT,
                url         TEXT,
                sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id   INTEGER PRIMARY KEY,
                username  TEXT,
                active    INTEGER DEFAULT 1,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                hotel       TEXT,
                operator    TEXT,
                price       REAL,
                recorded_at DATE DEFAULT (date('now')),
                PRIMARY KEY (hotel, operator, recorded_at)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                chat_id      INTEGER PRIMARY KEY,
                interval_min INTEGER DEFAULT 30,
                meal_filter  TEXT    DEFAULT 'any',
                stars_min    INTEGER DEFAULT 3,
                stars_max    INTEGER DEFAULT 5,
                city_filter  TEXT    DEFAULT 'all',
                price_max    INTEGER DEFAULT 9999,
                days_filter  INTEGER DEFAULT 180
            )
        """)
        conn.commit()

    # ✅ Автомиграция — добавляем колонки если их нет (не ломает старую БД)
    _migrate()


def _migrate():
    """Добавляет новые колонки в существующую БД если их ещё нет."""
    migrations = [
        ("user_settings", "days_filter",  "INTEGER DEFAULT 180"),
        ("user_settings", "interval_min", "INTEGER DEFAULT 30"),
        ("user_settings", "meal_filter",  "TEXT DEFAULT 'any'"),
        ("user_settings", "stars_min",    "INTEGER DEFAULT 3"),
        ("user_settings", "stars_max",    "INTEGER DEFAULT 5"),
        ("user_settings", "city_filter",  "TEXT DEFAULT 'all'"),
        ("user_settings", "price_max",    "INTEGER DEFAULT 9999"),
    ]
    with get_conn() as conn:
        for table, col, definition in migrations:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
                conn.commit()
            except Exception:
                pass  # колонка уже существует — игнорируем


# ── Хэш тура ─────────────────────────────────────────────────

def tour_hash(tour: dict) -> str:
    key = f"{tour['operator']}|{tour['hotel']}|{tour['price']}|{tour.get('departure_date','')}"
    return hashlib.md5(key.encode()).hexdigest()


def is_sent(tour: dict) -> bool:
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM sent_tours WHERE hash=?", (tour_hash(tour),)
        ).fetchone() is not None


def mark_sent(tour: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO sent_tours
              (hash,operator,hotel,destination,price,nights,departure,url)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            tour_hash(tour),
            tour.get("operator",""), tour.get("hotel",""),
            tour.get("destination",""), tour.get("price",0),
            tour.get("nights",0), tour.get("departure_date",""),
            tour.get("url",""),
        ))
        conn.commit()


# ── Цены ─────────────────────────────────────────────────────

def record_price(hotel: str, operator: str, price: float):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO price_history (hotel, operator, price)
            VALUES (?, ?, ?)
        """, (hotel, operator, price))
        conn.commit()


def get_yesterday_price(hotel: str, operator: str):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT price FROM price_history
            WHERE hotel=? AND operator=?
              AND recorded_at = date('now', '-1 day')
        """, (hotel, operator)).fetchone()
        return float(row["price"]) if row else None


# ── Пользователи ─────────────────────────────────────────────

def add_user(chat_id: int, username: str = ""):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO users (chat_id,username) VALUES (?,?)", (chat_id, username))
        conn.execute("UPDATE users SET active=1 WHERE chat_id=?", (chat_id,))
        conn.commit()
    _ensure_settings(chat_id)


def remove_user(chat_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET active=0 WHERE chat_id=?", (chat_id,))
        conn.commit()


def get_active_users() -> list:
    with get_conn() as conn:
        return [r["chat_id"] for r in conn.execute(
            "SELECT chat_id FROM users WHERE active=1"
        ).fetchall()]


def get_recent_tours(limit=5) -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM sent_tours ORDER BY sent_at DESC LIMIT ?", (limit,)
        ).fetchall()]


# ── Настройки ────────────────────────────────────────────────

def _ensure_settings(chat_id: int):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO user_settings (chat_id) VALUES (?)", (chat_id,))
        conn.commit()


def get_settings(chat_id: int) -> dict:
    _ensure_settings(chat_id)
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM user_settings WHERE chat_id=?", (chat_id,)).fetchone()
        return dict(row) if row else {}


def set_setting(chat_id: int, key: str, value):
    _ensure_settings(chat_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE user_settings SET {key}=? WHERE chat_id=?", (value, chat_id))
        conn.commit()


def is_paused(chat_id: int) -> bool:
    return False


def pause_user(chat_id: int, minutes: int):
    pass


def unpause_user(chat_id: int):
    pass

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
                image_url   TEXT    DEFAULT '',
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
                chat_id       INTEGER PRIMARY KEY,
                interval_min  INTEGER DEFAULT 360,
                meal_filter   TEXT    DEFAULT 'ai,uai',
                stars_min     INTEGER DEFAULT 4,
                stars_max     INTEGER DEFAULT 5,
                city_filter   TEXT    DEFAULT 'all',
                price_max     INTEGER DEFAULT 499,
                price_min     INTEGER DEFAULT 0,
                days_filter   INTEGER DEFAULT 14,
                chains_filter TEXT    DEFAULT 'barcelo,baron,domina,hilton,jaz,pickalbatros,rixos,steigenberger,sunrise,titanic',
                price_ranges  TEXT    DEFAULT '0-299,300-499'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hotel_images (
                hotel_url   TEXT PRIMARY KEY,
                image_url   TEXT,
                cached_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    _migrate()


def _migrate():
    migrations = [
        ("user_settings", "days_filter",  "INTEGER DEFAULT 14"),
        ("user_settings", "interval_min", "INTEGER DEFAULT 360"),
        ("user_settings", "meal_filter",  "TEXT DEFAULT 'ai,uai'"),
        ("user_settings", "stars_min",    "INTEGER DEFAULT 4"),
        ("user_settings", "stars_max",    "INTEGER DEFAULT 5"),
        ("user_settings", "city_filter",  "TEXT DEFAULT 'all'"),
        ("user_settings", "price_max",     "INTEGER DEFAULT 499"),
        ("user_settings", "price_min",     "INTEGER DEFAULT 0"),
        ("user_settings", "chains_filter", "TEXT DEFAULT 'barcelo,baron,domina,hilton,jaz,pickalbatros,rixos,steigenberger,sunrise,titanic'"),
        ("user_settings", "price_ranges",  "TEXT DEFAULT '0-299,300-499'"),
        ("sent_tours",    "image_url",     "TEXT DEFAULT ''"),
    ]
    with get_conn() as conn:
        for table, col, definition in migrations:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
                conn.commit()
            except Exception:
                pass


# ── Хэш тура ─────────────────────────────────────────────────
# Хэш включает дату вылета — один и тот же тур не шлётся дважды
# в одну проверку, но при следующей проверке шлётся снова
# (sent_tours очищается каждые 24 часа через cleanup_old_sent)

def tour_hash(tour: dict) -> str:
    key = f"{tour['operator']}|{tour['hotel']}|{tour.get('departure_date','')}"
    return hashlib.md5(key.encode()).hexdigest()


def is_sent(tour: dict) -> bool:
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM sent_tours WHERE hash=?", (tour_hash(tour),)
        ).fetchone() is not None


def mark_sent(tour: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO sent_tours
              (hash,operator,hotel,destination,price,nights,departure,url,image_url,sent_at)
            VALUES (?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
        """, (
            tour_hash(tour),
            tour.get("operator",""), tour.get("hotel",""),
            tour.get("destination",""), tour.get("price",0),
            tour.get("nights",0), tour.get("departure_date",""),
            tour.get("url",""), tour.get("image",""),
        ))
        conn.commit()


def cleanup_old_sent(hours: int = 0):  # 0 = чистить при каждой проверке (режим разработки)
    """Удаляет записи старше N часов — чтобы туры снова присылались."""
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM sent_tours
            WHERE sent_at < datetime('now', ? || ' hours')
        """, (f"-{hours}",))
        deleted = conn.execute("SELECT changes()").fetchone()[0]
        conn.commit()
    return deleted


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
        rows = conn.execute(
            "SELECT * FROM sent_tours ORDER BY sent_at DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for r in rows:
            t = dict(r)
            # _send_tour ждёт поле "image", а в БД хранится "image_url"
            t["image"] = t.get("image_url") or ""
            result.append(t)
        return result


# ── Настройки ────────────────────────────────────────────────

def reset_settings(chat_id: int):
    """Сбрасывает настройки пользователя на дефолтные."""
    with get_conn() as conn:
        conn.execute("DELETE FROM user_settings WHERE chat_id=?", (chat_id,))
        conn.commit()
    _ensure_settings(chat_id)


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


def get_cached_image(hotel_url: str) -> str:
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT image_url FROM hotel_images WHERE hotel_url=?", (hotel_url,)
            ).fetchone()
            return row["image_url"] if row else None
    except Exception:
        return None


def cache_image(hotel_url: str, image_url: str):
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO hotel_images (hotel_url, image_url) VALUES (?,?)",
                (hotel_url, image_url)
            )
            conn.commit()
    except Exception:
        pass


def pause_user(chat_id: int, minutes: int):
    pass


def unpause_user(chat_id: int):
    pass

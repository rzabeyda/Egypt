import os
from dotenv import load_dotenv
load_dotenv()

# ============================================================
#  EGYPT TOUR BOT — CONFIG
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# Заполни после первого /myid
ALLOWED_USERS = []   # пример: [123456789]

# ── Глобальные дефолты ──────────────────────────────────────
MAX_PRICE_EUR            = 600
MIN_NIGHTS               = 7
MAX_DAYS_UNTIL_DEPARTURE = 7
DEPARTURE_AIRPORT        = "TLL"

EGYPT_KEYWORDS = [
    "egypt", "hurghada", "sharm", "hurgada",
    "египет", "хургада", "шарм",
    "EG", "HRG", "SSH",
]

# Фильтр по списку отелей отключён — принимаем любые 4-5★
GOOD_HOTELS = []

# ── Расписание ─────────────────────────────────────────────
CHECK_INTERVAL_MINUTES = 30

# ── Пути ───────────────────────────────────────────────────
DB_PATH  = "data/tours.db"
LOG_PATH = "logs/bot.log"

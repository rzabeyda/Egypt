from datetime import datetime
from config import MIN_NIGHTS, GOOD_HOTELS, EGYPT_KEYWORDS

ALL_INCLUSIVE_KEYWORDS = ["все включено", "all inclusive", "all-inclusive", " ai", "ai ", "uai", "ultra all"]
ULTRA_AI_KEYWORDS      = ["uai", "ultra all", "ultra-all"]
BREAKFAST_KEYWORDS     = [" bb", "bb ", "bed & breakfast", "bed and breakfast", "breakfast", "завтраки", "завтрак"]
ROOM_ONLY_KEYWORDS     = [" ro", "ro ", "room only", "без питания"]
HALF_BOARD_KEYWORDS    = [" hb", "hb ", "half board", "полупансион"]


def is_egypt(destination: str) -> bool:
    d = destination.lower()
    return any(k.lower() in d for k in EGYPT_KEYWORDS)


def is_good_hotel(name: str) -> bool:
    if not GOOD_HOTELS:
        return True
    n = name.lower()
    return any(h.strip().lower() in n for h in GOOD_HOTELS)


def _meal_matches(meal_plan, meal_filter: str) -> bool:
    m = " " + str(meal_plan or "").lower() + " "
    if meal_filter == "any":
        return True
    elif meal_filter == "uai":
        return any(k in m for k in ULTRA_AI_KEYWORDS)
    elif meal_filter in ("ai,uai", "ai"):
        return any(k in m for k in ALL_INCLUSIVE_KEYWORDS)
    elif meal_filter == "bb":
        return any(k in m for k in BREAKFAST_KEYWORDS)
    elif meal_filter == "ro":
        return any(k in m for k in ROOM_ONLY_KEYWORDS)
    elif meal_filter == "hb":
        return any(k in m for k in HALF_BOARD_KEYWORDS)
    return True


def is_good_stars(stars, min_stars=3, max_stars=5) -> bool:
    try:
        s = int(str(stars))
        if s >= 100:
            s = s // 100
        return min_stars <= s <= max_stars
    except Exception:
        return False


def is_within_days(departure_date: str, max_days: int) -> bool:
    """Вылет в ближайшие max_days дней."""
    if not departure_date:
        return True
    try:
        dep = datetime.strptime(departure_date[:10], "%Y-%m-%d")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        delta = (dep - today).days
        return 0 <= delta <= max_days
    except Exception:
        return True


def is_right_city(destination: str, city_filter: str) -> bool:
    if city_filter == "all":
        return True
    d = destination.lower()
    if city_filter == "hrg":
        return any(k in d for k in ["хургада", "hurghada", "hrg"])
    if city_filter == "ssh":
        return any(k in d for k in ["шарм", "sharm", "ssh"])
    return True


def passes_filters(tour: dict, settings: dict = None) -> bool:
    from config import MAX_PRICE_EUR

    # Дефолты — максимально широкие чтобы ничего не резать без явного выбора
    price_max = int(settings.get("price_max",  9999))  if settings else MAX_PRICE_EUR
    stars_min = int(settings.get("stars_min",  3))     if settings else 3
    stars_max = int(settings.get("stars_max",  5))     if settings else 5
    city_f    = settings.get("city_filter",  "all")    if settings else "all"
    meal_f    = settings.get("meal_filter",  "any")    if settings else "any"
    days_f    = int(settings.get("days_filter", 180))  if settings else 180

    # Цена
    if tour.get("price", 9999) > price_max:
        return False
    if tour.get("price", 0) <= 0:
        return False

    # Минимум ночей
    nights = tour.get("nights", 0)
    if nights > 0 and nights < MIN_NIGHTS:
        return False

    # Египет
    dest_str = tour.get("destination", "") + " " + tour.get("hotel", "")
    if not is_egypt(dest_str):
        return False

    # Список отелей (если включён)
    if not is_good_hotel(tour.get("hotel", "")):
        return False

    # Питание
    if not _meal_matches(tour.get("meal_plan", ""), meal_f):
        return False

    # Звёзды
    if not is_good_stars(tour.get("stars", 0), stars_min, stars_max):
        return False

    # Город
    if not is_right_city(tour.get("destination", ""), city_f):
        return False

    # Дни до вылета — берём из настроек пользователя
    if not is_within_days(tour.get("departure_date", ""), days_f):
        return False

    return True

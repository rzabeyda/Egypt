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
    if meal_filter == "any":
        return True
    # Если питание не указано — не режем тур
    if not meal_plan or str(meal_plan).strip() == "":
        return True
    m = " " + str(meal_plan or "").lower() + " "
    if meal_filter == "uai":
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
    import logging
    log = logging.getLogger(__name__)

    price_max    = int(settings.get("price_max",  9999))  if settings else MAX_PRICE_EUR
    price_min    = int(settings.get("price_min",  0))     if settings else 0
    price_ranges = settings.get("price_ranges", "any")    if settings else "any"
    stars_min = int(settings.get("stars_min",  3))     if settings else 3
    stars_max = int(settings.get("stars_max",  5))     if settings else 5
    city_f    = settings.get("city_filter",  "all")    if settings else "all"
    meal_f    = settings.get("meal_filter",  "any")    if settings else "any"
    days_f    = int(settings.get("days_filter", 180))  if settings else 180
    chains_f  = settings.get("chains_filter", "any")   if settings else "any"

    price = tour.get("price", 0)
    if price <= 0:
        return False

    if price_ranges != "any":
        # Проверяем попадает ли цена хотя бы в один из выбранных диапазонов
        in_range = False
        for rng in price_ranges.split(","):
            rng = rng.strip()
            if "-" in rng:
                parts = rng.split("-")
                rmin, rmax = int(parts[0]), int(parts[1])
                if rmin <= price <= rmax:
                    in_range = True
                    break
        if not in_range:
            return False
    else:
        # Старая логика price_min/price_max как fallback
        if price > price_max:
            return False
        if price_min > 0 and price < price_min:
            return False

    nights = tour.get("nights", 0)
    if nights > 0 and nights < MIN_NIGHTS:
        log.info(f"ФИЛЬТР ночей мало: {nights} | {tour.get('hotel','')}")
        return False

    dest_str = tour.get("destination", "") + " " + tour.get("hotel", "")
    if not is_egypt(dest_str):
        log.info(f"ФИЛЬТР не Египет: {dest_str[:50]}")
        return False

    if not is_good_hotel(tour.get("hotel", "")):
        log.info(f"ФИЛЬТР отель не в списке: {tour.get('hotel','')}")
        return False

    if not _meal_matches(tour.get("meal_plan", ""), meal_f):
        return False

    if not is_good_stars(tour.get("stars", 0), stars_min, stars_max):
        log.info(f"ФИЛЬТР звёзды: {tour.get('stars',0)} не в {stars_min}-{stars_max} | {tour.get('hotel','')}")
        return False

    if not is_right_city(tour.get("destination", ""), city_f):
        log.info(f"ФИЛЬТР город: {tour.get('destination','')} | {city_f}")
        return False

    if not is_within_days(tour.get("departure_date", ""), days_f):
        log.info(f"ФИЛЬТР дни: {tour.get('departure_date','')} | max={days_f}")
        return False

    if not matches_chains(tour.get("hotel", ""), chains_f):
        return False

    return True


# Сети отелей — ключевые слова для поиска в названии
HOTEL_CHAINS = {
    "rixos":        ["rixos"],
    "jaz":          ["jaz"],
    "pickalbatros": ["pickalbatros", "albatros"],
    "sunrise":      ["sunrise"],
    "steigenberger":["steigenberger"],
    "hilton":       ["hilton"],
    "barcelo":      ["barcelo", "barceló"],
    "domina":       ["domina"],
    "baron":        ["baron"],
    "titanic":      ["titanic"],
}


def matches_chains(hotel_name: str, chains_filter: str) -> bool:
    """chains_filter — строка через запятую, напр. 'sunrise,hilton' или 'any'"""
    if not chains_filter or chains_filter == "any":
        return True
    name = hotel_name.lower()
    for chain_key in chains_filter.split(","):
        chain_key = chain_key.strip()
        keywords = HOTEL_CHAINS.get(chain_key, [chain_key])
        if any(kw in name for kw in keywords):
            return True
    return False

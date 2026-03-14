"""
Novatours.ee — прямой API через pim.novatours.eu
"""
import logging
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)

SITE = "https://www.novatours.ee"
PIM  = "https://pim.novatours.eu/webservice/nova/et_ru"

_token_cache = {"token": None}

CITY_SLUGS = {
    "Хургада": "hurghada",
    "Шарм Эль Шейх": "sharm-el-sheikh",
    "Шарм-эль-Шейх": "sharm-el-sheikh",
}

import re as _re

def _hotel_slug(name: str) -> str:
    name = _re.sub(r"\s*\(.*?\)", "", name)
    name = name.lower().strip().replace("&", "and")
    name = _re.sub(r"[^a-z0-9\s]", "", name)
    return _re.sub(r"\s+", "-", name.strip())


def _get_token() -> str:
    if _token_cache["token"]:
        return _token_cache["token"]
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                locale="ru-RU",
            ).new_page()
            token = None
            def on_req(req):
                nonlocal token
                auth = req.headers.get("authorization", "")
                if auth.startswith("Bearer ") and "pim.novatours" in req.url:
                    token = auth.replace("Bearer ", "").strip()
            page.on("request", on_req)
            page.goto(f"{SITE}/ru", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            browser.close()
            if token:
                _token_cache["token"] = token
                logger.info(f"Novatours: токен получен ({token[:10]}...)")
                return token
    except Exception as e:
        logger.error(f"Novatours: ошибка получения токена: {e}")
    return "03096e21141074517f6c058f9052cbfe"


def fetch_novatours() -> list:
    token = _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"{SITE}/",
    }
    session = requests.Session()
    session.headers.update(headers)

    # Шаг 1 — получаем список отелей с минимальными ценами
    # Только ближайшие 30 дней (горящие туры)
    today = datetime.now()
    date_from = today.strftime("%Y-%m-%d")
    date_to   = (today + timedelta(days=30)).strftime("%Y-%m-%d")

    try:
        r = session.get(f"{PIM}/list-hotels", params={
            "country_code[]": "EG",
            "departure_code": "TLL",
            "adults": 2,
            "childs": 0,
            "nights_from": 7,
            "nights_to": 14,
            "check_in_from": date_from,
            "check_in_to": date_to,
            "sort": "price_asc",
            "items_per_page": 100,
        }, timeout=20)
        r.raise_for_status()
        hotels = r.json().get("hotels", [])
    except Exception as e:
        logger.error(f"Novatours list-hotels error: {e}")
        _token_cache["token"] = None
        return []

    if not hotels:
        logger.warning("Novatours: туры не найдены")
        return []

    logger.info(f"Novatours: {len(hotels)} отелей с ценами")

    # Коды городов для URL
    CITY_CODES = {"Хургада": "HRG", "Шарм Эль Шейх": "SSH", "Шарм-эль-Шейх": "SSH"}

    # Шаг 2 — для каждого отеля получаем реальные офферы с датами
    tours = []
    for h in hotels:
        price = h.get("price")
        if not price:
            continue

        hotel_code = h.get("hotelCode", "")
        hotel_name = h.get("name", "")
        city       = h.get("city", "Египет")
        stars      = str(h.get("stars", ""))

        # Фото
        image = ""
        media = h.get("media", [])
        if media and media[0].get("image"):
            image = media[0]["image"].get("list_thumbnail", "")

        # ✅ ИСПРАВЛЕНО: прямая ссылка на конкретный отель по hotel_code
        city_code_url = CITY_CODES.get(city, "HRG")
        url = f"{SITE}/ru/search/{hotel_code}?fs=step3&hc%5B0%5D=EG&hci%5B0%5D={city_code_url}&hp=1"

        # Получаем офферы с датами
        try:
            r2 = session.get(f"{PIM}/list-hotel-offers", params={
                "hotel_code[]": hotel_code,
                "departure_code": "TLL",
                "adults": 2,
                "childs": 0,
                "nights_from": 7,
                "nights_to": 14,
                "check_in_from": date_from,
                "check_in_to": date_to,
                "sort": "price_asc",
            }, timeout=15)
            if r2.status_code == 200:
                offers = r2.json().get("offers", [])
                # Берём самый дешёвый оффер
                if offers:
                    best = min(offers, key=lambda x: x.get("price", 9999))
                    check_in    = best.get("check_in", "")
                    nights      = int(best.get("nights") or 0)
                    offer_price = float(best.get("price") or price)
                    free_seats  = best.get("free_seats")
                    board_raw = best.get("board_name") or best.get("board") or ""
                    if isinstance(board_raw, dict):
                        board = (board_raw.get("boardTranslation") or
                                 board_raw.get("title") or
                                 board_raw.get("name") or "")
                    else:
                        board = str(board_raw)

                    # Считаем дату возврата
                    return_date = ""
                    if check_in and nights:
                        try:
                            dep_dt = datetime.strptime(check_in, "%Y-%m-%d")
                            return_date = (dep_dt + timedelta(days=nights)).strftime("%Y-%m-%d")
                        except Exception:
                            pass

                    tours.append({
                        "operator": "Novatours",
                        "hotel": hotel_name,
                        "destination": city,
                        "price": offer_price,
                        "nights": nights,
                        "departure_date": check_in,
                        "return_date": return_date,
                        "meal_plan": board,
                        "stars": stars,
                        "seats_left": free_seats,
                        "image": image,
                        "url": url,
                        "hotel_code": hotel_code,
                    })
                    continue
        except Exception as e:
            logger.debug(f"Novatours offers {hotel_code}: {e}")

        # Фолбэк — без дат если оффер не получили
        tours.append({
            "operator": "Novatours",
            "hotel": hotel_name,
            "destination": city,
            "price": float(price),
            "nights": 0,
            "departure_date": "",
            "return_date": "",
            "meal_plan": "",
            "stars": stars,
            "seats_left": None,
            "image": image,
            "url": url,
            "hotel_code": hotel_code,
        })

    return tours

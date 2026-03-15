"""
TEZ Tour Estonia — API https://search.tezapi.eu/tariffsearch/getResult
Ссылки на отели строятся через sessionKey полученный Playwright.
"""
import logging
import re
import time
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

API_URL = "https://search.tezapi.eu/tariffsearch/getResult"
SITE    = "https://www.teztour.ee"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://www.teztour.ee/",
}

PARAMS_BASE = {
    "cityId":           3746,
    "countryId":        5732,
    "priceMin":         0,
    "priceMax":         200000,
    "nightsMin":        7,
    "nightsMax":        14,
    "accommodationId":  2,
    "hotelClassId":     0,
    "hotelClassBetter": "true",
    "rAndBId":          0,
    "rAndBBetter":      "true",
    "tourType":         1,
    "locale":           "ru",
    "xml":              "false",
    "searchMethodId":   3,
    "currency":         18864,
}

_session_key_cache = {"key": None, "ts": 0}


def _get_session_key() -> str:
    """Получаем sessionKey с teztour.ee через Playwright. Кэшируем на 30 минут."""
    now = time.time()
    if _session_key_cache["key"] and now - _session_key_cache["ts"] < 1800:
        return _session_key_cache["key"]

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="ru-RU",
            ).new_page()

            found = []
            def on_resp(resp):
                url = resp.url
                m = re.search(r'/sessionKey/([a-f0-9]{32})/', url)
                if m:
                    found.append(m.group(1))

            page.on("response", on_resp)

            today = datetime.now()
            date_str = today.strftime("%d.%m.%Y")
            date_to  = (today + timedelta(days=20)).strftime("%d.%m.%Y")

            search_url = (
                f"{SITE}/toursearch/tourType/1/cityId/3746"
                f"/before/{date_to}/after/{date_str}"
                f"/countryId/5732/minNights/7/maxNights/14/adults/2"
                f"/flexdate/0/flexnight/0/hotelTypeId/-9006278/mealTypeId/-9006284"
                f"/rAndBBetter/yes/isTableView/0/lview/cls"
                f"/noTicketsTo/no/noTicketsFrom/no/hotelInStop/no"
                f"/recommendedFlag/no/onlineConfirmFlag/no/tourMaxPrice/200000"
                f"/categoryGreatThan/yes/currencyId/18864/dtype/period/searchMethodId/3.ru.html"
            )
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            # ищем в финальном URL
            m = re.search(r'/sessionKey/([a-f0-9]{32})/', page.url)
            if m:
                found.append(m.group(1))

            # ищем в HTML
            html = page.content()
            m2 = re.search(r'sessionKey[/"\s:=]+([a-f0-9]{32})', html)
            if m2:
                found.append(m2.group(1))

            browser.close()

            if found:
                key = found[0]
                _session_key_cache["key"] = key
                _session_key_cache["ts"]  = now
                logger.info(f"TEZ: sessionKey получен ({key[:8]}...)")
                return key

    except Exception as e:
        logger.warning(f"TEZ: не удалось получить sessionKey: {e}")

    return ""


def _build_hotel_url(hotel_id: int, date_from: datetime, date_to: datetime) -> str:
    """Строим ссылку на конкретный отель на teztour.ee."""
    after  = date_from.strftime("%d.%m.%Y")
    before = date_to.strftime("%d.%m.%Y")
    return (
        f"{SITE}/toursearch/tourType/1/cityId/3746"
        f"/before/{before}/after/{after}"
        f"/countryId/5732/minNights/7/maxNights/14/adults/2"
        f"/hotels/{hotel_id}"
        f"/rAndBBetter/yes/tourMaxPrice/200000"
        f"/categoryGreatThan/yes/currencyId/18864/dtype/period/searchMethodId/3.ru.html"
    )


def _safe(lst, idx, default=None):
    try:
        return lst[idx]
    except (IndexError, TypeError):
        return default


def _parse_item(item: list, date_from: datetime, date_to: datetime) -> dict | None:
    try:
        if not isinstance(item, list) or len(item) < 11:
            return None

        dep_date = _safe(item, 0, "")
        nights   = int(_safe(item, 3, 0))

        departure_date = ""
        if dep_date:
            try:
                departure_date = datetime.strptime(dep_date, "%d.%m.%Y").strftime("%Y-%m-%d")
            except Exception:
                departure_date = dep_date

        return_date = ""
        if departure_date and nights:
            try:
                return_date = (
                    datetime.strptime(departure_date, "%Y-%m-%d") + timedelta(days=nights)
                ).strftime("%Y-%m-%d")
            except Exception:
                pass

        city_info   = _safe(item, 5, [])
        destination = _safe(city_info, 0, "Египет")

        hotel_info = _safe(item, 6, [])
        hotel_name = _safe(hotel_info, 1, "")
        hotel_img  = _safe(hotel_info, 2, "")
        hotel_id   = _safe(hotel_info, 3, 0)

        if not hotel_name:
            return None

        stars = 4
        m = re.search(r'(\d)\s*\*', hotel_name)
        if m:
            stars = int(m.group(1))
        hotel_name = re.sub(r'\s*\d\s*\*\s*$', '', hotel_name).strip()

        meal_info = _safe(item, 7, [])
        meal_plan = _safe(meal_info, 1, "") or _safe(meal_info, 0, "")

        price_info = _safe(item, 10, {})
        total_raw  = price_info.get("total", 0) if isinstance(price_info, dict) else 0
        try:
            total = float(total_raw)
        except (TypeError, ValueError):
            return None
        if total <= 0:
            return None
        price_per_person = round(total / 2, 2)

        seats_left = None
        for i in range(11, min(len(item), 20)):
            el = item[i]
            if isinstance(el, list) and len(el) == 1 and isinstance(_safe(el, 0), dict):
                econom   = el[0].get("to", {}).get("econom", {})
                seat_set = econom.get("seatSet", "")
                if seat_set == "Few":
                    seats_left = 3
                elif seat_set == "Available":
                    seats_left = 9
                break

        url = _build_hotel_url(hotel_id, date_from, date_to)

        return {
            "operator":       "TEZ Tour",
            "hotel":          hotel_name,
            "destination":    destination,
            "price":          price_per_person,
            "nights":         nights,
            "departure_date": departure_date,
            "return_date":    return_date,
            "meal_plan":      str(meal_plan),
            "stars":          stars,
            "seats_left":     seats_left,
            "image":          hotel_img,
            "url":            url,
        }

    except Exception as e:
        logger.debug(f"TEZ: ошибка разбора: {e}")
        return None


def fetch_teztour() -> list:
    session = requests.Session()
    session.headers.update(HEADERS)

    today     = datetime.now()
    date_from = today
    date_to   = today + timedelta(days=20)

    params = PARAMS_BASE.copy()
    params["after"]  = date_from.strftime("%d.%m.%Y")
    params["before"] = date_to.strftime("%d.%m.%Y")

    try:
        logger.info(f"TEZ API: запрос {params['after']}–{params['before']}")
        r = session.get(API_URL, params=params, timeout=30)

        if r.status_code != 200:
            logger.warning(f"TEZ API: HTTP {r.status_code}")
            return []

        data = r.json()
        if not data.get("success"):
            logger.warning(f"TEZ API: success=false, message={data.get('message')}")
            return []

        items = data.get("data", [])
        if not isinstance(items, list):
            logger.warning("TEZ API: нет списка data")
            return []

        tours = [t for t in (
_parse_item(i, date_from, date_to) for i in items
        ) if t]

        # Дедупликация — один отель, самая дешёвая цена
        best = {}
        for t in tours:
            key = t["hotel"]
            if key not in best or t["price"] < best[key]["price"]:
                best[key] = t
        tours = list(best.values())

        logger.info(f"TEZ Tour: {len(tours)} туров")
        return tours

    except Exception as e:
        logger.error(f"TEZ API: ошибка: {e}")
        return []

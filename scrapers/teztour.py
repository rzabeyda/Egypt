"""
TEZ Tour scraper — получает свежий sessionKey, потом polling blockdata
"""
import requests
import logging
import time
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SITE = "https://www.teztour.ee"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}


def get_fresh_session_key(session, date_from: str, date_to: str) -> str | None:
    """
    Получаем sessionKey — сначала заходим на главную, потом на страницу поиска.
    sessionKey берём из финального URL или из HTML страницы.
    """
    # Шаг 1: заходим на главную чтобы получить куки
    r0 = session.get(f"{SITE}/ru", timeout=30)
    logger.info(f"TEZ главная: {r0.status_code}")
    time.sleep(1.0)

    # Шаг 2: переходим на страницу поиска туров в Египет
    search_init_url = (
        f"{SITE}/ru/tours/egypt/"
        f"?depCity=3746"
        f"&before={date_from}&after={date_to}"
        f"&nights=4-10&adults=2&tourMaxPrice=115000"
    )
    r1 = session.get(search_init_url, timeout=30, allow_redirects=True)
    logger.info(f"TEZ search init: {r1.status_code}, url: {r1.url[:80]}")

    # Ищем sessionKey в финальном URL
    m = re.search(r'/sessionKey/([a-f0-9]{32})/', r1.url)
    if m:
        return m.group(1)

    # Ищем в HTML
    m2 = re.search(r'sessionKey[/"\s:=]+([a-f0-9]{32})', r1.text)
    if m2:
        return m2.group(1)

    # Шаг 3: пробуем напрямую через toursearch URL
    toursearch_url = (
        f"{SITE}/toursearch/tourType/1/cityId/3746"
        f"/before/{date_from}/after/{date_to}"
        f"/countryId/5732/minNights/4/maxNights/10/adults/2"
        f"/flexdate/0/flexnight/0/hotelTypeId/-9006278/mealTypeId/-9006284"
        f"/rAndBBetter/yes/isTableView/0/lview/cls"
        f"/noTicketsTo/no/noTicketsFrom/no/hotelInStop/no"
        f"/recommendedFlag/no/onlineConfirmFlag/no/tourMaxPrice/115000"
        f"/categoryGreatThan/yes/currencyId/18864/dtype/period/searchMethodId/3.ru.html"
    )
    r2 = session.get(toursearch_url, timeout=30, allow_redirects=True)
    logger.info(f"TEZ toursearch: {r2.status_code}, url: {r2.url[:80]}")

    m3 = re.search(r'/sessionKey/([a-f0-9]{32})/', r2.url)
    if m3:
        return m3.group(1)

    m4 = re.search(r'sessionKey[/"\s:=]+([a-f0-9]{32})', r2.text)
    if m4:
        return m4.group(1)

    # Шаг 4: ищем в JS переменных на странице
    m5 = re.search(r'["\']([a-f0-9]{32})["\']', r2.text)
    if m5:
        logger.info(f"TEZ: нашли 32-hex строку в HTML: {m5.group(1)}")
        return m5.group(1)

    logger.warning("TEZ: sessionKey не найден ни в одном ответе")
    logger.debug(f"HTML фрагмент: {r2.text[:500]}")
    return None


def build_search_url(token: str, date_from: str, date_to: str) -> str:
    return (
        f"{SITE}/toursearch/{token}/tourType/1/cityId/3746"
        f"/before/{date_from}/after/{date_to}"
        f"/countryId/5732/minNights/4/maxNights/10/adults/2"
        f"/flexdate/0/flexnight/0/hotelTypeId/-9006278/mealTypeId/-9006284"
        f"/rAndBBetter/yes/isTableView/0/lview/cls"
        f"/noTicketsTo/no/noTicketsFrom/no/hotelInStop/no"
        f"/recommendedFlag/no/onlineConfirmFlag/no/tourMaxPrice/115000"
        f"/categoryGreatThan/yes/currencyId/18864/dtype/period/searchMethodId/3.ru.html"
    )


def build_blockdata_url(token: str, date_from: str, date_to: str) -> str:
    return (
        f"{SITE}/toursearch/blockdata/sessionKey/{token}/tourType/1/cityId/3746"
        f"/before/{date_from}/after/{date_to}"
        f"/countryId/5732/minNights/4/maxNights/10/adults/2"
        f"/flexdate/0/flexnight/0/hotelTypeId/-9006278/mealTypeId/-9006284"
        f"/rAndBBetter/yes/isTableView/0/lview/cls"
        f"/noTicketsTo/no/noTicketsFrom/no/hotelInStop/no"
        f"/recommendedFlag/no/onlineConfirmFlag/no/tourMaxPrice/115000"
        f"/categoryGreatThan/yes/currencyId/18864/dtype/period/searchMethodId/3.ru.html"
    )


def parse_tours(data: dict, date_from: str, date_to: str, token: str) -> list:
    tours = []
    tour_list = data.get("data", [])

    for item in tour_list:
        try:
            if len(item) < 7:
                continue

            dep_date = item[0]
            nights = item[1]
            hotel_info = item[2]
            meal_info = item[3]
            room_info = item[4]
            price_info = item[5]

            hotel_id = hotel_info[0]
            img_url = hotel_info[2] if len(hotel_info) > 2 else ""
            img_url = img_url.replace("_small.", "_middle.")

            meal_name = meal_info[1] if len(meal_info) > 1 else str(meal_info[0])
            room_name = room_info[1] if len(room_info) > 1 else "Standard"
            price = price_info[0]

            tour_url = build_search_url(token, date_from, date_to)

            tours.append({
                "operator": "TEZ Tour",
                "hotel": f"Hotel {hotel_id}",
                "hotel_id": str(hotel_id),
                "stars": 0,
                "meal": meal_name,
                "room": room_name,
                "departure_date": dep_date,
                "nights": nights,
                "price": price,
                "currency": "EUR",
                "url": tour_url,
                "image": img_url,
                "city": "Sharm el Sheikh",
            })
        except Exception as e:
            logger.debug(f"Ошибка парсинга: {e}")
            continue

    return tours


def enrich_with_filters(tours: list, filters_data) -> list:
    if isinstance(filters_data, dict):
        hotel_list = filters_data.get("data", [])
    elif isinstance(filters_data, list):
        hotel_list = filters_data
    else:
        return tours

    hotel_map = {}
    for h in hotel_list:
        if not isinstance(h, dict):
            continue
        hid = str(h.get("hotelId", ""))
        hotel_map[hid] = {
            "name": h.get("name", ""),
            "stars": h.get("class", 0),
        }

    for tour in tours:
        hid = tour.get("hotel_id", "")
        if hid in hotel_map:
            tour["hotel"] = hotel_map[hid]["name"]
            tour["stars"] = hotel_map[hid]["stars"]

    return tours


def poll_blockdata(session, blockdata_url, date_from, date_to, token,
                   max_attempts=20, delay=2.0):
    payload = {
        "isRender": "true",
        "time": "0",
        "needMore[state]": "0",
        "isRenderData": "false",
        "page[price]": "0",
        "page[optimalNights]": "0",
        "page[isNext]": "true",
        "page[isLoad]": "false",
        "page[cache]": "",
    }

    for attempt in range(1, max_attempts + 1):
        try:
            r = session.post(
                blockdata_url, data=payload, timeout=30,
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": build_search_url(token, date_from, date_to),
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                }
            )
            if r.status_code != 200:
                logger.warning(f"TEZ polling HTTP {r.status_code} попытка {attempt}")
                time.sleep(delay)
                continue

            data = r.json()
            page_info = data.get("page", {})
            is_load = page_info.get("isLoad", False)
            hid_count = len(page_info.get("hid", []))

            logger.info(f"TEZ polling {attempt}: isLoad={is_load}, hid={hid_count}, size={len(r.text)}")

            if is_load and hid_count > 0:
                tours = parse_tours(data, date_from, date_to, token)
                return tours, data

            time.sleep(delay)

        except Exception as e:
            logger.warning(f"TEZ polling ошибка {attempt}: {e}")
            time.sleep(delay)

    return [], {}


def fetch_teztour(config=None) -> list:
    """
    Новый парсер TEZ TOUR через официальный API `https://search.tezapi.eu/tariffsearch/getResult`.

    ВАЖНО:
    - Мы больше не пытаемся вытащить sessionKey из HTML teztour.ee (механизм поменяли).
    - Используем публичный endpoint Tour Search, который по документации не требует авторизации.
    - Параметры подобраны под:
        * вылет из Таллина (cityId=3746),
        * Египет (countryId=5732),
        * 2 взрослых в номере DBL (accommodationId=2),
        * диапазон ночей и цен как в старом парсере.
    Если TEZ на своей стороне что‑то поменяет (ID регионов, классы отелей и т.п.),
    будет достаточно поправить константы PARAMS_BASE ниже.
    """

    API_URL = "https://search.tezapi.eu/tariffsearch/getResult"

    # Базовые параметры для поиска туров в Египет из Таллина.
    # Часть параметров (hotelClassId, rAndBId, tourId) в документации помечены как обязательные,
    # но на практике API зачастую принимает и более "пустые" значения.
    PARAMS_BASE = {
        "cityId": 3746,        # Таллин (из старого URL teztour.ee)
        "countryId": 5732,     # Египет (из справочника стран TEZ)
        "priceMin": 0,
        "priceMax": 115000,
        # Ограничения TEZ: разница между nightsMax и nightsMin не больше 8 ночей.
        # Берём от 7 до 14 ночей (14 - 7 = 7).
        "nightsMin": 7,
        "nightsMax": 14,
        "accommodationId": 2,  # 2 взрослых, DBL
        # Ниже — максимально нейтральные значения, чтобы не отфильтровывать лишнее.
        "hotelClassId": 0,         # 0 — все классы отелей (если backend это поддерживает)
        "hotelClassBetter": True,  # "и лучше"
        "rAndBId": 0,              # 0 — любое питание
        "rAndBBetter": True,
        "tourId": "",              # пусто — все регионы страны (если backend это поддерживает)
        "tourType": 1,             # Пакетный тур (перелёт+отель)
        "locale": "ru",
        "xml": False,              # JSON‑ответ
        "searchMethodId": 3,
        "disableNonRef": False,
        "currency": 18864,         # EUR
    }

    def _build_params(date_from: datetime, date_to: datetime) -> dict:
        """Формируем параметры для одного запроса TEZ API."""
        params = PARAMS_BASE.copy()
        params["after"] = date_from.strftime("%d.%m.%Y")
        params["before"] = date_to.strftime("%d.%m.%Y")
        return params

    def _parse_item(item: dict) -> dict | None:
        """Преобразуем один элемент ответа TEZ в наш унифицированный формат тура."""
        try:
            hotel = item.get("hotel", {}) or {}
            region = hotel.get("region", {}) or {}
            pansion = item.get("pansion", {}) or {}
            price = item.get("price", {}) or {}

            check_in = item.get("checkIn") or ""
            nights = int(item.get("nightCount") or 0)

            # Цена приходит как общая сумма. В боте цена считается "за человека",
            # поэтому делим на 2 (двухместное размещение).
            total_price = float(price.get("total") or 0)
            if total_price <= 0:
                return None
            price_per_person = total_price / 2.0

            hotel_name = hotel.get("name", "").strip() or "Отель TEZ"
            destination = (
                region.get("resortArrivalRegionName")
                or region.get("name")
                or "Египет"
            )

            image = hotel.get("previewImg") or ""

            # Ссылка на отель / бронирование
            url = hotel.get("url") or ""
            if not url:
                booking = (item.get("bookingUrl") or {}).get("bookingUrl") or []
                if isinstance(booking, list) and booking:
                    url = booking[0].get("url", "") or ""

            # Питание
            meal = pansion.get("name") or pansion.get("description") or ""

            # Звёзды: в API нет явного поля категории, поэтому выставляем 4★ по умолчанию.
            stars = 4

            # Дата выезда из отеля (если есть)
            check_out = item.get("checkOut") or ""

            return {
                "operator": "TEZ Tour",
                "hotel": hotel_name,
                "destination": destination,
                "price": round(price_per_person),
                "nights": nights,
                "departure_date": check_in,
                "return_date": check_out,
                "meal_plan": meal,
                "stars": stars,
                "seats_left": None,
                "image": image,
                "url": url,
            }
        except Exception as e:
            logger.debug(f"TEZ: ошибка разбора элемента: {e}")
            return None

    session = requests.Session()
    session.headers.update({
        "User-Agent": HEADERS["User-Agent"],
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://www.teztour.ee/",
    })

    today = datetime.now()
    # Ограничение TEZ: между after и before не больше 20 календарных дней.
    # Берём 20 дней вперёд от сегодняшнего дня.
    date_from = today
    date_to = today + timedelta(days=20)

    params = _build_params(date_from, date_to)

    try:
        logger.info(
            f"TEZ API: запрос тарифов {params['after']}–{params['before']} "
            f"(cityId={params['cityId']}, countryId={params['countryId']})"
        )
        r = session.get(API_URL, params=params, timeout=30)
        if r.status_code != 200:
            logger.warning(f"TEZ API: HTTP {r.status_code} — {r.text[:200]}")
            return []

        data = r.json()
        # JSON‑вариант по документации: success, count, data / searchResult / и т.п.
        items = data.get("data")

        # Если data — не список, попробуем вытащить item из вложенных структур (как в XML‑схеме)
        if isinstance(items, dict):
            inner = items.get("item")
            if isinstance(inner, list):
                items = inner

        if not isinstance(items, list):
            logger.warning(
                "TEZ API: неожиданный формат ответа (нет списка data) "
                f"type(data)={type(data)}, keys={list(data.keys())}"
            )
            # На всякий случай логируем кусок сырых данных, чтобы можно было глазами посмотреть структуру.
            logger.debug(f"TEZ API raw: {r.text[:1000]}")
            return []

        tours: list[dict] = []
        for raw in items:
            tour = _parse_item(raw)
            if tour:
                tours.append(tour)

        logger.info(f"TEZ API: получено {len(tours)} туров")
        return tours

    except Exception as e:
        logger.error(f"TEZ API: ошибка запроса/парсинга: {e}")
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    session = requests.Session()
    session.headers.update(HEADERS)

    date_str = "17.03.2026"

    print("=== Шаг 1: главная страница ===")
    r0 = session.get(f"{SITE}/ru", timeout=30)
    print(f"Главная: {r0.status_code}")
    print(f"Cookies: {dict(session.cookies)}")

    time.sleep(1.0)

    print("\n=== Шаг 2: страница поиска (toursearch без sessionKey) ===")
    toursearch_url = (
        f"{SITE}/toursearch/tourType/1/cityId/3746"
        f"/before/{date_str}/after/{date_str}"
        f"/countryId/5732/minNights/4/maxNights/10/adults/2"
        f"/flexdate/0/flexnight/0/hotelTypeId/-9006278/mealTypeId/-9006284"
        f"/rAndBBetter/yes/isTableView/0/lview/cls"
        f"/noTicketsTo/no/noTicketsFrom/no/hotelInStop/no"
        f"/recommendedFlag/no/onlineConfirmFlag/no/tourMaxPrice/115000"
        f"/categoryGreatThan/yes/currencyId/18864/dtype/period/searchMethodId/3.ru.html"
    )
    r2 = session.get(toursearch_url, timeout=30, allow_redirects=True)
    print(f"Status: {r2.status_code}")
    print(f"Final URL: {r2.url}")
    print(f"Cookies: {dict(session.cookies)}")

    # Ищем sessionKey
    m = re.search(r'/sessionKey/([a-f0-9]{32})/', r2.url)
    if m:
        print(f"\nSessionKey из URL: {m.group(1)}")
    else:
        print("\nSessionKey не в URL, ищем в HTML...")
        matches = re.findall(r'[a-f0-9]{32}', r2.text)
        unique_keys = list(dict.fromkeys(matches))[:5]
        print(f"Найденные 32-hex строки: {unique_keys}")
        print(f"\nПервые 300 символов HTML:\n{r2.text[:300]}")

"""
delfiin.eu — парсер горящих туров в Египет из Таллина
Парсит страницы рейсов напрямую. Структура HTML известна.
"""
import logging
import re
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
SITE = "https://www.delfiin.ee"

# URL шаблоны: /ru/sooduspakkumised/egiptus_hurghada/DDMMННН/TIMESTAMP/
# Парсим индекс и берём все рейсы с нужным кол-вом ночей
EGYPT_PAGES = [
    ("Хургада",       f"{SITE}/ru/sooduspakkumised/egiptus_hurghada"),
    ("Шарм-эль-Шейх", f"{SITE}/ru/sooduspakkumised/egiptus_sharm_el_sheikh"),
    ("Марса-Алам",    f"{SITE}/ru/sooduspakkumised/egiptus_el_alamein"),
]

MIN_NIGHTS   = 7
MAX_NIGHTS   = 14
MAX_DAYS_AHEAD = 60
MAX_PAGES    = 20  # максимум страниц рейсов открываем


def fetch_delfiin() -> list:
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("pip install requests beautifulsoup4")
        return []

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9",
    })

    all_tours = []

    for destination, index_url in EGYPT_PAGES:
        try:
            resp = session.get(index_url, timeout=20)
            resp.raise_for_status()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")

            flight_pages = _get_flight_pages(soup, destination)
            logger.info(f"Delfiin {destination}: {len(flight_pages)} страниц рейсов")

            for page_info in flight_pages[:MAX_PAGES]:
                try:
                    tours = _parse_flight_page(session, page_info, destination)
                    all_tours.extend(tours)
                    logger.info(f"Delfiin {destination} {page_info['dep_date']} {page_info['nights']}н: {len(tours)} туров")
                except Exception as e:
                    logger.debug(f"Delfiin страница {page_info.get('url','')} ошибка: {e}")

        except Exception as e:
            logger.error(f"Delfiin {destination} ошибка: {e}")

    # Дедупликация по отель+дата+цена
    seen = set()
    unique_tours = []
    for t in all_tours:
        key = f"{t['hotel']}|{t['departure_date']}|{t['price']}"
        if key not in seen:
            seen.add(key)
            unique_tours.append(t)

    logger.info(f"Delfiin итого: {len(unique_tours)} туров (было {len(all_tours)} с дублями)")

    # Картинки: берём из кэша БД, новые грузим максимум 20 штук за раз
    hotel_image_cache = {}
    new_fetches = 0
    for t in unique_tours:
        url = t.get("url", "")
        if not url:
            continue
        if url in hotel_image_cache:
            t["image"] = hotel_image_cache[url]
            continue
        try:
            from database import get_cached_image
            cached = get_cached_image(url)
        except Exception:
            cached = None
        if cached is not None:
            hotel_image_cache[url] = cached
            t["image"] = cached
        elif new_fetches < 20:
            img = _get_hotel_image(session, url)
            hotel_image_cache[url] = img
            t["image"] = img
            new_fetches += 1
        else:
            t["image"] = ""

    return unique_tours


def _get_flight_pages(soup, destination: str) -> list:
    """
    Парсит индекс-страницу и возвращает список URL страниц рейсов.
    URL формат: /ru/sooduspakkumised/egiptus_hurghada/28031007/1774656000/
    Паттерн: DDMMСУФ NIGHTS / TIMESTAMP
    """
    today  = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff = today + timedelta(days=MAX_DAYS_AHEAD)

    results = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Ищем ссылки вида /ru/sooduspakkumised/.../DDMMXXNN/TIMESTAMP/
        m = re.search(
            r'/sooduspakkumised/[^/]+/(\d{2})(\d{2})\d{2}(\d{2})/(\d{9,11})/',
            href
        )
        if not m:
            continue

        day    = int(m.group(1))
        month  = int(m.group(2))
        nights = int(m.group(3))
        ts     = m.group(4)

        if not (MIN_NIGHTS <= nights <= MAX_NIGHTS):
            continue

        year = today.year
        try:
            dep_dt = datetime(year, month, day)
            if dep_dt < today - timedelta(days=1):
                dep_dt = datetime(year + 1, month, day)
            if not (today <= dep_dt <= cutoff):
                continue
            dep_date = dep_dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

        url = (SITE + href) if href.startswith("/") else href
        url = url.split("#")[0].rstrip("/") + "/"

        key = f"{dep_date}|{nights}|{ts}"
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "url":      url,
            "dep_date": dep_date,
            "nights":   nights,
        })

    # Сортируем по дате
    results.sort(key=lambda x: (x["dep_date"], x["nights"]))
    return results


def _parse_flight_page(session, page_info: dict, destination: str) -> list:
    from bs4 import BeautifulSoup

    resp = session.get(page_info["url"], timeout=25)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    dep_date = page_info["dep_date"]
    nights   = page_info["nights"]
    tours    = []
    seen     = set()

    try:
        return_date = (
            datetime.strptime(dep_date, "%Y-%m-%d") + timedelta(days=nights)
        ).strftime("%Y-%m-%d")
    except Exception:
        return_date = ""

    dep_dt = datetime.strptime(dep_date, "%Y-%m-%d")

    section = None
    offerid = None
    for suffix in ["10", "11", "00"]:
        sid = f"s{dep_dt.day:02d}{dep_dt.month:02d}{suffix}{nights:02d}"
        sec = soup.find("div", id=sid)
        if sec:
            section = sec
            offerid = f"{dep_dt.day:02d}{dep_dt.month:02d}{suffix}{nights:02d}"
            break

    if not section:
        section = soup.find("div", class_="offer_content")

    if not section:
        return []

    _parse_rows(section, dep_date, nights, destination, return_date, tours, seen)

    if offerid:
        ts_m = re.search(r'/(\d{9,11})/', page_info["url"])
        ts = ts_m.group(1) if ts_m else ""
        if ts:
            try:
                ajax_resp = session.get(
                    f"{SITE}/offers_right_loader.php",
                    params={"offerid": offerid, "str": "", "dz": str(nights),
                            "dat": ts, "loc": "11", "rus": ""},
                    timeout=20
                )
                logger.info(f"AJAX {offerid} status={ajax_resp.status_code} len={len(ajax_resp.text)}")
                if ajax_resp.status_code == 200 and ajax_resp.text.strip():
                    ajax_soup = BeautifulSoup(ajax_resp.text, "html.parser")
                    _parse_rows(ajax_soup, dep_date, nights, destination, return_date, tours, seen)
            except Exception as e:
                logger.debug(f"AJAX error {offerid}: {e}")

    return tours


def _parse_rows(container, dep_date, nights, destination, return_date, tours, seen):
    try:
        return_date_calc = (
            datetime.strptime(dep_date, "%Y-%m-%d") + timedelta(days=nights)
        ).strftime("%Y-%m-%d")
        if not return_date:
            return_date = return_date_calc
    except Exception:
        pass

    for tr in container.find_all("tr", class_=re.compile(r'\bhotel\b')):
        try:
            o1 = tr.find("td", class_="o1")
            if not o1:
                continue
            link = o1.find("a", href=True)
            if not link:
                continue
            hotel_name = link.get_text(strip=True)
            # Убираем "(Ex. Старое название)" и "(ex. ...)"
            hotel_name = re.sub(r'\s*\([Ee]x\.?[^)]*\)', '', hotel_name).strip()
            if not hotel_name:
                continue
            hotel_url = link["href"]
            if hotel_url.startswith("/"):
                hotel_url = SITE + hotel_url

            stars = 0
            ms = re.search(r'\((\d)[+\-]?[*★]\)', hotel_name)
            if ms:
                stars = int(ms.group(1))

            room_div = o1.find("div", class_="room")
            meal_plan = ""
            if room_div:
                meal_plan = _detect_meal(room_div.get_text(" ").lower())

            o2 = tr.find("td", class_="o2")
            if not o2:
                continue
            price_span = o2.find("span", class_="price")
            price_text = price_span.get_text(strip=True) if price_span else o2.get_text(strip=True)
            price_m = re.search(r'(\d+)', price_text.replace(" ", "").replace("\xa0", ""))
            if not price_m:
                continue
            price = float(price_m.group(1))
            if price < 50 or price > 9999:
                continue

            flight_time = ""
            o5 = tr.find("td", class_="o5")
            if o5:
                times = re.findall(r'(\d{2}:\d{2})-(\d{2}:\d{2})', o5.get_text())
                if len(times) >= 2:
                    flight_time = f"✈️ Таллин → {destination}: {times[0][0]}–{times[0][1]}\n✈️ {destination} → Таллин: {times[1][0]}–{times[1][1]}"
                elif len(times) == 1:
                    flight_time = f"✈️ Таллин → {destination}: {times[0][0]}–{times[0][1]}"

            seats_left = None
            o4 = tr.find("td", class_="o4")
            if o4:
                img = o4.find("img")
                if img:
                    sm = re.search(r'tickets-(\d+)', img.get("src", ""))
                    if sm:
                        seats_left = int(sm.group(1))

            key = f"{hotel_name}|{dep_date}|{price}"
            if key in seen:
                continue
            seen.add(key)

            tours.append({
                "operator":       "Delfiin",
                "hotel":          hotel_name,
                "destination":    destination,
                "price":          price,
                "nights":         nights,
                "departure_date": dep_date,
                "return_date":    return_date,
                "meal_plan":      meal_plan,
                "stars":          stars,
                "seats_left":     seats_left,
                "image":          "",
                "flight_time":    flight_time,
                "url":            hotel_url,
            })

        except Exception as e:
            logger.debug(f"Delfiin tr ошибка: {e}")


def _get_hotel_image(session, hotel_url: str) -> str:
    """Берёт картинку отеля с hoteldesc.php — с кэшем в БД."""
    try:
        from database import get_cached_image, cache_image
        cached = get_cached_image(hotel_url)
        if cached is not None:
            return cached

        # Меняем showhotel.php на hoteldesc.php
        desc_url = hotel_url.replace("showhotel.php", "hoteldesc.php")

        resp = session.get(desc_url, timeout=15)
        if resp.status_code != 200:
            cache_image(hotel_url, "")
            return ""

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        image_url = ""
        for img in soup.find_all("img", src=True):
            src = img.get("src", "")
            if not src:
                continue
            # Пропускаем иконки
            if any(x in src.lower() for x in ["tezhoverd", "icon", "logo", "flag"]):
                continue
            if src.startswith("http"):
                image_url = src
            else:
                image_url = SITE + "/" + src.lstrip("/")
            break

        cache_image(hotel_url, image_url)
        logger.debug(f"Картинка {hotel_url}: {image_url[:60] if image_url else 'не найдена'}")
        return image_url
    except Exception as e:
        logger.debug(f"Картинка {hotel_url}: {e}")
        return ""


def _detect_meal(text: str) -> str:
    if any(k in text for k in ["ultra all", "uai", "ультра"]):
        return "Ultra All Inclusive"
    if any(k in text for k in ["всё включено", "все включено", "all inclusive", "kõik hinnas"]):
        return "All Inclusive"
    if any(k in text for k in ["half board", " hb", "полупансион"]):
        return "HB"
    if any(k in text for k in ["завтраки+ужины", "завтраки + ужины"]):
        return "HB"
    if any(k in text for k in ["завтрак", "breakfast", " bb"]):
        return "BB"
    if any(k in text for k in ["room only", " ro", "без питания"]):
        return "RO"
    return ""

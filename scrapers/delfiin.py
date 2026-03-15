"""
Delfiin.ee — парсер горящих туров в Египет из Таллина
"""
import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
SITE = "https://www.delfiin.ee"

_image_cache = {}


def _get_hotel_image(url: str) -> str:
    if url in _image_cache:
        return _image_cache[url]
    try:
        img_url = url.replace("showhotel.php", "hoteldesc.php").replace("&l=1", "&l=0&r#")
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            ).new_page()
            page.goto(img_url, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(2000)
            html = page.content()
            browser.close()
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if not src or "tezhoverd" in src:
                continue
            if src.endswith((".jpg", ".jpeg", ".png", ".webp")):
                result = src if src.startswith("http") else SITE + "/" + src.lstrip("/")
                _image_cache[url] = result
                return result
    except Exception as e:
        logger.debug(f"Delfiin image error: {e}")
    _image_cache[url] = ""
    return ""


def fetch_delfiin() -> list:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright не установлен")
        return []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="ru-RU",
        ).new_page()
        page.goto("https://www.delfiin.ee/ru/sooduspakkumised/1773705600/",
                  wait_until="networkidle", timeout=40000)
        page.wait_for_timeout(5000)
        html = page.content()
        browser.close()

    tours = _parse(html)

    # Загружаем фото — один раз на уникальный отель
    seen_img = {}
    for t in tours:
        key = t["hotel"]
        if key not in seen_img:
            seen_img[key] = _get_hotel_image(t["url"])
        t["image"] = seen_img[key]

    (logger.info if tours else logger.warning)(
        f"Delfiin: {len(tours)} туров" if tours else "Delfiin: туры не найдены"
    )
    return tours


def _parse(html: str) -> list:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    tours = []
    seen  = set()

    for block in soup.find_all("div", class_="offer_content"):
        block_id = block.get("id", "")

        dep_date = ""
        m = re.match(r's(\d{2})(\d{2})\d+', block_id)
        if m:
            day, month = m.group(1), m.group(2)
            year = str(datetime.now().year)
            try:
                dt = datetime(int(year), int(month), int(day))
                if dt < datetime.now() - timedelta(days=1):
                    dt = datetime(int(year) + 1, int(month), int(day))
                dep_date = dt.strftime("%Y-%m-%d")
            except Exception:
                pass

        for row in block.find_all("tr", class_="hotel"):
            try:
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue

                cell0 = cells[0]
                link  = cell0.find("a", href=re.compile(r"showhotel\.php"))
                if not link:
                    continue
                href = link.get("href", "")
                url  = href if href.startswith("http") else SITE + "/" + href.lstrip("/")
                hotel_name = link.get_text(strip=True)
                if not hotel_name:
                    continue

                stars = 0
                ms = re.search(r'\((\d)\*\)', hotel_name)
                if ms:
                    stars = int(ms.group(1))

                room_div   = cell0.find("div", class_="room")
                room_text  = room_div.get_text(" ", strip=True) if room_div else ""
                room_lower = room_text.lower()

                # Направление
                if any(k in room_lower for k in ["sharm", "шарм"]):
                    destination = "Шарм-эль-Шейх"
                elif any(k in room_lower for k in ["marsa alam", "марса алам"]):
                    destination = "Марса-Алам"
                elif any(k in room_lower for k in ["el gouna", "эль гуна"]):
                    destination = "Эль-Гуна"
                else:
                    destination = "Хургада"

                # Питание
                meal_plan = ""
                if any(k in room_lower for k in ["ultra all", "uai", "ультра"]):
                    meal_plan = "Ultra All Inclusive"
                elif any(k in room_lower for k in ["всё включено", "все включено", "all inclusive", "kõik hinnas"]):
                    meal_plan = "All Inclusive"
                elif any(k in room_lower for k in ["завтрак", "breakfast", "bb"]):
                    meal_plan = "BB"
                elif any(k in room_lower for k in ["без питания", "room only"]):
                    meal_plan = "RO"
                elif any(k in room_lower for k in ["полупансион", "half board", "hb"]):
                    meal_plan = "HB"

                # Места
                seats_left = None
                if len(cells) > 2:
                    img = cells[2].find("img")
                    if img:
                        src = img.get("src", "")
                        sm = re.search(r'tickets-(\d+)', src)
                        if sm:
                            seats_left = int(sm.group(1))

                # Время рейса — формат: "🕐 Таллин - Хургада: 03:35–08:20\n🕐 Хургада - Таллин: 21:55–03:05"
                flight_time = ""
                if len(cells) > 3:
                    ft    = cells[3].get_text(" ", strip=True)
                    times = re.findall(r'\d{2}:\d{2}', ft)
                    if len(times) >= 4:
                        flight_time = (
                            f"🕐 Таллин - {destination}: {times[0]}–{times[1]}\n"
                            f"🕐 {destination} - Таллин: {times[2]}–{times[3]}"
                        )
                    elif len(times) >= 2:
                        flight_time = f"🕐 Таллин - {destination}: {times[0]}–{times[1]}"

                # Цена
                price_m = re.search(r'(\d+)', cells[1].get_text(strip=True).replace(" ", ""))
                if not price_m:
                    continue
                price = float(price_m.group(1))
                if price < 50 or price > 9999:
                    continue

                nights = 7
                return_date = ""
                if dep_date:
                    try:
                        return_date = (
                            datetime.strptime(dep_date, "%Y-%m-%d") + timedelta(days=nights)
                        ).strftime("%Y-%m-%d")
                    except Exception:
                        pass

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
                    "url":            url,
                })

            except Exception as e:
                logger.debug(f"Delfiin row error: {e}")
                continue

    return tours

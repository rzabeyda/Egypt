"""
Delfiin.ee — парсер горящих туров в Египет из Таллина
"""
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)
SITE = "https://www.delfiin.ee"


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

    tours = _parse_html(html)
    logger.info(f"Delfiin: {len(tours)} туров" if tours else "Delfiin: туры не найдены")
    return tours


def _parse_html(html: str) -> list:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    tours = []

    # Каждый тур — строка таблицы с классом содержащим "offer" или tr с ссылкой showhotel
    rows = soup.find_all("tr")
    for row in rows:
        try:
            link_tag = row.find("a", href=re.compile(r"showhotel\.php"))
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            url  = href if href.startswith("http") else SITE + "/" + href.lstrip("/")

            # Название отеля
            hotel = link_tag.get_text(strip=True)
            if not hotel:
                continue

            # Все ячейки строки
            cells = [td.get_text(strip=True) for td in row.find_all("td")]

            # Ищем дату (формат DD.MM.YY или DD.MM.YYYY)
            departure_date = ""
            for cell in cells:
                m = re.search(r'(\d{2})\.(\d{2})\.(\d{2,4})', cell)
                if m:
                    d, mo, y = m.groups()
                    y = "20" + y if len(y) == 2 else y
                    try:
                        departure_date = datetime(int(y), int(mo), int(d)).strftime("%Y-%m-%d")
                    except Exception:
                        pass
                    break

            # Ищем ночи
            nights = 0
            for cell in cells:
                m = re.search(r'(\d+)\s*[нn]', cell.lower())
                if m:
                    nights = int(m.group(1))
                    break

            # Ищем цену
            price = 0.0
            for cell in cells:
                m = re.search(r'(\d+)', cell.replace(" ", ""))
                if m:
                    val = int(m.group(1))
                    if 100 <= val <= 5000:
                        price = float(val)
                        break

            # Направление
            destination = "Египет"
            for cell in cells:
                cl = cell.lower()
                if "хургада" in cl or "hurghada" in cl:
                    destination = "Хургада"
                    break
                elif "шарм" in cl or "sharm" in cl:
                    destination = "Шарм-эль-Шейх"
                    break

            # Питание
            meal_plan = ""
            for cell in cells:
                cl = cell.lower()
                if any(k in cl for k in ["all inclusive", "ai", "все включено", "kõik hinnas"]):
                    meal_plan = "All Inclusive"
                    break
                elif any(k in cl for k in ["uai", "ultra"]):
                    meal_plan = "Ultra All Inclusive"
                    break

            # Звёзды
            stars = 0
            for cell in cells:
                m = re.search(r'(\d)\s*\*', cell)
                if m:
                    stars = int(m.group(1))
                    break
            if not stars:
                m = re.search(r'(\d)\s*\*', hotel)
                if m:
                    stars = int(m.group(1))

            if price <= 0:
                continue

            tours.append({
                "operator":       "Delfiin",
                "hotel":          hotel,
                "destination":    destination,
                "price":          price,
                "nights":         nights,
                "departure_date": departure_date,
                "return_date":    "",
                "meal_plan":      meal_plan,
                "stars":          stars,
                "seats_left":     None,
                "image":          "",
                "url":            url,
            })

        except Exception as e:
            logger.debug(f"Delfiin row error: {e}")
            continue

    # Дедупликация
    seen, out = set(), []
    for t in tours:
        k = f"{t['hotel']}|{t['price']}"
        if k not in seen:
            seen.add(k)
            out.append(t)
    return out

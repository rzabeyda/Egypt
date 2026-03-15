from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

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

soup = BeautifulSoup(html, "html.parser")

# Ищем строку с Tivoli или любым отелем Шарм
for row in soup.find_all("tr", class_="hotel"):
    link = row.find("a", href=re.compile(r"showhotel\.php"))
    if not link:
        continue
    text = row.get_text(" ", strip=True)
    if "sharm" in text.lower() or "шарм" in text.lower():
        print("=== СТРОКА ШАРМ ===")
        print(row.prettify()[:2000])
        print("\nЯЧЕЙКИ:")
        for i, td in enumerate(row.find_all("td")):
            print(f"  [{i}]: {repr(td.get_text(' ', strip=True)[:100])}")
        break

# Смотрим заголовок блока над строками
print("\n=== ЗАГОЛОВОК БЛОКА ===")
for block in soup.find_all("div", class_="offer_content"):
    bid = block.get("id", "")
    # ищем заголовок перед блоком
    prev = block.find_previous_sibling()
    if prev:
        print(f"id={bid}, prev sibling: tag={prev.name}, class={prev.get('class')}")
        print(f"  text: {prev.get_text(' ', strip=True)[:150]}")
    if bid.startswith("s1703"):
        break

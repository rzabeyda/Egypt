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

# Ищем первую ссылку на отель и смотрим её родителей
link = soup.find("a", href=re.compile(r"showhotel\.php"))
if link:
    print("Ссылка:", link.get("href", "")[:80])
    print("Текст ссылки:", link.get_text(strip=True))
    print()
    # Идём вверх по дереву
    parent = link.parent
    for i in range(6):
        print(f"Родитель {i}: tag={parent.name}, class={parent.get('class')}, id={parent.get('id')}")
        cells = parent.find_all("td")
        if cells:
            print(f"  Ячейки ({len(cells)}):", [c.get_text(strip=True)[:40] for c in cells])
        parent = parent.parent
        if parent is None:
            break

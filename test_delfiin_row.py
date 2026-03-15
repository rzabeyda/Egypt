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

# Находим первую строку с отелем
for row in soup.find_all("tr"):
    link = row.find("a", href=re.compile(r"showhotel\.php"))
    if link:
        print("=== СТРОКА С ОТЕЛЕМ ===")
        print(row.prettify()[:3000])
        break

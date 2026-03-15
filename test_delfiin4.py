from playwright.sync_api import sync_playwright
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
    
    # Ищем данные об отелях
    print("Длина HTML:", len(html))
    
    # Ищем цены
    prices = re.findall(r'(\d+)\s*€', html)
    print("Цены в HTML:", prices[:10])
    
    # Ищем названия отелей
    hotels = re.findall(r'showhotel\.php\?e=([^"&]+)', html)
    print(f"Ссылок на отели: {len(hotels)}")
    for h in hotels[:3]:
        print(" ", h[:80])

    # Текст страницы
    text = page.inner_text("body")
    print("\nТекст страницы (первые 1000 символов):")
    print(text[:1000])

    browser.close()

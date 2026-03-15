import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

today  = datetime.now()
after  = today.strftime("%d.%m.%Y")
before = (today + timedelta(days=20)).strftime("%d.%m.%Y")

search_url = (
    f"https://www.teztour.ee/toursearch/tourType/1/cityId/3746"
    f"/before/{before}/after/{after}"
    f"/countryId/5732/minNights/7/maxNights/14/adults/2"
    f"/flexdate/0/flexnight/0/hotelTypeId/-9006278/mealTypeId/-9006284"
    f"/rAndBBetter/yes/isTableView/0/lview/cls"
    f"/noTicketsTo/no/noTicketsFrom/no/hotelInStop/no"
    f"/recommendedFlag/no/onlineConfirmFlag/no/tourMaxPrice/200000"
    f"/categoryGreatThan/yes/currencyId/18864/dtype/period/searchMethodId/3.ru.html"
)

hotel_urls = {}  # api_name -> teztour_url

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        locale="ru-RU",
        viewport={"width": 1280, "height": 800},
    )
    page = ctx.new_page()

    # Перехватываем навигацию на страницы отелей
    navigated = []
    def on_resp(resp):
        url = resp.url
        if "/tours/" in url and "/hotel/" in url and url not in navigated:
            navigated.append(url)
            print("HOTEL URL:", url[:200])

    page.on("response", on_resp)

    print("Загружаю страницу поиска...")
    page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
    page.wait_for_timeout(8000)

    # Ищем кликабельные элементы отелей
    # Пробуем разные селекторы
    selectors = [
        "a[href*='/tours/']",
        ".hotel-name a",
        ".b-hotel-name a", 
        ".hotel_name a",
        "a[class*='hotel']",
        ".search-result a",
        "td.b-hotel a",
    ]
    
    for sel in selectors:
        els = page.query_selector_all(sel)
        if els:
            print(f"Найдено {len(els)} элементов по селектору: {sel}")
            for el in els[:2]:
                href = el.get_attribute("href")
                text = el.inner_text()
                print(f"  text={text[:50]}, href={str(href)[:100]}")
            break
    else:
        print("Элементы не найдены ни по одному селектору")
        
    # Пробуем кликнуть на первый результат
    try:
        first = page.query_selector("td.b-hotel") or page.query_selector(".hotel") or page.query_selector("[class*='hotel']")
        if first:
            print(f"Кликаю на: {first.get_attribute('class')}")
            first.click()
            page.wait_for_timeout(3000)
            print("URL после клика:", page.url[:200])
    except Exception as e:
        print("Ошибка клика:", e)

    # Смотрим что вообще есть на странице
    body_text = page.inner_text("body")
    print("\nТекст страницы (первые 300 символов):")
    print(body_text[:300])

    browser.close()

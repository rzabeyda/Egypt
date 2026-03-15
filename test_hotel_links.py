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

found_urls = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        locale="ru-RU",
    ).new_page()

    def on_resp(resp):
        url = resp.url
        if "/tours/" in url and "/hotel/" in url:
            found_urls.append(url)
            print("FOUND:", url[:150])

    page.on("response", on_resp)
    page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)

    # Ищем ссылки на отели прямо в HTML
    html = page.content()
    hotel_links = re.findall(r'href="(/tours/[^"]+hotel/\d+[^"]+)"', html)
    print("\nСсылки на отели в HTML:")
    for l in hotel_links[:5]:
        print(" ", l[:150])

    # Ищем sessionKey в HTML
    keys = re.findall(r'/tours/([a-f0-9]{32})/', html)
    print("\nsessionKey в HTML:", list(dict.fromkeys(keys))[:3])

    browser.close()

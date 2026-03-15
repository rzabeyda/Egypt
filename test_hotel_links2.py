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

    page.on("response", on_resp)
    page.goto(search_url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(8000)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
    page.wait_for_timeout(5000)

    html = page.content()

    # ссылки на отели
    hotel_links = re.findall(r'href="(/tours/[^"]{10,})"', html)
    print(f"Ссылок на отели в HTML: {len(hotel_links)}")
    for l in hotel_links[:3]:
        print(" ", l[:200])

    # sessionKey
    keys = re.findall(r'/tours/([a-f0-9]{32})/', html)
    print("\nsessionKey:", list(dict.fromkeys(keys))[:2])

    # все href с /tours/
    all_tours = re.findall(r'href="[^"]*tours[^"]*"', html)
    print(f"\nВсе href с 'tours': {len(all_tours)}")
    for l in all_tours[:3]:
        print(" ", l[:200])

    print("\nПервые 500 символов HTML:")
    print(html[:500])

    browser.close()

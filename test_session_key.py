import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

SITE = "https://www.teztour.ee"

today    = datetime.now()
date_str = today.strftime("%d.%m.%Y")
date_to  = (today + timedelta(days=20)).strftime("%d.%m.%Y")

search_url = (
    f"{SITE}/toursearch/tourType/1/cityId/3746"
    f"/before/{date_to}/after/{date_str}"
    f"/countryId/5732/minNights/7/maxNights/14/adults/2"
    f"/flexdate/0/flexnight/0/hotelTypeId/-9006278/mealTypeId/-9006284"
    f"/rAndBBetter/yes/isTableView/0/lview/cls"
    f"/noTicketsTo/no/noTicketsFrom/no/hotelInStop/no"
    f"/recommendedFlag/no/onlineConfirmFlag/no/tourMaxPrice/200000"
    f"/categoryGreatThan/yes/currencyId/18864/dtype/period/searchMethodId/3.ru.html"
)

print("Открываю:", search_url)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        locale="ru-RU",
    ).new_page()

    found_keys = []
    def on_resp(resp):
        m = re.search(r'/sessionKey/([a-f0-9]{32})/', resp.url)
        if m:
            found_keys.append(m.group(1))
            print(f"sessionKey в запросе: {m.group(1)}")

    page.on("response", on_resp)
    page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(4000)

    print("Финальный URL:", page.url)

    m = re.search(r'/sessionKey/([a-f0-9]{32})/', page.url)
    if m:
        print("sessionKey из URL:", m.group(1))
    else:
        print("sessionKey в URL не найден")

    # ищем в HTML
    html = page.content()
    keys = re.findall(r'[a-f0-9]{32}', html)
    print("32-hex строки в HTML:", list(dict.fromkeys(keys))[:5])

    browser.close()

from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

# Проверяем — открывает ли такая ссылка конкретный отель?
# hotel_id = 125158 (PANORAMA NAAMA HEIGHTS)

today   = datetime.now()
after   = today.strftime("%d.%m.%Y")
before  = (today + timedelta(days=20)).strftime("%d.%m.%Y")

# Вариант 1 — через параметры в URL
url1 = f"https://www.teztour.ee/ru/tours/egypt/?depCity=3746&hotels=125158&adults=2&nights=7-14&after={after}&before={before}"

# Вариант 2 — через toursearch с hotels в пути  
url2 = (
    f"https://www.teztour.ee/toursearch/tourType/1/cityId/3746"
    f"/before/{before}/after/{after}"
    f"/countryId/5732/minNights/7/maxNights/14/adults/2"
    f"/hotels/125158"
    f"/rAndBBetter/yes/tourMaxPrice/200000"
    f"/categoryGreatThan/yes/currencyId/18864/dtype/period/searchMethodId/3.ru.html"
)

print("URL1:", url1)
print("URL2:", url2)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # headless=False чтобы видеть браузер
    page = browser.new_page()
    
    page.goto(url2, wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(3000)
    print("Финальный URL:", page.url)
    print("Title:", page.title())
    
    input("Нажми Enter чтобы закрыть браузер...")
    browser.close()

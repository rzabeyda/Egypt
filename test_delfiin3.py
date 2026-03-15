from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        locale="ru-RU",
    ).new_page()

    all_requests = []

    def on_req(req):
        url = req.url
        if any(k in url for k in ["api", "ajax", "search", "offer", "tour", "package", "hotel", "json", "data"]):
            all_requests.append(url)

    page.on("request", on_req)
    page.goto("https://www.delfiin.ee/ru/sooduspakkumised/1773705600/",
              wait_until="networkidle", timeout=40000)
    page.wait_for_timeout(5000)

    print(f"Найдено {len(all_requests)} интересных запросов:")
    for url in all_requests:
        print(" ", url[:150])

import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        locale="ru-RU",
    ).new_page()

    api_calls = []

    def on_resp(resp):
        ct = resp.headers.get("content-type", "")
        if "json" in ct:
            url = resp.url
            try:
                data = resp.json()
                api_calls.append({"url": url, "data": data})
                print(f"API: {url[:100]}")
                print(f"  keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            except:
                pass

    page.on("response", on_resp)
    page.goto("https://www.delfiin.ee/ru/sooduspakkumised/1773705600/", 
              wait_until="networkidle", timeout=40000)
    page.wait_for_timeout(5000)

    print(f"\nВсего API вызовов: {len(api_calls)}")
    if api_calls:
        print("\nПервый вызов:")
        print(json.dumps(api_calls[0]["data"], ensure_ascii=False, indent=2)[:2000])

    browser.close()

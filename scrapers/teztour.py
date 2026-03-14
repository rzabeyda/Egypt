"""
TEZ Tour Estonia (teztour.ee) — Playwright.
"""
import logging, json, re
logger = logging.getLogger(__name__)
SITE = "https://www.teztour.ee"


def fetch_teztour() -> list:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright не установлен"); return []

    captured, tours = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="ru-RU", viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()

        def on_resp(resp):
            ct = resp.headers.get("content-type", "")
            if "json" not in ct: return
            url = resp.url.lower()
            if any(k in url for k in ["api", "search", "tour", "package", "offer", "hotel", "result"]):
                try:
                    data = resp.json()
                    if data: captured.append(data)
                except Exception: pass

        page.on("response", on_resp)

        for url in [
            f"{SITE}/ru/last-minute",
            f"{SITE}/ru/egipet",
            f"{SITE}/ru/hurgada",
            f"{SITE}/ru/sharm-el-shejh",
        ]:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(5000)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                page.wait_for_timeout(2000)
            except Exception as e: logger.debug(f"TEZ {url}: {e}")

        try: tours.extend(_parse_html(page.content(), "TEZ Tour"))
        except Exception: pass
        browser.close()

    for data in captured: tours.extend(_parse(data, "TEZ Tour"))
    unique = _dedupe(tours)
    (logger.info if unique else logger.warning)(f"TEZ Tour: {len(unique) if unique else 'туры не найдены'}")
    return unique


def _dedupe(t):
    seen, out = set(), []
    for x in t:
        k = f"{x['hotel']}|{x['price']}"
        if k not in seen and x["hotel"]: seen.add(k); out.append(x)
    return out

def _parse(data, op): return [t for t in (_item(i, op) for i in _list(data)) if t]

def _parse_html(html, op):
    for pat in [r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', r'window\.__STATE__\s*=\s*({.+?});',
                r'"packages"\s*:\s*(\[.+?\])', r'"tours"\s*:\s*(\[.+?\])', r'"offers"\s*:\s*(\[.+?\])']:
        m = re.search(pat, html, re.DOTALL)
        if m:
            try:
                r = _parse(json.loads(m.group(1)), op)
                if r: return r
            except Exception: continue
    return []

def _list(data):
    if isinstance(data, list): return data
    if isinstance(data, dict):
        for k in ("packages","tours","offers","results","data","items","hotels","products","list"):
            v = data.get(k)
            if isinstance(v, list) and v: return v
        for v in data.values():
            if isinstance(v, dict):
                r = _list(v)
                if r: return r
    return []

def _item(item, op):
    hotel = item.get("hotel") or item.get("hotelName") or item.get("hotel_name") or item.get("name") or ""
    if not hotel or not isinstance(hotel, str): return None
    raw = item.get("price") or item.get("pricePerPerson") or item.get("cost") or 0
    try: price = float(str(raw).replace(",",".").replace(" ","") or 0)
    except: price = 0
    if price > 10000: price /= 100
    url = item.get("url") or item.get("link") or f"{SITE}/ru/last-minute"
    if url and not str(url).startswith("http"): url = SITE + url
    return {
        "operator": op, "hotel": hotel,
        "destination": item.get("resort") or item.get("destination") or item.get("city") or item.get("country") or "Egypt",
        "price": price, "nights": int(item.get("nights") or item.get("duration") or 0),
        "departure_date": item.get("departureDate") or item.get("departure_date") or item.get("date") or "",
        "return_date": item.get("returnDate") or item.get("return_date") or "",
        "meal_plan": item.get("meal") or item.get("board") or item.get("mealPlan") or "",
        "stars": str(item.get("stars") or item.get("hotelStars") or ""),
        "seats_left": item.get("seatsLeft") or item.get("seats_left") or item.get("availableSeats") or None,
        "image": item.get("image") or item.get("photo") or item.get("hotelImage") or item.get("imageUrl") or "",
        "url": str(url),
    }

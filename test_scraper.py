import requests, json

TOKEN = "03096e21141074517f6c058f9052cbfe"
BASE = "https://pim.novatours.eu/webservice/nova/et_ru"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.novatours.ee/",
}
s = requests.Session()
s.headers.update(HEADERS)

r = s.get(f"{BASE}/list-hotels", params={
    "country_code[]": "EG",
    "departure_code": "TLL",
    "adults": 2, "childs": 0,
    "nights_from": 7, "nights_to": 14,
    "sort": "price_asc", "items_per_page": 10,
}, timeout=20)

hotels = r.json().get("hotels", [])
print(f"Отелей: {len(hotels)}\n")
for h in hotels:
    if h.get("price"):
        # Ищем URL поля
        url_fields = {k: v for k, v in h.items() if v and isinstance(v, str) and ('url' in k.lower() or 'slug' in k.lower() or 'link' in k.lower() or 'path' in k.lower())}
        print(f"{h['name']} | code: {h.get('hotelCode')} | url fields: {url_fields}")

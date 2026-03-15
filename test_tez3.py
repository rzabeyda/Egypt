import requests, json

r = requests.get("https://search.tezapi.eu/tariffsearch/getResult", params={
    "cityId": 3746, "countryId": 5732,
    "after": "15.03.2026", "before": "04.04.2026",
    "priceMin": 0, "priceMax": 200000,
    "nightsMin": 7, "nightsMax": 14,
    "accommodationId": 2, "hotelClassId": 0,
    "hotelClassBetter": "true", "rAndBId": 0,
    "rAndBBetter": "true", "tourType": 1,
    "locale": "ru", "xml": "false",
    "searchMethodId": 3, "currency": 18864,
}, timeout=30)

data = r.json()
print("Top-level keys:", list(data.keys()))

items = data.get("data")
print("type(data):", type(items))

if isinstance(items, list) and items:
    print("Первый элемент:")
    print(json.dumps(items[0], ensure_ascii=False, indent=2))
elif isinstance(items, dict):
    print("data keys:", list(items.keys()))
    print(json.dumps(items, ensure_ascii=False, indent=2)[:2000])
else:
    print("RAW:", r.text[:2000])

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

items = r.json().get("data", [])
item = items[0]

print("Все элементы первого тура:")
for i, el in enumerate(item):
    s = str(el)
    if "http" in s or "url" in s.lower() or "link" in s.lower():
        print(f"  [{i}] {s[:200]}")

print("\nПолный первый элемент:")
print(json.dumps(item, ensure_ascii=False, indent=2)[:3000])

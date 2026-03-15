import requests, json, re

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
print("Top keys:", list(data.keys()))
print("info:", data.get("info"))

item = data["data"][0]
hotel_id = item[6][3]  # 125158
print("\nhotel_id:", hotel_id)
print("item[11]:", item[11])

# ищем sessionKey во всём ответе
text = r.text
keys = re.findall(r'[a-f0-9]{32}', text)
print("\n32-hex строки в ответе (первые 10):", list(dict.fromkeys(keys))[:10])

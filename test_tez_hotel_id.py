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

items = r.json()["data"]

# Печатаем первые 3 отеля — все числа из каждого элемента
for item in items[:3]:
    hotel_info = item[6]
    print(f"\nОтель: {hotel_info[1]}")
    print(f"  item[6] полностью: {hotel_info}")
    # ищем все числа > 100000 во всём элементе
    import re
    nums = re.findall(r'\b(\d{6,})\b', json.dumps(item))
    print(f"  Большие числа в элементе: {list(dict.fromkeys(nums))[:10]}")

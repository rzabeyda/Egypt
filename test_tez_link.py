import requests

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

item = r.json()["data"][0]
print("item[6] (отель):", item[6])
print("item[11]:", item[11])

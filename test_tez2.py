import requests

BASE = {
    "cityId": 3746, "countryId": 5732,
    "after": "15.03.2026", "before": "04.04.2026",
    "nightsMin": 7, "nightsMax": 14,
    "accommodationId": 2,
    "hotelClassId": 0, "hotelClassBetter": "true",
    "rAndBId": 0, "rAndBBetter": "true",
    "tourType": 1, "locale": "ru", "xml": "false",
    "searchMethodId": 3, "currency": 18864,
}

# Пробуем разные комбинации priceMin/priceMax
tests = [
    {"priceMin": 0, "priceMax": 200000},   # большое число
    {"priceMin": 0, "priceMax": 999999},
    {},                                      # вообще без цены
    {"priceMin": 100, "priceMax": 100000},
]

for extra in tests:
    params = {**BASE, **extra}
    r = requests.get("https://search.tezapi.eu/tariffsearch/getResult", params=params, timeout=30)
    data = r.json()
    label = str(extra) if extra else "БЕЗ ЦЕНЫ"
    success = data.get("success")
    msg = data.get("message", "")
    count = len(data.get("data") or [])
    print(f"{label}")
    print(f"  success={success}, msg={msg[:80]}, tours={count}")
    print()

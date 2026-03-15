import sys, json
sys.path.insert(0, "C:/Egypt")
import requests
from datetime import datetime, timedelta

PIM = "https://pim.novatours.eu/webservice/nova/et_ru"
TOKEN = "03096e21141074517f6c058f9052cbfe"
headers = {"Authorization": f"Bearer {TOKEN}", "User-Agent": "Mozilla/5.0"}

today = datetime.now()
r = requests.get(f"{PIM}/list-hotel-offers", params={
    "hotel_code[]": "EGSSHARMBR",
    "departure_code": "TLL",
    "adults": 2, "childs": 0,
    "nights_from": 7, "nights_to": 14,
    "check_in_from": today.strftime("%Y-%m-%d"),
    "check_in_to": (today + timedelta(days=30)).strftime("%Y-%m-%d"),
    "sort": "price_asc",
}, headers=headers, timeout=15)

offers = r.json().get("offers", [])
print("Первый оффер — все поля:")
print(json.dumps(offers[0], ensure_ascii=False, indent=2))

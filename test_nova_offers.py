import sys
sys.path.insert(0, "C:/Egypt")
import requests
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)

PIM = "https://pim.novatours.eu/webservice/nova/et_ru"
TOKEN = "03096e21141074517f6c058f9052cbfe"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.novatours.ee/",
}

today = datetime.now()
date_from = today.strftime("%Y-%m-%d")
date_to = (today + timedelta(days=30)).strftime("%Y-%m-%d")

# Берём первый отель — Sharm Bride
r = requests.get(f"{PIM}/list-hotel-offers", params={
    "hotel_code[]": "EGSSHARMBR",
    "departure_code": "TLL",
    "adults": 2,
    "childs": 0,
    "nights_from": 7,
    "nights_to": 14,
    "check_in_from": date_from,
    "check_in_to": date_to,
    "sort": "price_asc",
}, headers=headers, timeout=15)

import json
offers = r.json().get("offers", [])
print(f"Всего офферов: {len(offers)}")
for o in offers[:10]:
    print(f"  check_in={o.get('check_in')} nights={o.get('nights')} price={o.get('price')} departure={o.get('departure_datetime','')}")

import sys
sys.path.insert(0, "C:/Egypt")
import logging
logging.basicConfig(level=logging.INFO)

from scrapers.novatours import fetch_novatours
from scrapers.teztour import fetch_teztour

print("=== NOVATOURS ===")
nova = fetch_novatours()
for t in nova[:5]:
    print(f"  {t['hotel'][:35]} | {t['departure_date']} | {t['nights']}н | {t['price']}€ | {t['url'][:60]}")

print("\n=== TEZ TOUR ===")
tez = fetch_teztour()
for t in tez[:5]:
    print(f"  {t['hotel'][:35]} | {t['departure_date']} | {t['nights']}н | {t['price']}€")

import sys
sys.path.insert(0, ".")
import logging
logging.basicConfig(level=logging.INFO)

# Копируем delfiin.py в scrapers/ перед тестом
import shutil
shutil.copy("delfiin.py", "scrapers/delfiin.py")

from scrapers.delfiin import fetch_delfiin
tours = fetch_delfiin()
print(f"\nНайдено туров: {len(tours)}")
for t in tours[:10]:
    print(f"{t['hotel']} | {t['destination']} | {t['price']}€ | {t['nights']}н | {t['departure_date']} | {t['url'][:60]}")

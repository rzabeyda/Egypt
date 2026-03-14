from scrapers.novatours import fetch_novatours
from filters import passes_filters

tours = fetch_novatours()
print(f"\nВсего туров: {len(tours)}\n")
for t in tours:
    passed = passes_filters(t)
    status = "✅ ПРОШЁЛ" if passed else "❌ ОТФИЛЬТРОВАН"
    print(f"{status} | {t['hotel']} | stars:{t['stars']} | meal:{t['meal_plan']} | price:{t['price']} | dep:{t['departure_date']}")

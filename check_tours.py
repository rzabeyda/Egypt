import logging
import sys

from scrapers import fetch_novatours, fetch_teztour
from filters import passes_filters


def _safe_print(text: str) -> None:
    """Печать в консоль без падения на Unicode в Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore"))


def main():
    """
    Утилита для локальной проверки, какие туры найдёт логика бота
    (Novatours + TEZ Tour) без телеграма и расписания.
    """
    logging.basicConfig(level=logging.INFO)

    all_tours = []

    for name, fn in (("Novatours", fetch_novatours), ("TEZ Tour", fetch_teztour)):
        try:
            tours = fn()
            logging.info("%s: %d туров до фильтра", name, len(tours))
            all_tours.extend(tours)
        except Exception as e:
            logging.error("%s упал: %s", name, e)

    _safe_print(f"\nВсего туров до фильтров: {len(all_tours)}")

    filtered = [t for t in all_tours if passes_filters(t)]
    _safe_print(f"После применения фильтров по умолчанию: {len(filtered)}\n")

    for t in filtered[:20]:
        line = (
            f"{t.get('operator')} | {t.get('hotel')} | "
            f"{t.get('destination')} | {t.get('price')}€ | "
            f"{t.get('nights')} ночей | {t.get('departure_date')}"
        )
        _safe_print(line)


if __name__ == "__main__":
    main()



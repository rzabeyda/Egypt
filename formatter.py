from datetime import datetime

MEAL_MAP = {
    "uai": "🍽️🍽️ Ультра все включено",
    "ultra all": "🍽️🍽️ Ультра все включено",
    "all inclusive": "🍽️ Все включено",
    "all-inclusive": "🍽️ Все включено",
    "все включено": "🍽️ Все включено",
    " ai ": "🍽️ Все включено",
    "hb": "🥗 Half Board",
    "half board": "🥗 Half Board",
    "полупансион": "🥗 Half Board",
    "fb": "🍴 Full Board",
    "full board": "🍴 Full Board",
    "bb": "🥐 Завтраки",
    "bed & breakfast": "🥐 Завтраки",
    "завтраки": "🥐 Завтраки",
    "ro": "🏨 Без питания",
    "room only": "🏨 Без питания",
}

MONTHS_RU = ["","января","февраля","марта","апреля","мая",
              "июня","июля","августа","сентября","октября","ноября","декабря"]


def _fmt_meal(meal: str) -> str:
    if not meal:
        return ""
    m = (" " + meal.lower() + " ")
    for k, v in MEAL_MAP.items():
        if k in m:
            return v
    return meal.upper()


def _fmt_stars(stars) -> str:
    try:
        return "⭐" * int(str(stars).replace("*", "").strip())
    except:
        return ""


def _fmt_datetime(d: str) -> str:
    if not d:
        return ""
    s = str(d).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(s[:16], fmt[:16])
            return f"{dt.day:02d}.{dt.month:02d}"
        except:
            continue
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(s[:10], fmt)
            return f"{dt.day:02d}.{dt.month:02d}"
        except:
            continue
    return s[:10]


def price_arrow(hotel: str, operator: str, price: float) -> str:
    try:
        from database import get_yesterday_price, record_price
        yesterday = get_yesterday_price(hotel, operator)
        record_price(hotel, operator, price)
        if yesterday is None:
            return ""
        diff = price - yesterday
        if diff < -5:
            return f"🔴▼ -{abs(diff):.0f}€ дешевле чем вчера"
        elif diff > 5:
            return f"🟢▲ +{diff:.0f}€ дороже чем вчера"
    except Exception:
        pass
    return ""


def format_tour(tour: dict) -> tuple:
    hotel       = tour.get("hotel", "—")
    destination = tour.get("destination", "Египет")
    price       = tour.get("price", 0)
    nights      = tour.get("nights", 0)
    operator    = tour.get("operator", "")
    meal        = _fmt_meal(str(tour.get("meal_plan") or ""))
    stars       = _fmt_stars(tour.get("stars", ""))
    dep         = _fmt_datetime(tour.get("departure_date", ""))
    ret         = _fmt_datetime(tour.get("return_date", ""))
    seats       = tour.get("seats_left")
    url         = tour.get("url") or ""
    image       = str(tour.get("image") or "")
    flight_time = tour.get("flight_time") or ""

    arrow = price_arrow(hotel, operator, price)

    # Рейтинг из нашей базы
    rating_str = ""
    try:
        from ratings import get_rating
        rating, _ = get_rating(hotel)
        if rating:
            rating_str = f"🏆 Рейтинг: {rating}/10"
    except Exception:
        pass

    lines = [
        f"🏨 <b>{hotel}</b>",
    ]

    if rating_str:
        lines.append(rating_str)

    lines.append("")
    lines.append(f"📍 {destination}" + (f"  {meal}" if meal else ""))
    lines.append(f"🌙 Отдых: <b>{nights} ночей</b>" if nights else "")
    lines.append(f"💰 <b>{price:.0f}€</b> / чел | <b>{price * 2:.0f}€</b> / 2 чел")

    if arrow:
        lines.append(arrow)

    lines.append("")

    if dep and ret:
        dep_time = ret_time = ""
        if flight_time:
            times = []
            import re as _re
            for m in _re.finditer(r'(\d{2}:\d{2})–(\d{2}:\d{2})', flight_time):
                times.append(f"{m.group(1)}–{m.group(2)}")
            if len(times) >= 1:
                dep_time = times[0]
            if len(times) >= 2:
                ret_time = times[1]
        dep_str = dep_time and f" | {dep_time}" or ""
        ret_str = ret_time and f" | {ret_time}" or ""
        lines.append(f"✈️ Вылет: <b>{dep}</b>{dep_str}")
        lines.append(f"🏠 Домой: <b>{ret}</b>{ret_str}")
    elif dep:
        lines.append(f"✈️ Вылет: <b>{dep}</b> из Таллина")

    if seats is not None:
        try:
            sv = int(seats)
            emoji = "😰" if sv <= 3 else "😐" if sv <= 6 else "🙂"
            lines.append(f"{emoji} Мест в самолёте: <b>{seats}</b>")
        except:
            pass

    if url:
        lines.append("")
        lines.append(f'<a href="{url}">👉 Смотреть и бронировать</a>')

    # Убираем пустые строки подряд
    result = []
    for line in lines:
        if line == "" and result and result[-1] == "":
            continue
        result.append(line)

    return "\n".join(result), image


def fmt_start() -> str:
    return (
        "👋 <b>Egypt Tour Bot</b>\n\n"
        "Слежу за горящими турами в Египет.\n\n"
        "📍 Вылет из Таллина\n"
        "🏖 Хургада / Шарм-эль-Шейх\n\n"
        "Кнопки внизу 👇\n"
        "🔍 <b>Проверить</b> — найти туры прямо сейчас\n"
        "⚙️ <b>Фильтры</b> — настройки поиска\n"
        "🔔/🔕 <b>Вкл/Выкл</b> — включить/выключить рассылку\n\n"
        "/last — последние найденные туры\n"
        "/status — статус бота"
    )


def fmt_status(users: int, last_check: str, total: int, interval_min: int = 30) -> str:
    return (
        f"📊 <b>Статус</b>\n\n"
        f"👥 Подписчиков: {users}\n"
        f"🕐 Последняя проверка: {last_check}\n"
        f"✅ Туров найдено всего: {total}\n"
        f"⏱ Следующая через ~{interval_min} мин"
    )


def fmt_settings(s: dict) -> str:
    meal_labels = {
        "ai,uai": "🍽️ Все включено (AI + UAI)",
        "ai":     "🍽️ Все включено",
        "uai":    "🍽️🍽️ Ультра все включено",
        "bb":     "🥐 Только завтраки",
        "ro":     "🏨 Без питания",
        "hb":     "🥗 Half Board",
        "any":    "🍴 Любое питание",
    }
    city_labels = {
        "all": "🏙 Все города",
        "hrg": "🌊 Хургада",
        "ssh": "🏔 Шарм-эль-Шейх",
    }

    interval = s.get("interval_min", 30)
    if interval >= 10080:
        interval_str = "7 дней"
    elif interval >= 60:
        interval_str = f"{interval // 60} ч."
    else:
        interval_str = f"{interval} мин."

    price_ranges = s.get("price_ranges", "any")
    if price_ranges == "any":
        price_str = "любая"
    else:
        price_str = price_ranges.replace(",", ", ").replace("0-299", "до 299€").replace("300-499", "300–499€").replace("500-799", "500–799€").replace("800-9999", "800€+")

    days_val = int(s.get("days_filter", 60))

    chains_val = s.get("chains_filter", "any")
    chains_str = "🏨 Любая сеть" if chains_val == "any" else f"🏨 {chains_val.replace(',', ', ')}"

    return (
        f"⚙️ <b>Мои настройки</b>\n\n"
        f"⏱ Частота: <b>{interval_str}</b>\n"
        f"🏙 Город: <b>{city_labels.get(s.get('city_filter', 'all'), 'Все')}</b>\n"
        f"📅 Вылет: <b>в ближайшие {days_val} дней</b>\n"
        f"💰 Цена: <b>{price_str}</b> / чел\n"
        f"🌟 Звёзды: <b>{s.get('stars_min', 3)}★ — {s.get('stars_max', 5)}★</b>\n"
        f"{chains_str}\n"
        f"{meal_labels.get(s.get('meal_filter', 'ai,uai'), '🍽️ AI')}"
    )

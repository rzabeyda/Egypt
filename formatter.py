from datetime import datetime
from ratings import get_rating

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
            if dt.hour or dt.minute:
                return f"{dt.day} {MONTHS_RU[dt.month]} {dt.hour:02d}:{dt.minute:02d}"
            return f"{dt.day} {MONTHS_RU[dt.month]}"
        except:
            continue
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(s[:10], fmt)
            return f"{dt.day} {MONTHS_RU[dt.month]}"
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

    arrow = price_arrow(hotel, operator, price)
    rating, rating_link = get_rating(hotel)

    lines = [
        f"🔥 <b>ГОРЯЩИЙ ТУР — {destination.upper()}</b>",
        "",
        f"🏨 <b>{hotel}</b> {stars}".strip(),
    ]

    if rating:
        lines.append(f'⭐ Рейтинг: <b>{rating}/10</b>  <a href="{rating_link}">→ отзывы</a>')

    if meal:
        lines.append(meal)
    if arrow:
        lines.append(arrow)

    lines.append("")
    lines.append(f"💰 <b>{price:.0f}€</b> / чел  (при размещении 2 чел)")
    lines.append(f"💵 За двоих: <b>{price * 2:.0f}€</b>")
    lines.append("")

    if dep and ret:
        lines.append(f"✈️  Вылет:   <b>{dep}</b>")
        lines.append(f"🏠  Возврат: <b>{ret}</b>")
    elif dep:
        lines.append(f"✈️  Вылет: <b>{dep}</b> из Таллина")

    if nights:
        lines.append(f"🌙 Длительность: <b>{nights} ночей</b>")

    if seats is not None:
        try:
            sv = int(seats)
            emoji = "🔴" if sv <= 3 else "🟡" if sv <= 6 else "🟢"
            lines.append(f"{emoji} Мест в самолёте: <b>{seats}</b>")
        except:
            pass

    lines.append("")
    lines.append(f"🏢 Оператор: {operator}")

    if url:
        lines.append("")
        lines.append(f'<a href="{url}">👉 Смотреть и бронировать</a>')

    return "\n".join(lines), image


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


def fmt_status(users: int, last_check: str, total: int) -> str:
    return (
        f"📊 <b>Статус</b>\n\n"
        f"👥 Подписчиков: {users}\n"
        f"🕐 Последняя проверка: {last_check}\n"
        f"✅ Туров найдено всего: {total}\n"
        f"⏱ Следующая через ~30 мин"
    )


def fmt_settings(s: dict) -> str:
    meal_labels = {
        "ai,uai": "🍽️ Все включено (AI + UAI)",
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

    price_val = s.get("price_max", 1000)
    price_str = "без лимита" if price_val == 9999 else f"{price_val}€"

    days_val = int(s.get("days_filter", 30))

    return (
        f"⚙️ <b>Мои настройки</b>\n\n"
        f"⏱ Частота: <b>{interval_str}</b>\n"
        f"🏙 Город: <b>{city_labels.get(s.get('city_filter', 'all'), 'Все')}</b>\n"
        f"📅 Вылет: <b>в ближайшие {days_val} дней</b>\n"
        f"💰 Макс. цена: <b>{price_str}</b> / чел\n"
        f"🌟 Звёзды: <b>{s.get('stars_min', 3)}★ — {s.get('stars_max', 5)}★</b>\n"
        f"{meal_labels.get(s.get('meal_filter', 'ai,uai'), '🍽️ AI')}"
    )

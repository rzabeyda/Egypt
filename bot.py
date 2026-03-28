"""
Egypt Tour Bot
Запуск: python bot.py
"""

import logging
import asyncio
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from database import (
    init_db, add_user, remove_user, get_active_users,
    get_recent_tours,
    get_settings, set_setting, reset_settings,
    is_sent, mark_sent,
)
from filters import passes_filters
from formatter import format_tour, fmt_start, fmt_status, fmt_settings
from delfiin import fetch_delfiin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

last_check_time = "ещё не проверял"
total_sent = 0
WAITING_PRICE = {}  # chat_id: True — ждём ввода цены


# ══════════════════════════════════════════════════════════════
#  ПОСТОЯННАЯ КЛАВИАТУРА ВНИЗУ
# ══════════════════════════════════════════════════════════════

def main_keyboard(chat_id: int) -> ReplyKeyboardMarkup:
    active = chat_id in get_active_users()
    toggle_label = "🔕 Выключить" if active else "🔔 Включить"
    return ReplyKeyboardMarkup(
        [[
            KeyboardButton("🔍 Искать туры"),
            KeyboardButton("⚙️ Фильтры"),
            KeyboardButton(toggle_label),
        ]],
        resize_keyboard=True,
        is_persistent=True,
    )


# ══════════════════════════════════════════════════════════════
#  INLINE КЛАВИАТУРЫ
# ══════════════════════════════════════════════════════════════

def kb_settings(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔔 Спам",    callback_data="menu_interval"),
            InlineKeyboardButton("🏙 Город",   callback_data="menu_city"),
            InlineKeyboardButton("📅 Вылет",   callback_data="menu_days"),
        ],
        [
            InlineKeyboardButton("💰 Цена",    callback_data="menu_price"),
            InlineKeyboardButton("🌟 Звёзды",  callback_data="menu_stars"),
            InlineKeyboardButton("🍽 Питание", callback_data="menu_meal"),
        ],
        [
            InlineKeyboardButton("🏨 Сеть отелей", callback_data="menu_chains"),
        ],
        [
            InlineKeyboardButton("🔄 Сбросить все фильтры", callback_data="reset_filters"),
        ],
    ])


def kb_interval() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("30 мин", callback_data="interval_30"),
            InlineKeyboardButton("1 час",  callback_data="interval_60"),
            InlineKeyboardButton("6 ч",    callback_data="interval_360"),
        ],
        [
            InlineKeyboardButton("12 ч",   callback_data="interval_720"),
            InlineKeyboardButton("24 ч",   callback_data="interval_1440"),
            InlineKeyboardButton("7 дней", callback_data="interval_10080"),
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="settings")],
    ])


def kb_city() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏙 Все",     callback_data="city_all"),
            InlineKeyboardButton("🌊 Хургада", callback_data="city_hrg"),
            InlineKeyboardButton("🏔 Шарм",    callback_data="city_ssh"),
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="settings")],
    ])


def kb_days() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("7 дней",   callback_data="days_7"),
            InlineKeyboardButton("14 дней",  callback_data="days_14"),
            InlineKeyboardButton("30 дней",  callback_data="days_30"),
        ],
        [
            InlineKeyboardButton("60 дней",  callback_data="days_60"),
            InlineKeyboardButton("180 дней", callback_data="days_180"),
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="settings")],
    ])


def kb_stars() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("3★",   callback_data="stars_3_3"),
            InlineKeyboardButton("4★",   callback_data="stars_4_4"),
            InlineKeyboardButton("5★",   callback_data="stars_5_5"),
        ],
        [
            InlineKeyboardButton("3-4★", callback_data="stars_3_4"),
            InlineKeyboardButton("4-5★", callback_data="stars_4_5"),
            InlineKeyboardButton("3-5★", callback_data="stars_3_5"),
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="settings")],
    ])


def kb_price(current: str = "any") -> InlineKeyboardMarkup:
    ranges = [
        ("0-299",    "до 299€"),
        ("300-499",  "300–499€"),
        ("500-699",  "500–699€"),
        ("700-9999", "700€+"),
    ]
    selected = set(current.split(",")) if current != "any" else set()
    rows = []
    row = []
    for key, label in ranges:
        tick = "✅ " if key in selected else ""
        row.append(InlineKeyboardButton(f"{tick}{label}", callback_data=f"price_toggle_{key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("♾ Любая цена", callback_data="price_toggle_any")])
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data="settings")])
    return InlineKeyboardMarkup(rows)


def kb_meal(current: str = "any") -> InlineKeyboardMarkup:
    options = [
        ("any",    "🍴 Любое питание"),
        ("ai,uai", "🍽️ Все включено (AI)"),
        ("uai",    "🍽️🍽️ Ультра все включено"),
        ("bb",     "🥐 Завтраки (BB)"),
        ("hb",     "🥗 Half Board (HB)"),
        ("ro",     "🏨 Без питания (RO)"),
    ]
    rows = []
    for key, label in options:
        tick = "✅ " if current == key else ""
        rows.append([InlineKeyboardButton(f"{tick}{label}", callback_data=f"meal_{key}")])
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data="settings")])
    return InlineKeyboardMarkup(rows)


def kb_chains(current: str = "any") -> InlineKeyboardMarkup:
    chains = [
        ("rixos",         "Rixos"),
        ("jaz",           "Jaz"),
        ("pickalbatros",  "Pickalbatros"),
        ("sunrise",       "Sunrise"),
        ("steigenberger", "Steigenberger"),
        ("hilton",        "Hilton"),
        ("barcelo",       "Barceló"),
        ("domina",        "Domina"),
        ("baron",         "Baron"),
        ("titanic",       "Titanic"),
    ]
    selected = set(current.split(",")) if current != "any" else set()
    rows = []
    row = []
    for key, label in chains:
        tick = "✅ " if key in selected else ""
        row.append(InlineKeyboardButton(f"{tick}{label}", callback_data=f"chain_toggle_{key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🍀 Любая сеть", callback_data="chain_any")])
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data="settings")])
    return InlineKeyboardMarkup(rows)


# ══════════════════════════════════════════════════════════════
#  КОМАНДЫ
# ══════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if config.ALLOWED_USERS and chat_id not in config.ALLOWED_USERS:
        await update.message.reply_text(
            f"⛔ Нет доступа.\n\nТвой chat_id: <code>{chat_id}</code>",
            parse_mode="HTML",
        )
        return
    add_user(chat_id, update.effective_user.username or "")
    await update.message.reply_text(
        fmt_start(), parse_mode="HTML", reply_markup=main_keyboard(chat_id)
    )
    s = get_settings(chat_id)
    s["chat_id"] = chat_id
    await update.message.reply_text(
        "⚙️ <b>Ваши фильтры по умолчанию:</b>\n\n" + fmt_settings(s),
        parse_mode="HTML"
    )
    await update.message.reply_text("🤖 Ищу предложения.. ожидайте!")
    all_tours = await fetch_all_tours()
    s = get_settings(chat_id)
    user_tours = [t for t in all_tours if passes_filters(t, s)]
    if user_tours:
        user_tours = _dedup_tours(user_tours)
        user_tours.sort(key=lambda t: t.get("price", 0), reverse=True)
        for tour in user_tours:
            await _send_tour(ctx.bot, chat_id, tour)
    else:
        await update.message.reply_text(
            "😕 Сейчас нет туров по вашим фильтрам. Буду проверять и пришлю как появятся!"
        )


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    remove_user(update.effective_chat.id)
    await update.message.reply_text(
        "🔕 Рассылка выключена.",
        reply_markup=main_keyboard(update.effective_chat.id),
    )


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        fmt_status(len(get_active_users()), last_check_time, total_sent, config.CHECK_INTERVAL_MINUTES),
        parse_mode="HTML",
    )


async def cmd_last(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    recent = get_recent_tours(5)
    if not recent:
        await update.message.reply_text("Пока не нашёл ни одного тура 🙁")
        return
    await update.message.reply_text(f"📋 <b>Последние {len(recent)} туров:</b>", parse_mode="HTML")
    for t in recent:
        await _send_tour(ctx.bot, update.effective_chat.id, t)


async def cmd_myid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Твой chat_id: <code>{update.effective_chat.id}</code>", parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════════════
#  ТЕКСТОВЫЕ КНОПКИ
# ══════════════════════════════════════════════════════════════

async def on_text_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    # Обработка ввода цены вручную
    if WAITING_PRICE.get(chat_id):
        WAITING_PRICE.pop(chat_id, None)
        import re as _re
        nums = _re.findall(r'\d+', text)
        if len(nums) >= 2:
            pmin, pmax = int(nums[0]), int(nums[1])
        elif len(nums) == 1:
            pmin, pmax = 0, int(nums[0])
        else:
            await update.message.reply_text("❌ Не понял. Введи например: 300 700")
            return
        set_setting(chat_id, "price_min", pmin)
        set_setting(chat_id, "price_max", pmax)
        set_setting(chat_id, "price_ranges", f"{pmin}-{pmax}")
        s = get_settings(chat_id)
        s["chat_id"] = chat_id
        label = f"{pmin}–{pmax}€" if pmin > 0 else f"до {pmax}€"
        await update.message.reply_text(
            f"✅ Цена: {label}\n\n" + fmt_settings(s),
            parse_mode="HTML",
            reply_markup=kb_settings(chat_id)
        )
        return

    if text == "⚙️ Фильтры":
        s = get_settings(chat_id)
        s["chat_id"] = chat_id
        await update.message.reply_text(
            fmt_settings(s), parse_mode="HTML", reply_markup=kb_settings(chat_id)
        )

    elif text == "🔔 Включить":
        add_user(chat_id, update.effective_user.username or "")
        await update.message.reply_text(
            "🔔 Рассылка включена!", reply_markup=main_keyboard(chat_id)
        )

    elif text == "🔕 Выключить":
        remove_user(chat_id)
        await update.message.reply_text(
            "🔕 Рассылка выключена.", reply_markup=main_keyboard(chat_id)
        )

    elif text == "🔍 Искать туры":
        await update.message.reply_text("🤖 Ищу предложения на delfiin.eu, подождите!")
        all_tours = await fetch_all_tours()
        s = get_settings(chat_id)
        user_tours = [t for t in all_tours if passes_filters(t, s)]
        if user_tours:
            user_tours = _dedup_tours(user_tours)
            user_tours.sort(key=lambda t: t.get("price", 0), reverse=True)
            for tour in user_tours:
                await _send_tour(ctx.bot, chat_id, tour)
        else:
            await update.message.reply_text("😕 Туров по вашим фильтрам сейчас нет.")


# ══════════════════════════════════════════════════════════════
#  INLINE КНОПКИ
# ══════════════════════════════════════════════════════════════

async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    if data == "settings":
        s = get_settings(chat_id)
        s["chat_id"] = chat_id
        await query.message.edit_text(
            fmt_settings(s), parse_mode="HTML", reply_markup=kb_settings(chat_id)
        )
        return

    if data == "reset_filters":
        reset_settings(chat_id)
        await _back_settings(query, chat_id, "🔄 Фильтры сброшены до стандартных!")
        return

    if data == "menu_interval":
        await query.message.edit_text(
            "⏱ <b>Частота рассылки (Спам)</b>\n\nКак часто проверять и присылать новые туры?",
            parse_mode="HTML", reply_markup=kb_interval()
        )
        return

    if data == "menu_city":
        await query.message.edit_text(
            "🏙 <b>Город</b>", parse_mode="HTML", reply_markup=kb_city()
        )
        return

    if data == "menu_days":
        await query.message.edit_text(
            "📅 <b>Вылет в ближайшие...</b>", parse_mode="HTML", reply_markup=kb_days()
        )
        return

    if data == "menu_price":
        s = get_settings(chat_id)
        current = s.get("price_ranges", "any")
        await query.message.edit_text(
            "💰 <b>Цена за 1 человека</b>\n\nМожно выбрать несколько диапазонов:",
            parse_mode="HTML", reply_markup=kb_price(current)
        )
        return

    if data == "price_manual":
        WAITING_PRICE[chat_id] = True
        await query.message.edit_text(
            "✏️ <b>Введи диапазон цены</b>\n\nФормат: <code>от до</code>\nПример: <code>300 700</code>",
            parse_mode="HTML"
        )
        return

    if data.startswith("price_toggle_"):
        key = data.replace("price_toggle_", "")
        s = get_settings(chat_id)
        current = s.get("price_ranges", "any")
        if key == "any":
            new_val = "any"
            set_setting(chat_id, "price_min", 0)
            set_setting(chat_id, "price_max", 9999)
        else:
            selected = set(current.split(",")) if current != "any" else set()
            if key in selected:
                selected.discard(key)
            else:
                selected.add(key)
            new_val = ",".join(sorted(selected)) if selected else "any"
        set_setting(chat_id, "price_ranges", new_val)
        label = "любая" if new_val == "any" else new_val.replace(",", ", ")
        await query.message.edit_text(
            f"✅ Цена: {label}\n\nВыбери диапазон:",
            parse_mode="HTML", reply_markup=kb_price(new_val)
        )
        return

    if data == "price_toggle_any":
        set_setting(chat_id, "price_ranges", "any")
        set_setting(chat_id, "price_min", 0)
        set_setting(chat_id, "price_max", 9999)
        await _back_settings(query, chat_id, "✅ Цена: любая")
        return

    if data == "menu_stars":
        await query.message.edit_text(
            "🌟 <b>Звёздность отеля</b>", parse_mode="HTML", reply_markup=kb_stars()
        )
        return

    if data == "menu_meal":
        await query.message.edit_text(
            "🍽 <b>Тип питания</b>", parse_mode="HTML", reply_markup=kb_meal()
        )
        return

    if data.startswith("interval_"):
        minutes = int(data.split("_")[1])
        set_setting(chat_id, "interval_min", minutes)
        if minutes >= 10080:
            label = "7 дней"
        elif minutes >= 60:
            label = f"{minutes // 60} ч."
        else:
            label = f"{minutes} мин."
        await _back_settings(query, chat_id, f"✅ Частота: {label}")
        return

    if data.startswith("city_"):
        val = data[5:]
        set_setting(chat_id, "city_filter", val)
        labels = {"all": "🏙 Все города", "hrg": "🌊 Хургада", "ssh": "🏔 Шарм"}
        await _back_settings(query, chat_id, f"✅ Город: {labels.get(val, val)}")
        return

    if data.startswith("days_"):
        val = int(data.split("_")[1])
        set_setting(chat_id, "days_filter", val)
        await _back_settings(query, chat_id, f"✅ Вылет в ближайшие: {val} дней")
        return

    if data.startswith("stars_"):
        parts = data.split("_")
        mn, mx = int(parts[1]), int(parts[2])
        set_setting(chat_id, "stars_min", mn)
        set_setting(chat_id, "stars_max", mx)
        await _back_settings(query, chat_id, f"✅ Звёзды: {mn}★ — {mx}★")
        return

    if data == "menu_chains":
        s = get_settings(chat_id)
        current = s.get("chains_filter", "any")
        await query.message.edit_text(
            "🏨 <b>Сеть отелей</b>\n\nВыбери одну или несколько сетей (нажимай — галочка появится).\nПо умолчанию — любая сеть.",
            parse_mode="HTML", reply_markup=kb_chains(current)
        )
        return

    if data.startswith("chain_toggle_"):
        key = data.replace("chain_toggle_", "")
        s = get_settings(chat_id)
        current = s.get("chains_filter", "any")
        selected = set(current.split(",")) if current != "any" else set()
        if key in selected:
            selected.discard(key)
        else:
            selected.add(key)
        new_val = ",".join(sorted(selected)) if selected else "any"
        set_setting(chat_id, "chains_filter", new_val)
        label = "любая сеть" if new_val == "any" else new_val.replace(",", ", ")
        await query.message.edit_text(
            f"✅ Сети: {label}\n\nВыбери одну или несколько сетей:",
            parse_mode="HTML", reply_markup=kb_chains(new_val)
        )
        return

    if data == "chain_any":
        set_setting(chat_id, "chains_filter", "any")
        await query.message.edit_text(
            "✅ Сети: любая\n\nВыбери одну или несколько сетей:",
            parse_mode="HTML", reply_markup=kb_chains("any")
        )
        return

    if data.startswith("meal_"):
        val = data[5:]
        set_setting(chat_id, "meal_filter", val)
        labels = {
            "ai,uai": "🍽️ Все включено",
            "uai":    "🍽️🍽️ Ультра все включено",
            "bb":     "🥐 Только завтраки",
            "ro":     "🏨 Без питания",
            "any":    "🍴 Любое",
        }
        await _back_settings(query, chat_id, f"✅ Питание: {labels.get(val, val)}")
        return


async def _back_settings(query, chat_id: int, notice: str):
    s = get_settings(chat_id)
    s["chat_id"] = chat_id
    await query.message.edit_text(
        f"{notice}\n\n" + fmt_settings(s),
        parse_mode="HTML",
        reply_markup=kb_settings(chat_id),
    )


# ══════════════════════════════════════════════════════════════
#  ОТПРАВКА ТУРА
# ══════════════════════════════════════════════════════════════

async def _send_tour(bot, chat_id: int, tour: dict):
    text, image = format_tour(tour)
    if not image:
        return
    if is_sent(tour):
        return
    try:
        if image.startswith("http"):
            await bot.send_photo(chat_id=chat_id, photo=image, caption=text, parse_mode="HTML")
        else:
            import os
            if os.path.isfile(image):
                with open(image, "rb") as f:
                    await bot.send_photo(chat_id=chat_id, photo=f, caption=text, parse_mode="HTML")
    except Exception:
        await bot.send_message(
            chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True
        )
    mark_sent(tour)


def _dedup_tours(tours: list) -> list:
    """Дедупликация по отель+дата. Предпочитаем тур с картинкой."""
    import re as _re
    def base_name(hotel):
        return _re.sub(r'\s*\(\d+[*★][^)]*\).*', '', hotel).strip().lower()

    best = {}
    for t in tours:
        key = f"{base_name(t.get('hotel',''))}|{t.get('departure_date','')}|{t.get('destination','')}"
        if key not in best:
            best[key] = t
        else:
            if t.get("image") and not best[key].get("image"):
                logger.info(f"DEDUP заменяем на с картинкой: {t.get('hotel')}")
                best[key] = t
            else:
                logger.info(f"DEDUP убираем дубль: {t.get('hotel')} {t.get('departure_date')}")
    logger.info(f"DEDUP: {len(tours)} → {len(best)} туров")
    return list(best.values())
# ══════════════════════════════════════════════════════════════

SCRAPERS = [
    ("Delfiin", fetch_delfiin),
]


async def fetch_all_tours() -> list:
    """Все туры для кнопки Проверить и /start."""
    loop = asyncio.get_event_loop()
    results = await asyncio.gather(
        *[loop.run_in_executor(None, fn) for _, fn in SCRAPERS],
        return_exceptions=True,
    )
    all_tours = []
    for (name, _), result in zip(SCRAPERS, results):
        if isinstance(result, Exception):
            logger.error(f"{name} упал: {result}")
        elif result:
            all_tours.extend(result)
    return all_tours


async def run_check(app=None, notify_users=True) -> list:
    """Периодическая проверка (по расписанию)."""
    global last_check_time, total_sent
    last_check_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    logger.info(f"▶️  Проверка [{last_check_time}]")

    loop = asyncio.get_event_loop()
    results = await asyncio.gather(
        *[loop.run_in_executor(None, fn) for _, fn in SCRAPERS],
        return_exceptions=True,
    )

    all_tours = []
    for (name, _), result in zip(SCRAPERS, results):
        if isinstance(result, Exception):
            logger.error(f"{name} упал: {result}")
        elif result:
            logger.info(f"{name}: {len(result)} туров до фильтра")
            all_tours.extend(result)

    logger.info(f"Итого до фильтра: {len(all_tours)}")

    logger.info(f"✅ Всего туров: {len(all_tours)}")

    if notify_users and app:
        for chat_id in get_active_users():
            s = get_settings(chat_id)
            user_tours = [t for t in all_tours if passes_filters(t, s)]
            if user_tours:
                user_tours = _dedup_tours(user_tours)
                total_sent += len(user_tours)
                for tour in user_tours:
                    try:
                        await _send_tour(app.bot, chat_id, tour)
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logger.error(f"Ошибка отправки {chat_id}: {e}")
                try:
                    interval = s.get("interval_min", config.CHECK_INTERVAL_MINUTES)
                    if interval >= 1440:
                        interval_str = f"{interval // 1440} дн."
                    elif interval >= 60:
                        interval_str = f"{interval // 60} ч."
                    else:
                        interval_str = f"{interval} мин."
                    await app.bot.send_message(
                        chat_id,
                        f"✅ Проверка завершена — найдено {len(user_tours)} тур(ов) по вашим фильтрам.\n"
                        f"⏱ Следующая проверка через {interval_str}"
                    )
                except Exception:
                    pass
            else:
                try:
                    interval = s.get("interval_min", config.CHECK_INTERVAL_MINUTES)
                    if interval >= 1440:
                        interval_str = f"{interval // 1440} дн."
                    elif interval >= 60:
                        interval_str = f"{interval // 60} ч."
                    else:
                        interval_str = f"{interval} мин."
                    await app.bot.send_message(
                        chat_id,
                        f"🔍 Проверил Delfiin — {len(all_tours)} предложений.\n"
                        f"По вашим фильтрам ничего не найдено.\n"
                        f"⏱ Следующая проверка через {interval_str}"
                    )
                except Exception:
                    pass

    return all_tours


# ══════════════════════════════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════════════════════════════

def main():
    init_db()
    logger.info("✅ БД готова")

    app = Application.builder().token(config.TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("stop",   cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("last",   cmd_last))
    app.add_handler(CommandHandler("myid",   cmd_myid))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_button))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: asyncio.ensure_future(run_check(app=app, notify_users=True)),
        trigger="interval",
        minutes=config.CHECK_INTERVAL_MINUTES,
        id="check",
        max_instances=1,
    )

    for uid in config.ALLOWED_USERS:
        add_user(uid, "auto")
        logger.info(f"✅ Авто-подписан: {uid}")

    async def on_startup(app):
        scheduler.start()
        logger.info(f"⏰ Планировщик: каждые {config.CHECK_INTERVAL_MINUTES} мин")
        await asyncio.sleep(5)
        for cid in get_active_users():
            try:
                s = get_settings(cid)
                interval = s.get("interval_min", config.CHECK_INTERVAL_MINUTES)
                if interval >= 1440:
                    interval_str = f"{interval // 1440} дн."
                elif interval >= 60:
                    interval_str = f"{interval // 60} ч."
                else:
                    interval_str = f"{interval} мин."
                await app.bot.send_message(
                    cid,
                    f"🤖 Бот запущен!\n\n"
                    f"📍 Вылет из Таллина → Египет\n"
                    f"🔍 Проверяю Delfiin.eu\n"
                    f"⏱ Автопроверка каждые {interval_str}",
                    reply_markup=main_keyboard(cid)
                )
            except Exception:
                pass
        await run_check(app=app, notify_users=True)

    async def on_shutdown(app):
        scheduler.shutdown()

    app.post_init = on_startup
    app.post_shutdown = on_shutdown

    logger.info("🤖 Бот запущен!")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except Exception:
        pass

    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()

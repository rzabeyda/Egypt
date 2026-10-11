"""
Egypt Tour Bot
Запуск: python bot.py
"""

import logging
import asyncio
import time
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, TypeHandler,
    ApplicationHandlerStop, filters, ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.error import Forbidden, BadRequest

import config
from database import (
    init_db, add_user, remove_user, get_active_users,
    get_recent_tours,
    get_settings, set_setting, reset_settings,
    mark_sent, is_sent_to, mark_sent_to, cleanup_user_sent,
    get_last_notified, set_last_notified,
)
from filters import passes_filters
from formatter import format_tour, fmt_start, fmt_status, fmt_settings
from delfiin import fetch_delfiin
from top_hotels import TOP_HOTELS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
    ],
)
# httpx пишет в INFO каждый getUpdates вместе с токеном в URL
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

last_check_time = "ещё не проверял"
total_sent = 0
WAITING_PRICE = {}  # chat_id: True — ждём ввода цены

# Глобальная ссылка на app для планировщика
_app = None


# ══════════════════════════════════════════════════════════════
#  ПОСТОЯННАЯ КЛАВИАТУРА ВНИЗУ
# ══════════════════════════════════════════════════════════════

def main_keyboard(chat_id: int) -> ReplyKeyboardMarkup:
    active = chat_id in get_active_users()
    toggle_label = "ВЫКЛ" if active else "ВКЛ"
    return ReplyKeyboardMarkup(
        [[
            KeyboardButton("Искать"),
            KeyboardButton("Фильтры"),
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
            InlineKeyboardButton("⏱ Интервал", callback_data="menu_interval"),
            InlineKeyboardButton("📅 Вылет",   callback_data="menu_days"),
            InlineKeyboardButton("💰 Цена",    callback_data="menu_price"),
        ],
        [
            InlineKeyboardButton("🌟 Звёзды",  callback_data="menu_stars"),
            InlineKeyboardButton("🏅 Рейтинг", callback_data="menu_rating"),
            InlineKeyboardButton("🏨 Отели",   callback_data="menu_chains"),
        ],
    ])


def kb_interval(current: int = 0) -> InlineKeyboardMarkup:
    def b(label, minutes):
        tick = "✅ " if current == minutes else ""
        return InlineKeyboardButton(f"{tick}{label}", callback_data=f"interval_{minutes}")
    return InlineKeyboardMarkup([
        [b("6 ч", 360), b("12 ч", 720), b("24 ч", 1440)],
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


def kb_days(current: int = 0) -> InlineKeyboardMarkup:
    def b(label, days):
        tick = "✅ " if current == days else ""
        return InlineKeyboardButton(f"{tick}{label}", callback_data=f"days_{days}")
    return InlineKeyboardMarkup([
        [b("7 дней", 7), b("14 дней", 14)],
        [InlineKeyboardButton("◀️ Назад", callback_data="settings")],
    ])


def kb_stars(mn: int = 0, mx: int = 0) -> InlineKeyboardMarkup:
    def b(label, a, z):
        tick = "✅ " if (mn, mx) == (a, z) else ""
        return InlineKeyboardButton(f"{tick}{label}", callback_data=f"stars_{a}_{z}")
    return InlineKeyboardMarkup([
        [b("4-5★", 4, 5), b("3-5★", 3, 5)],
        [InlineKeyboardButton("◀️ Назад", callback_data="settings")],
    ])


def kb_price(current: str = "any", price_max: int = 9999) -> InlineKeyboardMarkup:
    # старые настройки: «any» с потолком price_max — ни один пункт не отмечаем
    sel = "legacy" if (current == "any" and price_max < 9999) else current
    def b(label, key):
        tick = "✅ " if sel == key else ""
        return InlineKeyboardButton(f"{tick}{label}", callback_data=f"price_toggle_{key}")
    return InlineKeyboardMarkup([
        [b("0 – 500 €", "0-499"), b("500 – 1000 €", "500-999"), b("1000+ €", "1000-9999")],
        [b("Любая цена", "any")],
        [InlineKeyboardButton("◀️ Назад", callback_data="settings")],
    ])


def kb_rating(current: float = 0) -> InlineKeyboardMarkup:
    def b(label, value):
        tick = "✅ " if float(current or 0) == value else ""
        return InlineKeyboardButton(f"{tick}{label}", callback_data=f"rating_{int(value)}")
    return InlineKeyboardMarkup([
        [b("7+", 7), b("8+", 8), b("9+", 9)],
        [b("Любой", 0)],
        [InlineKeyboardButton("◀️ Назад", callback_data="settings")],
    ])


def kb_meal(current: str = "any") -> InlineKeyboardMarkup:
    def b(label, key, active):
        tick = "✅ " if active else ""
        return InlineKeyboardButton(f"{tick}{label}", callback_data=f"meal_{key}")
    is_ai = current in ("ai,uai", "ai", "uai")
    return InlineKeyboardMarkup([
        [b("Всё включено", "ai,uai", is_ai), b("Любое питание", "any", not is_ai)],
        [InlineKeyboardButton("◀️ Назад", callback_data="settings")],
    ])


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
        ("savoy",         "Savoy"),
        ("sunnydays",     "Sunny Days"),
        ("hawaii",        "Hawaii"),
        ("coral",         "Coral"),
        ("fourseasons",   "Four Seasons"),
        ("reef",          "Reef"),
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
    any_tick = "✅ " if not selected else ""
    rows.append([InlineKeyboardButton(f"{any_tick}Любая сеть", callback_data="chain_any")])
    rows.append([InlineKeyboardButton("🏆 Топ отелей", callback_data="top_menu")])
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data="settings")])
    return InlineKeyboardMarkup(rows)


def kb_top_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Хургада", callback_data="top_hrg"),
            InlineKeyboardButton("Шарм-эль-Шейх", callback_data="top_ssh"),
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu_chains")],
    ])


TOP_PAGE_SIZE = 60   # строк на странице (лимит Telegram ~4096 символов)


def _top_pages(city: str) -> int:
    n = len(TOP_HOTELS.get(city, []))
    return max(1, -(-n // TOP_PAGE_SIZE))


def kb_top_list(city: str, page: int = 1) -> InlineKeyboardMarkup:
    pages = _top_pages(city)
    other = "ssh" if city == "hrg" else "hrg"
    other_label = "Шарм-эль-Шейх" if city == "hrg" else "Хургада"
    rows = []
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"top_{city}_{page - 1}"))
    if pages > 1:
        nav.append(InlineKeyboardButton(f"{page}/{pages}", callback_data=f"top_{city}_{page}"))
    if page < pages:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"top_{city}_{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(other_label, callback_data=f"top_{other}")])
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data="top_menu")])
    return InlineKeyboardMarkup(rows)


def _top_text(city: str, page: int = 1) -> str:
    title = "Хургада" if city == "hrg" else "Шарм-эль-Шейх"
    hotels = TOP_HOTELS.get(city, [])
    pages = _top_pages(city)
    page = min(max(page, 1), pages)
    start = (page - 1) * TOP_PAGE_SIZE
    head = f"🏆 <b>Топ отелей: {title}</b>"
    if pages > 1:
        head += f" ({page}/{pages})"
    lines = [head, ""]
    for i, (name, stars, rating) in enumerate(hotels[start:start + TOP_PAGE_SIZE], start + 1):
        star_part = f" · {stars}★" if stars else ""
        lines.append(f"{i}. {name}{star_part} · {rating}/10")
    return "\n".join(lines)[:4000]


# ══════════════════════════════════════════════════════════════
#  КОМАНДЫ
# ══════════════════════════════════════════════════════════════

MAX_TOURS_PER_SEND = 10   # максимум туров за один раз (чтобы не заспамить чат)
_searching: set = set()


async def _do_search(bot, chat_id: int):
    """Ручной поиск в фоне, чтобы не блокировать остальные команды."""
    if chat_id in _searching:
        return
    _searching.add(chat_id)
    try:
        all_tours = await fetch_all_tours()
        s = get_settings(chat_id)
        user_tours = [t for t in all_tours if passes_filters(t, s)]
        if user_tours:
            user_tours = _dedup_tours(user_tours)
            user_tours.sort(key=lambda t: t.get("price", 0))
            shown = user_tours[:MAX_TOURS_PER_SEND]
            for tour in shown:
                await _send_tour(bot, chat_id, tour)
                mark_sent_to(chat_id, tour)
                mark_sent(tour)
            if len(user_tours) > len(shown):
                await bot.send_message(
                    chat_id,
                    f"Показаны {len(shown)} самых дешёвых из {len(user_tours)}. "
                    f"Сузь выбор в «Фильтры», чтобы увидеть остальные.",
                )
        else:
            await bot.send_message(
                chat_id,
                "😕 Сейчас нет туров.",
            )
    except Exception as e:
        logger.error(f"Ошибка поиска {chat_id}: {e}")
    finally:
        _searching.discard(chat_id)


_bg_tasks: set = set()


def _spawn(coro):
    t = asyncio.create_task(coro)
    _bg_tasks.add(t)
    t.add_done_callback(_bg_tasks.discard)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if config.ALLOWED_USERS and chat_id not in config.ALLOWED_USERS:
        await update.message.reply_text(
            f"⛔ Нет доступа.\n\nТвой chat_id: <code>{chat_id}</code>",
            parse_mode="HTML",
        )
        return
    add_user(chat_id, update.effective_user.username or "")
    s = get_settings(chat_id)
    s["chat_id"] = chat_id
    # нижняя клавиатура крепится к этому сообщению (приветствие убрано)
    await update.message.reply_text(
        fmt_settings(s),
        parse_mode="HTML", reply_markup=main_keyboard(chat_id)
    )
    await update.message.reply_text("Ищу предложения, ожидайте!")
    _spawn(_do_search(ctx.bot, chat_id))


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

    if text in ("Фильтры", "⚙️ Фильтры"):
        s = get_settings(chat_id)
        s["chat_id"] = chat_id
        await update.message.reply_text(
            fmt_settings(s), parse_mode="HTML", reply_markup=kb_settings(chat_id)
        )

    elif text in ("ВКЛ", "Включить", "🔔 Включить"):
        add_user(chat_id, update.effective_user.username or "")
        await update.message.reply_text(
            "🔔 Рассылка включена!", reply_markup=main_keyboard(chat_id)
        )

    elif text in ("ВЫКЛ", "Выключить", "🔕 Выключить"):
        remove_user(chat_id)
        await update.message.reply_text(
            "🔕 Рассылка выключена.", reply_markup=main_keyboard(chat_id)
        )

    elif text in ("Искать", "🔍 Искать"):
        await update.message.reply_text("Ищу предложения, ожидайте!")
        _spawn(_do_search(ctx.bot, chat_id))


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

    if data == "search_now":
        await query.message.reply_text("Ищу предложения, ожидайте!")
        _spawn(_do_search(query.message.get_bot(), chat_id))
        return

    # ✅ ИСПРАВЛЕНО: reset_filters был недоступен из-за return выше
    if data == "reset_filters":
        reset_settings(chat_id)
        await _back_settings(query, chat_id, "🔄 Фильтры сброшены до стандартных!")
        return

    if data == "menu_interval":
        await query.message.edit_text(
            "⏱ <b>Частота рассылки</b>\n\nКак часто проверять и присылать новые туры?",
            parse_mode="HTML",
            reply_markup=kb_interval(int(get_settings(chat_id).get("interval_min", 0)))
        )
        return

    if data == "menu_city":
        await query.message.edit_text(
            "🏙 <b>Город</b>", parse_mode="HTML", reply_markup=kb_city()
        )
        return

    if data == "menu_days":
        await query.message.edit_text(
            "📅 <b>Вылет в ближайшие...</b>", parse_mode="HTML",
            reply_markup=kb_days(int(get_settings(chat_id).get("days_filter", 0)))
        )
        return

    if data == "menu_price":
        s = get_settings(chat_id)
        current = s.get("price_ranges", "any")
        await query.message.edit_text(
            "💰 <b>Цена за 1 человека</b>\n"
            "<i>при условии, что в номере проживают 2 человека</i>",
            parse_mode="HTML",
            reply_markup=kb_price(current, int(s.get("price_max", 9999)))
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
        if key == "any":
            set_setting(chat_id, "price_min", 0)
            set_setting(chat_id, "price_max", 9999)
        set_setting(chat_id, "price_ranges", key)
        labels = {"any": "любая цена", "0-499": "0 – 500 €", "500-999": "500 – 1000 €", "1000-9999": "1000+ €", "500-9999": "500+ €"}
        await _back_settings(query, chat_id, f"✅ Цена: {labels.get(key, key)} (за 1 человека)")
        return

    if data == "price_toggle_any":
        set_setting(chat_id, "price_ranges", "any")
        set_setting(chat_id, "price_min", 0)
        set_setting(chat_id, "price_max", 9999)
        await _back_settings(query, chat_id, "✅ Цена: любая")
        return

    if data == "menu_stars":
        await query.message.edit_text(
            "🌟 <b>Звёзды</b>", parse_mode="HTML",
            reply_markup=kb_stars(int(get_settings(chat_id).get("stars_min", 0)),
                                  int(get_settings(chat_id).get("stars_max", 0)))
        )
        return

    if data == "menu_rating":
        s = get_settings(chat_id)
        await query.message.edit_text(
            "🏅 <b>Рейтинг отеля</b>\n<i>по Booking, от 1 до 10</i>",
            parse_mode="HTML", reply_markup=kb_rating(s.get("rating_min", 0)),
        )
        return

    if data.startswith("rating_"):
        value = int(data.split("_")[1])
        set_setting(chat_id, "rating_min", value)
        await _back_settings(query, chat_id, f"✅ Рейтинг: {value}+" if value else "✅ Рейтинг: любой")
        return

    if data == "menu_meal":
        await query.message.edit_text(
            "🍽 <b>Тип питания</b>", parse_mode="HTML",
            reply_markup=kb_meal(get_settings(chat_id).get("meal_filter", "any"))
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
            "🏨 <b>Сеть отелей</b>\n\nВыбери одну или несколько сетей",
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

    if data == "top_menu":
        await query.message.edit_text(
            "🏆 <b>Топ отелей</b>\n\nПопулярные отели у туристов, по рейтингу Booking.",
            parse_mode="HTML", reply_markup=kb_top_menu(),
        )
        return

    if data.startswith("top_") and data != "top_menu":
        parts = data.split("_")
        city = parts[1]
        page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        if city in ("hrg", "ssh"):
            await query.message.edit_text(
                _top_text(city, page), parse_mode="HTML", reply_markup=kb_top_list(city, page),
            )
        return

    if data == "chain_any":
        set_setting(chat_id, "chains_filter", "any")
        await _back_settings(query, chat_id, "✅ Сети: любая")
        return

    if data.startswith("meal_"):
        val = data[5:]
        set_setting(chat_id, "meal_filter", val)
        labels = {
            "ai,uai": "Всё включено",
            "any":    "Любое питание",
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
    try:
        if image and image.startswith("http"):
            await bot.send_photo(chat_id=chat_id, photo=image, caption=text, parse_mode="HTML")
        elif image and os.path.isfile(image):
            with open(image, "rb") as f:
                await bot.send_photo(chat_id=chat_id, photo=f, caption=text, parse_mode="HTML")
        else:
            raise ValueError("no image")
    except Exception:
        await bot.send_message(
            chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True
        )


def _dedup_tours(tours: list) -> list:
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
                best[key] = t
    logger.info(f"DEDUP: {len(tours)} → {len(best)} туров")
    return list(best.values())


SCRAPERS = [
    ("Delfiin", fetch_delfiin),
]


async def fetch_all_tours() -> list:
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

    if notify_users and app:
        now = datetime.now()
        cleanup_user_sent(30)
        for chat_id in get_active_users():
            s = get_settings(chat_id)
            interval = int(s.get("interval_min", config.CHECK_INTERVAL_MINUTES))

            # интервал для пользователя хранится в БД — переживает перезапуск бота
            last = get_last_notified(chat_id)
            if last is not None:
                elapsed_min = (now - last).total_seconds() / 60
                if elapsed_min < interval:
                    logger.info(f"Юзер {chat_id} — пропускаем, прошло {elapsed_min:.0f}/{interval} мин")
                    continue

            if interval >= 1440:
                interval_str = f"{interval // 1440} дн."
            elif interval >= 60:
                interval_str = f"{interval // 60} ч."
            else:
                interval_str = f"{interval} мин."

            user_tours = _dedup_tours([t for t in all_tours if passes_filters(t, s)])
            new_tours = [t for t in user_tours if not is_sent_to(chat_id, t)]
            new_tours.sort(key=lambda t: t.get("price", 0))
            set_last_notified(chat_id, now)

            if not new_tours:
                logger.info(f"Юзер {chat_id}: новых туров нет")
                continue

            pending = len(new_tours)
            new_tours = new_tours[:MAX_TOURS_PER_SEND]
            total_sent += len(new_tours)
            for tour in new_tours:
                try:
                    await _send_tour(app.bot, chat_id, tour)
                    mark_sent_to(chat_id, tour)
                    mark_sent(tour)
                    await asyncio.sleep(0.05)
                except (Forbidden, BadRequest) as e:
                    if isinstance(e, Forbidden) or "chat not found" in str(e).lower():
                        logger.warning(f"Юзер {chat_id} недоступен ({e}) — отключаю рассылку")
                        remove_user(chat_id)
                        break
                    logger.error(f"Ошибка отправки {chat_id}: {e}")
                except Exception as e:
                    logger.error(f"Ошибка отправки {chat_id}: {e}")
            else:
                try:
                    await app.bot.send_message(
                        chat_id,
                        f"✅ Новых туров: {pending}"
                        + (f" (показаны {len(new_tours)} самых дешёвых, остальные пришлю в следующий раз)"
                           if pending > len(new_tours) else "")
                        + ".\n"
                        f"⏱ Следующая проверка через {interval_str}"
                    )
                except Exception:
                    pass

    return all_tours


# ══════════════════════════════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════════════════════════════

def main():
    global _app
    init_db()
    logger.info("✅ БД готова")

    app = Application.builder().token(config.TELEGRAM_TOKEN).concurrent_updates(True).build()
    _app = app

    # защита от повторной обработки одного и того же апдейта (+ запись в журнал для диагностики)
    _seen_ids: set = set()
    _seen_order: list = []
    _last_text: dict = {}

    async def drop_duplicate_updates(update: Update, context):
        uid = update.update_id
        user = update.effective_user.id if update.effective_user else None
        if uid in _seen_ids:
            logger.warning(f"ДУБЛЬ апдейта {uid} от {user} — пропускаю")
            raise ApplicationHandlerStop
        _seen_ids.add(uid)
        _seen_order.append(uid)
        if len(_seen_order) > 1000:
            _seen_ids.discard(_seen_order.pop(0))
        msg = update.effective_message
        text = (msg.text or "")[:30] if msg else ""
        logger.info(f"апдейт {uid} от {user} msg={msg.message_id if msg else None} text={text!r}")
        # двойное нажатие / повтор одного и того же текста из одного чата в течение 2 секунд
        if update.message and update.message.text:
            key = (update.effective_chat.id, update.message.text)
            now_m = time.monotonic()
            if now_m - _last_text.get(key, 0) < 2.0:
                logger.warning(f"повтор текста {text!r} от {user} за <2 c — пропускаю")
                raise ApplicationHandlerStop
            _last_text[key] = now_m

    app.add_handler(TypeHandler(Update, drop_duplicate_updates), group=-1)

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("stop",   cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("last",   cmd_last))
    app.add_handler(CommandHandler("myid",   cmd_myid))
    app.add_handler(CallbackQueryHandler(on_button))
    async def on_error(update, context):
        err = context.error
        if isinstance(err, BadRequest) and "not modified" in str(err).lower():
            return  # повторное нажатие той же кнопки — не ошибка
        logger.error(f"Необработанная ошибка: {err!r}", exc_info=err)

    app.add_error_handler(on_error)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_button))

    scheduler = AsyncIOScheduler()

    # ✅ ИСПРАВЛЕНО: используем async def вместо lambda с ensure_future
    async def scheduled_check():
        await run_check(app=app, notify_users=True)

    scheduler.add_job(
        scheduled_check,
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
        try:
            from telegram import BotCommand
            await app.bot.set_my_commands([
                BotCommand("start",  "Запуск и поиск туров"),
                BotCommand("last",   "Последние найденные туры"),
                BotCommand("status", "Статус бота"),
                BotCommand("stop",   "Выключить рассылку"),
            ])
        except Exception as e:
            logger.warning(f"set_my_commands: {e}")
        logger.info(f"⏰ Планировщик: каждые {config.CHECK_INTERVAL_MINUTES} мин")
        await run_check(app=app, notify_users=True)

    async def on_shutdown(app):
        scheduler.shutdown()

    app.post_init = on_startup
    app.post_shutdown = on_shutdown

    logger.info("🤖 Бот запущен!")

    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()

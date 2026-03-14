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
    is_sent, mark_sent, get_recent_tours,
    get_settings, set_setting,
)
from filters import passes_filters
from formatter import format_tour, fmt_start, fmt_status, fmt_settings
from scrapers import fetch_novatours, fetch_teztour, fetch_coral, fetch_joinup

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


# ══════════════════════════════════════════════════════════════
#  ПОСТОЯННАЯ КЛАВИАТУРА ВНИЗУ
# ══════════════════════════════════════════════════════════════

def main_keyboard(chat_id: int) -> ReplyKeyboardMarkup:
    active = chat_id in get_active_users()
    toggle_label = "🔕 Выключить" if active else "🔔 Включить"
    return ReplyKeyboardMarkup(
        [[
            KeyboardButton("🔍 Проверить"),
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
            InlineKeyboardButton("⏱ Время",    callback_data="menu_interval"),
            InlineKeyboardButton("🏙 Город",   callback_data="menu_city"),
            InlineKeyboardButton("📅 Дни",     callback_data="menu_days"),
        ],
        [
            InlineKeyboardButton("💰 Цена",    callback_data="menu_price"),
            InlineKeyboardButton("🌟 Звёзды",  callback_data="menu_stars"),
            InlineKeyboardButton("🍽 Питание", callback_data="menu_meal"),
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
            InlineKeyboardButton("30 дней",  callback_data="days_30"),
            InlineKeyboardButton("180 дней", callback_data="days_180"),
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="settings")],
    ])


def kb_price() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("200€", callback_data="price_200"),
            InlineKeyboardButton("400€", callback_data="price_400"),
            InlineKeyboardButton("600€", callback_data="price_600"),
        ],
        [
            InlineKeyboardButton("800€",       callback_data="price_800"),
            InlineKeyboardButton("1000€",      callback_data="price_1000"),
            InlineKeyboardButton("Без лимита", callback_data="price_9999"),
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


def kb_meal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍽️ Все включено (AI)",           callback_data="meal_ai,uai")],
        [InlineKeyboardButton("🍽️🍽️ Ультра все включено (UAI)", callback_data="meal_uai")],
        [InlineKeyboardButton("🥐 Только завтраки (BB)",         callback_data="meal_bb")],
        [InlineKeyboardButton("🏨 Без питания (RO)",             callback_data="meal_ro")],
        [InlineKeyboardButton("🍴 Любое питание",                callback_data="meal_any")],
        [InlineKeyboardButton("◀️ Назад",                        callback_data="settings")],
    ])


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
    await update.message.reply_text("🔍 Ищу горящие туры, подождите...")
    found = await run_check(notify_users=False)
    s = get_settings(chat_id)
    user_tours = [t for t in found if passes_filters(t, s)]
    if user_tours:
        for tour in user_tours[:5]:
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
        fmt_status(len(get_active_users()), last_check_time, total_sent),
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

    elif text == "🔍 Проверить":
        await update.message.reply_text("🔍 Проверяю...")
        all_tours = await fetch_all_tours()
        s = get_settings(chat_id)
        user_tours = [t for t in all_tours if passes_filters(t, s)]
        if user_tours:
            for tour in user_tours[:5]:
                await _send_tour(ctx.bot, chat_id, tour)
        else:
            await update.message.reply_text("😕 Горящих туров по вашим фильтрам сейчас нет.")


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
        from config import MAX_PRICE_EUR
        set_setting(chat_id, "interval_min", 30)
        set_setting(chat_id, "meal_filter", "any")
        set_setting(chat_id, "stars_min", 3)
        set_setting(chat_id, "stars_max", 5)
        set_setting(chat_id, "city_filter", "all")
        set_setting(chat_id, "price_max", 9999)
        set_setting(chat_id, "days_filter", 180)
        await _back_settings(query, chat_id, "🔄 Фильтры сброшены до стандартных!")
        return

    if data == "menu_interval":
        await query.message.edit_text(
            "⏱ <b>Частота обновлений</b>\n\nКак часто проверять и присылать новые туры?",
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
        await query.message.edit_text(
            "💰 <b>Максимальная цена</b>\n\nЗа 1 человека при двухместном размещении:",
            parse_mode="HTML", reply_markup=kb_price()
        )
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

    # ── Интервал ─────────────────────────────────────────────
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

    # ── Город ────────────────────────────────────────────────
    if data.startswith("city_"):
        val = data[5:]
        set_setting(chat_id, "city_filter", val)
        labels = {"all": "🏙 Все города", "hrg": "🌊 Хургада", "ssh": "🏔 Шарм"}
        await _back_settings(query, chat_id, f"✅ Город: {labels.get(val, val)}")
        return

    # ── Дни ──────────────────────────────────────────────────
    if data.startswith("days_"):
        val = int(data.split("_")[1])
        set_setting(chat_id, "days_filter", val)
        await _back_settings(query, chat_id, f"✅ Вылет в ближайшие: {val} дней")
        return

    # ── Цена ─────────────────────────────────────────────────
    if data.startswith("price_"):
        val = int(data.split("_")[1])
        set_setting(chat_id, "price_max", val)
        label = "без лимита" if val == 9999 else f"{val}€"
        await _back_settings(query, chat_id, f"✅ Макс. цена: {label}")
        return

    # ── Звёзды ───────────────────────────────────────────────
    if data.startswith("stars_"):
        parts = data.split("_")
        mn, mx = int(parts[1]), int(parts[2])
        set_setting(chat_id, "stars_min", mn)
        set_setting(chat_id, "stars_max", mx)
        await _back_settings(query, chat_id, f"✅ Звёзды: {mn}★ — {mx}★")
        return

    # ── Питание ──────────────────────────────────────────────
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
    if image and image.startswith("http"):
        try:
            await bot.send_photo(chat_id=chat_id, photo=image, caption=text, parse_mode="HTML")
            return
        except Exception:
            pass
    await bot.send_message(
        chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True
    )


# ══════════════════════════════════════════════════════════════
#  ПРОВЕРКА ТУРОВ
# ══════════════════════════════════════════════════════════════

SCRAPERS = [
    ("Novatours",    fetch_novatours),
    # ("TEZ Tour",     fetch_teztour),
    # ("Coral Travel", fetch_coral),
    # ("Join Up",      fetch_joinup),
]



async def fetch_all_tours() -> list:
    """Получает все актуальные туры без фильтра is_sent — для кнопки Проверить."""
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

    new_tours = []
    for tour in all_tours:
        if passes_filters(tour) and not is_sent(tour):
            mark_sent(tour)
            new_tours.append(tour)

    logger.info(f"🔥 Новых горящих: {len(new_tours)}")

    if new_tours and notify_users and app:
        total_sent += len(new_tours)
        for chat_id in get_active_users():
            s = get_settings(chat_id)
            user_tours = [t for t in new_tours if passes_filters(t, s)]
            for tour in user_tours[:5]:
                try:
                    await _send_tour(app.bot, chat_id, tour)
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.error(f"Ошибка отправки {chat_id}: {e}")

    return new_tours


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
                await app.bot.send_message(
                    cid, "🤖 Бот запущен!", reply_markup=main_keyboard(cid)
                )
            except Exception:
                pass
        await run_check(app=app, notify_users=True)

    async def on_shutdown(app):
        scheduler.shutdown()

    app.post_init = on_startup
    app.post_shutdown = on_shutdown

    logger.info("🤖 Бот запущен!")
    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()

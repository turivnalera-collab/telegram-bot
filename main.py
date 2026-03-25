import json
import asyncio

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ====== ТОКЕНЫ 4 БОТОВ ======
TOKEN_MAIN_1 = "8786002373:AAHFQX78hxHeT5S7SERYIutPLkOkmpspUkA"
TOKEN_MAIN_2 = "8644658987:AAEO2zgmpxY1UnGs_6A0MBIV9PZyk9ojTSE"
TOKEN_MAIN_3 = "8713831482:AAFN3j0xMP9uO263cOmFBiKaZJAGBEWiNkU"
TOKEN_MAIN_4 = "8613237521:AAEL7K1vMLgPLWrvL8sauzvpS9tXkMIBZVE"

# ====== КАНАЛЫ ДЛЯ КАЖДОГО БОТА ======
CHANNEL_ID_1 = -1003753174612
CHANNEL_ID_2 = -1003710727439
CHANNEL_ID_3 = -1003828265452
CHANNEL_ID_4 = -1003879420900

STATE_FILE = "state.json"

(FROM_WHERE, PHONE_TYPE, GAME_TYPE, CONFIRM) = range(4)

# ====== СОСТОЯНИЕ ======
def get_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        s = {"active": True, "users": 0, "user_ids": []}
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False)
        return s

def is_active():
    return get_state().get("active", True)

def update_user(uid: int):
    s = get_state()
    s.setdefault("user_ids", [])
    if uid not in s["user_ids"]:
        s["user_ids"].append(uid)
        s["users"] = len(s["user_ids"])
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False)

# ====== ОСНОВНЫЕ ФУНКЦИИ ======
async def block_if_off(update: Update):
    if not is_active():
        if update.message:
            await update.message.reply_text("🚫 Бот временно выключен.")
        return True
    return False

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await block_if_off(update):
        return ConversationHandler.END

    update_user(update.effective_user.id)

    countries = [['Украина 🇺🇦'], ['Казахстан 🇰🇿'], ['Россия 🇷🇺'], ['Другое 🌐']]
    await update.message.reply_text("Привет! 👋 Заполни короткую заявку 📋")
    await update.message.reply_text(
        "Откуда вы?",
        reply_markup=ReplyKeyboardMarkup(
            countries,
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return FROM_WHERE

async def from_where(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await block_if_off(update):
        return ConversationHandler.END

    ctx.user_data["country"] = update.message.text

    phones = [['iOS 🍎'], ['Android 🤖']]
    await update.message.reply_text(
        "Какой у вас телефон?",
        reply_markup=ReplyKeyboardMarkup(
            phones,
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return PHONE_TYPE

async def phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await block_if_off(update):
        return ConversationHandler.END

    ctx.user_data["phone"] = update.message.text

    if update.message.text == "Android 🤖":
        c = ctx.user_data.get("country", "—")
        card = (
            f"🎉 Новая заявка от {update.effective_user.username or update.effective_user.full_name}\n\n"
            f"🌍 Страна: {c}\n"
            f"📱 Устройство: Android 🤖\n"
            f"💵 Платно\n\n"
            f"📨 Отправить заявку?"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 Отправить", callback_data="send_admin")]
        ])
        await update.message.reply_text(card, reply_markup=kb)
        return CONFIRM

    games = [['Standoff 🔫'], ['PUBG 🎯'], ['Minecraft ⛏️']]
    await update.message.reply_text(
        "На какую игру нужен софт? 🎮",
        reply_markup=ReplyKeyboardMarkup(
            games,
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return GAME_TYPE

async def game(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await block_if_off(update):
        return ConversationHandler.END

    ctx.user_data["game"] = update.message.text

    c = ctx.user_data.get("country", "—")
    p = ctx.user_data.get("phone", "—")
    g = ctx.user_data.get("game", "—")

    card = (
        f"🎉 Новая заявка от {update.effective_user.username or update.effective_user.full_name}\n\n"
        f"🌍 Страна: {c}\n"
        f"📱 Устройство: {p}\n"
        f"🎮 Игра: {g}\n\n"
        f"📨 Отправить заявку?"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Отправить", callback_data="send_admin")]
    ])
    await update.message.reply_text(card, reply_markup=kb)
    return CONFIRM

async def send_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user = q.from_user
    d = ctx.user_data

    username = f"@{user.username}" if user.username else user.full_name

    msg = (
        f"📬 Новая заявка от {username}\n\n"
        f"🌍 Страна: {d.get('country', '—')}\n"
        f"📱 Устройство: {d.get('phone', '—')}\n"
        f"🎮 Игра: {d.get('game', '—')}"
    )

    try:
        channel_id = ctx.application.bot_data["channel_id"]
        await ctx.bot.send_message(chat_id=channel_id, text=msg)
        await q.edit_message_text("✅ Заявка отправлена!")
    except Exception as e:
        await q.edit_message_text(f"⚠️ Ошибка: {e}")

    return ConversationHandler.END

# ====== СОЗДАНИЕ ОДНОГО БОТА ======
def build_app(token: str, bot_name: str, channel_id: int):
    app = Application.builder().token(token).build()
    app.bot_data["channel_id"] = channel_id

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FROM_WHERE: [MessageHandler(filters.TEXT & ~filters.COMMAND, from_where)],
            PHONE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
            GAME_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, game)],
            CONFIRM: [CallbackQueryHandler(send_admin, pattern="^send_admin$")],
        },
        fallbacks=[],
        per_chat=True,
        per_user=True,
        per_message=False,
    )

    app.add_handler(conv)
    print(f"🟢 {bot_name} создан.")
    return app

async def start_app(app: Application, bot_name: str):
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    print(f"✅ {bot_name} запущен.")

async def stop_app(app: Application, bot_name: str):
    try:
        if app.updater:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()
        print(f"⛔ {bot_name} остановлен.")
    except Exception as e:
        print(f"Ошибка при остановке {bot_name}: {e}")

# ====== MAIN ДЛЯ HEROKU ======
async def main():
    app1 = build_app(TOKEN_MAIN_1, "Бот 1", CHANNEL_ID_1)
    app2 = build_app(TOKEN_MAIN_2, "Бот 2", CHANNEL_ID_2)
    app3 = build_app(TOKEN_MAIN_3, "Бот 3", CHANNEL_ID_3)
    app4 = build_app(TOKEN_MAIN_4, "Бот 4", CHANNEL_ID_4)

    apps = [
        (app1, "Бот 1"),
        (app2, "Бот 2"),
        (app3, "Бот 3"),
        (app4, "Бот 4"),
    ]

    try:
        for app, name in apps:
            await start_app(app, name)

        print("🚀 Все 4 бота запущены на Heroku.")
        await asyncio.Event().wait()

    finally:
        for app, name in apps:
            await stop_app(app, name)

if __name__ == "__main__":
    asyncio.run(main())














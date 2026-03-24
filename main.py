import json, asyncio, os
from aiohttp import web
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# ==== НАСТРОЙКИ ====
TOKEN_MAIN = "8265115212:AAHkqg6km67v_GJOTpjKVHTW8pKy6zSXbUc"
TOKEN_ADMIN = "8629071305:AAEWcYh4KQgDOcJdJxy1XjKzNc7aEZm2ZpY"
ADMIN_ID = 607368382                              # твой Telegram ID
ADMIN_CHANNEL_ID = -1003568920377                 # канал или чат для заявок
HEROKU_APP_NAME = "my-telegram"                   # имя твоего приложения на Heroku
PORT = int(os.environ.get("PORT", 8443))
STATE_FILE = "state.json"

(FROM_WHERE, PHONE_TYPE, GAME_TYPE, CONFIRM) = range(4)

# ==== РАБОТА С СОСТОЯНИЕМ ====
def get_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        s = {"active": True, "users": 0, "user_ids": []}
        with open(STATE_FILE, "w") as f:
            json.dump(s, f)
        return s

def set_active(v: bool):
    s = get_state()
    s["active"] = v
    with open(STATE_FILE, "w") as f:
        json.dump(s, f)

def is_active():
    return get_state().get("active", True)

def update_user(uid):
    s = get_state()
    if uid not in s.get("user_ids", []):
        s["user_ids"].append(uid)
        s["users"] = len(s["user_ids"])
        with open(STATE_FILE, "w") as f:
            json.dump(s, f)

# ==== ОСНОВНОЙ БОТ ====
async def block_if_off(update: Update):
    if not is_active():
        await update.message.reply_text("🚫 Бот временно выключен администратором.")
        return True
    return False

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await block_if_off(update):
        return ConversationHandler.END
    update_user(update.effective_user.id)
    await update.message.reply_text("Привет! 👋 Заполни короткую заявку 📋")
    countries = [["Украина 🇺🇦"], ["Казахстан 🇰🇿"], ["Россия 🇷🇺"], ["Другое 🌐"]]
    await update.message.reply_text(
        "Откуда вы?",
        reply_markup={"keyboard": countries, "resize_keyboard": True, "one_time_keyboard": True}
    )
    return FROM_WHERE

async def from_where(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await block_if_off(update):
        return ConversationHandler.END
    ctx.user_data["country"] = update.message.text
    phones = [["iOS 🍎"], ["Android 🤖"]]
    await update.message.reply_text(
        "Какой у вас телефон?",
        reply_markup={"keyboard": phones, "resize_keyboard": True, "one_time_keyboard": True}
    )
    return PHONE_TYPE

async def phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await block_if_off(update):
        return ConversationHandler.END
    ctx.user_data["phone"] = update.message.text
    if ctx.user_data["phone"] == "Android 🤖":
        c = ctx.user_data.get("country", "—")
        text = (
            f"🎉 Новая заявка от {update.effective_user.full_name}\n"
            f"🌍 Страна: {c}\n📱 Устройство: Android 🤖\n💵 Платно.\n\nОтправить заявку?"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📩 Отправить", callback_data="send_admin")]])
        await update.message.reply_text(text, reply_markup=kb)
        return CONFIRM
    games = [["Standoff 🔫"], ["PUBG 🎯"], ["Clash of Clans ⚔️"]]
    await update.message.reply_text(
        "На какую игру нужен софт? 🎮",
        reply_markup={"keyboard": games, "resize_keyboard": True, "one_time_keyboard": True}
    )
    return GAME_TYPE

async def game(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await block_if_off(update):
        return ConversationHandler.END
    ctx.user_data["game"] = update.message.text
    c, p, g = ctx.user_data.get("country", "—"), ctx.user_data.get("phone", "—"), ctx.user_data["game"]
    card = (
        f"🎉 Новая заявка:\n🌍 {c}\n📱 {p}\n🎮 {g}\n\n📨 Отправить заявку администратору?"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📩 Отправить", callback_data="send_admin")]])
    await update.message.reply_text(card, reply_markup=kb)
    return CONFIRM

async def send_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    d = ctx.user_data
    msg = (
        f"📬 Новая заявка от @{user.username or user.full_name}\n"
        f"🌍 {d.get('country', '—')}\n📱 {d.get('phone', '—')}\n🎮 {d.get('game', '—')}"
    )
    try:
        await ctx.bot.send_message(ADMIN_CHANNEL_ID, msg)
        await q.edit_message_text("✅ Заявка отправлена администратору!")
    except Exception as e:
        await q.edit_message_text(f"⚠️ Ошибка: {e}")
    return ConversationHandler.END

# ==== АДМИН БОТ ====
async def require_admin(update: Update):
    return update.effective_user.id == ADMIN_ID

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    kb = [
        [
            InlineKeyboardButton("🟢 Включить", callback_data="turn_on"),
            InlineKeyboardButton("🔴 Выключить", callback_data="turn_off")
        ],
        [InlineKeyboardButton("📊 Статус", callback_data="status")]
    ]
    st = "🟢 ВКЛЮЧЕН" if is_active() else "🔴 ВЫКЛЮЧЕН"
    await update.message.reply_text(f"⚙️ Панель администратора\nСтатус: {st}", reply_markup=InlineKeyboardMarkup(kb))

async def panel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != ADMIN_ID:
        await q.edit_message_text("⛔ Нет доступа.")
        return
    data = q.data
    if data == "turn_on":
        set_active(True)
        t = "✅ Основной бот включен."
    elif data == "turn_off":
        set_active(False)
        t = "🚫 Основной бот выключен."
    else:
        t = "📊 Статус: " + ("🟢 ВКЛЮЧЕН" if is_active() else "🔴 ВЫКЛЮЧЕН")
    kb = [
        [
            InlineKeyboardButton("🟢 Включить", callback_data="turn_on"),
            InlineKeyboardButton("🔴 Выключить", callback_data="turn_off")
        ],
        [InlineKeyboardButton("📊 Статус", callback_data="status")]
    ]
    await q.edit_message_text(f"{t}\n⚙️ Панель администратора", reply_markup=InlineKeyboardMarkup(kb))

# ==== ЗАПУСК ОБОИХ С WEBHOOK ====
async def run_both():
    main = Application.builder().token(TOKEN_MAIN).build()
    admin = Application.builder().token(TOKEN_ADMIN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FROM_WHERE: [MessageHandler(filters.TEXT & ~filters.COMMAND, from_where)],
            PHONE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
            GAME_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, game)],
            CONFIRM: [CallbackQueryHandler(send_admin, pattern="send_admin")]
        },
        fallbacks=[]
    )
    main.add_handler(conv)
    admin.add_handler(CommandHandler("start", cmd_start))
    admin.add_handler(CallbackQueryHandler(panel))

    # Создаём URL для webhook
    url_main = f"[{heroku_app_name}.herokuapp.com](https://{HEROKU_APP_NAME}.herokuapp.com/{TOKEN_MAIN})"
    url_admin = f"[{heroku_app_name}.herokuapp.com](https://{HEROKU_APP_NAME}.herokuapp.com/{TOKEN_ADMIN})"


    await main.bot.setWebhook(url=url_main)
    await admin.bot.setWebhook(url=url_admin)
    print("🌐 Вебхуки установлены")

    app = web.Application()
    app.add_routes([
        web.post(f"/{TOKEN_MAIN}", main.webhook_handler),
        web.post(f"/{TOKEN_ADMIN}", admin.webhook_handler),
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🚀 Слушаем порт {PORT} на Heroku…")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(run_both())








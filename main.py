import json, asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler,
    ContextTypes, filters
)

TOKEN_MAIN = "8265115212:AAHkqg6km67v_GJOTpjKVHTW8pKy6zSXbUc"
TOKEN_ADMIN = "8629071305:AAEWcYh4KQgDOcJdJxy1XjKzNc7aEZm2ZpY"
ADMIN_ID = 607368382
ADMIN_CHANNEL_ID = -1003568920377
STATE_FILE = "state.json"

(FROM_WHERE, PHONE_TYPE, GAME_TYPE, CONFIRM) = range(4)

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

# ==== Основной бот ====
async def block_if_off(update: Update):
    if not is_active():
        await update.message.reply_text("🚫 Бот временно выключен администратором.")
        return True
    return False

async def start(update: Update, ctx):
    if await block_if_off(update):
        return ConversationHandler.END
    update_user(update.effective_user.id)
    await update.message.reply_text("Привет 👋, заполни заявку 📋")
    countries = [["Украина 🇺🇦"], ["Казахстан 🇰🇿"], ["Россия 🇷🇺"], ["Другое 🌐"]]
    await update.message.reply_text(
        "Откуда вы?",
        reply_markup={"keyboard": countries, "resize_keyboard": True, "one_time_keyboard": True}
    )
    return FROM_WHERE

async def from_where(update: Update, ctx):
    ctx.user_data["country"] = update.message.text
    phones = [["iOS 🍎"], ["Android 🤖"]]
    await update.message.reply_text(
        "Какой у вас телефон?",
        reply_markup={"keyboard": phones, "resize_keyboard": True, "one_time_keyboard": True}
    )
    return PHONE_TYPE

async def phone(update: Update, ctx):
    ctx.user_data["phone"] = update.message.text
    if ctx.user_data["phone"] == "Android 🤖":
        c = ctx.user_data.get("country", "—")
        text = f"🎉 Заявка:\n🌍 {c}\n📱 Android 🤖\n💵 Платно"
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📩 Отправить", callback_data="send_admin")]])
        )
        return CONFIRM
    games = [["Standoff 🔫"], ["PUBG 🎯"], ["Clash of Clans ⚔️"]]
    await update.message.reply_text(
        "На какую игру нужен софт? 🎮",
        reply_markup={"keyboard": games, "resize_keyboard": True, "one_time_keyboard": True}
    )
    return GAME_TYPE

async def game(update: Update, ctx):
    ctx.user_data["game"] = update.message.text
    c = ctx.user_data.get("country", "—")
    p = ctx.user_data.get("phone", "—")
    g = ctx.user_data["game"]
    text = f"🎉 Заявка:\n🌍 {c}\n📱 {p}\n🎮 {g}"
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📩 Отправить", callback_data="send_admin")]])
    )
    return CONFIRM

async def send_admin(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    d = ctx.user_data
    msg = (
        f"📬 Заявка от @{user.username or user.full_name}\n"
        f"🌍 {d.get('country', '—')}\n📱 {d.get('phone', '—')}\n🎮 {d.get('game', '—')}"
    )
    await ctx.bot.send_message(ADMIN_CHANNEL_ID, msg)
    await q.edit_message_text("✅ Отправлено администратору!")
    return ConversationHandler.END

# ==== Админ-бот ====
async def cmd_start(update: Update, ctx):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ Нет доступа.")
    kb = [
        [
            InlineKeyboardButton("🟢 Включить", callback_data="on"),
            InlineKeyboardButton("🔴 Выключить", callback_data="off")
        ],
        [InlineKeyboardButton("📊 Статус", callback_data="status")]
    ]
    st = "🟢 ВКЛЮЧЕН" if is_active() else "🔴 ВЫКЛЮЧЕН"
    await update.message.reply_text(f"⚙️ Панель администратора\nСтатус: {st}", reply_markup=InlineKeyboardMarkup(kb))

async def panel(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != ADMIN_ID:
        return await q.edit_message_text("⛔ Нет доступа.")
    if q.data == "on":
        set_active(True)
        t = "✅ Включён"
    elif q.data == "off":
        set_active(False)
        t = "🚫 Выключен"
    else:
        t = "📊 Статус: " + ("🟢 ВКЛЮЧЕН" if is_active() else "🔴 ВЫКЛЮЧЕН")
    kb = [
        [InlineKeyboardButton("🟢 Включить", callback_data="on"), InlineKeyboardButton("🔴 Выключить", callback_data="off")],
        [InlineKeyboardButton("📊 Статус", callback_data="status")]
    ]
    await q.edit_message_text(f"{t}\n⚙️ Панель администратора", reply_markup=InlineKeyboardMarkup(kb))

# ==== Запуск обоих ====
async def main():
    main_app = Application.builder().token(TOKEN_MAIN).build()
    admin_app = Application.builder().token(TOKEN_ADMIN).build()

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
    main_app.add_handler(conv)

    admin_app.add_handler(CommandHandler("start", cmd_start))
    admin_app.add_handler(CallbackQueryHandler(panel))

    print("🟢 Оба приложения инициализированы")
    await asyncio.gather(
        main_app.start(),
        admin_app.start(),
        main_app.updater.start_polling(),
        admin_app.updater.start_polling(),
    )


if __name__ == "__main__":
    asyncio.run(main())









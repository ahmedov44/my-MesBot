
import json
import os
import random
import time
import nest_asyncio
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

nest_asyncio.apply()

TOKEN = os.getenv("BOT_TOKEN")
AUTHORIZED_USER_IDS = [5257767076, 7924310880]
SCORE_FILE = "scores.json"
PLAYER_FILE = "players.json"

words = ["Alma", "Armud", "Ərik", "Nar", "Mars", "Futbol", "Şahmat"]
user_stats = {}
user_words = {}
user_thoughts = {}

def load_data():
    global user_stats, user_words
    try:
        with open(SCORE_FILE, "r") as f:
            user_stats = json.load(f)
    except:
        user_stats = {}
    try:
        with open(PLAYER_FILE, "r") as f:
            user_words = json.load(f)
    except:
        user_words = {}

def save_data():
    with open(SCORE_FILE, "w") as f:
        json.dump(user_stats, f)
    with open(PLAYER_FILE, "w") as f:
        json.dump(user_words, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in AUTHORIZED_USER_IDS:
        await update.message.reply_text("❌ Bu əmri yalnız adminlər işlədə bilər.")
        return

    user_id = str(update.effective_user.id)
    word = random.choice(words)
    context.user_data["current_word"] = word
    context.user_data["awaiting_thought"] = False
    user_words[user_id] = word
    user_stats.setdefault(user_id, 0)

    keyboard = [
        [
            InlineKeyboardButton("📌 Sözü göstər", callback_data="show_word"),
            InlineKeyboardButton("🔁 Növbəti söz", callback_data="next"),
        ],
        [InlineKeyboardButton("📝 Fikrimi dəyişdim", callback_data="change_thought")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🟢 OYUN AKTİVDİR.
🔤 Söz: {word}", reply_markup=reply_markup
    )
    save_data()

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in AUTHORIZED_USER_IDS:
        await update.message.reply_text("❌ Bu əmri yalnız adminlər işlədə bilər.")
        return
    await update.message.reply_text("🔴 Oyun dayandırıldı.")
    save_data()

async def rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ratings = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)
    message = "🏆 Reytinq:
"
    for user_id, score in ratings:
        user = await context.bot.get_chat(user_id)
        name = user.first_name
        message += f"{name}: {score} xal
"
    if message == "🏆 Reytinq:
":
        message = "ℹ️ Hələ heç kim xal qazanmamayıb."
    await update.message.reply_text(message)

async def global_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(SCORE_FILE, "r") as f:
            all_scores = json.load(f)
    except FileNotFoundError:
        all_scores = {}
    if not all_scores:
        await update.message.reply_text("ℹ️ Ümumi xal məlumatı yoxdur.")
        return

    sorted_scores = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
    message = "🌍 Ümumi Reytinq:
"
    for user_id, score in sorted_scores:
        user = await context.bot.get_chat(user_id)
        name = user.first_name
        message += f"{name}: {score} xal
"
    await update.message.reply_text(message)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if context.user_data.get("awaiting_thought"):
        context.user_data["awaiting_thought"] = False
        user_stats[user_id] += 1
        user_thoughts[user_id] = update.message.text
        await update.message.reply_text("✅ Fikrin qəbul edildi. 1 xal qazandınız.")
        save_data()
    else:
        await update.message.reply_text("ℹ️ Zəhmət olmasa uyğun əmrdən istifadə edin.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if query.data == "next":
        word = random.choice(words)
        context.user_data["current_word"] = word
        user_words[user_id] = word
        await query.edit_message_text(f"🔤 Yeni söz: {word}")
    elif query.data == "change_thought":
        context.user_data["awaiting_thought"] = True
        await query.edit_message_text("📝 Zəhmət olmasa yeni fikrinizi göndərin.")
    elif query.data == "show_word":
        word = context.user_data.get("current_word", "Tapılmadı.")
        await query.edit_message_text(f"📌 Cari söz: {word}")

def main():
    load_data()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("basla", start))
    app.add_handler(CommandHandler("dayan", stop))
    app.add_handler(CommandHandler("reyting", rating))
    app.add_handler(CommandHandler("globalreyting", global_rating))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()

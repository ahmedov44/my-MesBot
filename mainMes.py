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
active_games = {}
current_word = {}
used_words = {}

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

user_stats = load_json(SCORE_FILE)
used_words = load_json(PLAYER_FILE)

def get_new_word(chat_id):
    available_words = list(set(words) - set(used_words.get(str(chat_id), [])))
    if not available_words:
        used_words[str(chat_id)] = []
        available_words = words.copy()
    word = random.choice(available_words)
    used_words.setdefault(str(chat_id), []).append(word)
    save_json(used_words, PLAYER_FILE)
    return word

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "group":
        await update.message.reply_text("Bu əmri yalnız qrup daxilində istifadə edin.")
        return
    chat_id = update.effective_chat.id
    current_word[chat_id] = get_new_word(chat_id)
    active_games[chat_id] = True
    await update.message.reply_text("🔁 OYUN AKTİVDİR.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in active_games:
        del active_games[chat_id]
        await update.message.reply_text("🛑 Oyun dayandırıldı.")
    else:
        await update.message.reply_text("Aktiv oyun yoxdur.")

async def show_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_scores = user_stats.get(str(chat_id), {})
    if not chat_scores:
        await update.message.reply_text("❌ Hələ heç kim xal qazanmamayıb.")
        return

    sorted_scores = sorted(chat_scores.items(), key=lambda x: x[1], reverse=True)
    text = "📊 Qrup üzrə reytinq:\n\n"
    for i, (user, score) in enumerate(sorted_scores, 1):
        text += f"{i}. {user}: {score} xal\n"
    await update.message.reply_text(text)

async def global_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_scores = {}
    for group_scores in user_stats.values():
        for user, score in group_scores.items():
            all_scores[user] = all_scores.get(user, 0) + score

    if not all_scores:
        await update.message.reply_text("❌ Ümumi xal məlumatı yoxdur.")
        return

    sorted_scores = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
    text = "🌐 Ümumi reytinq:\n\n"
    for i, (user, score) in enumerate(sorted_scores, 1):
        text += f"{i}. {user}: {score} xal\n"
    await update.message.reply_text(text)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user_name = message.from_user.first_name
    text = message.text.strip()

    if chat_id in active_games:
        correct = current_word.get(chat_id)
        if not correct:
            return

        if text.lower() == correct.lower():
            user_stats.setdefault(str(chat_id), {})
            user_stats[str(chat_id)][user_name] = user_stats[str(chat_id)].get(user_name, 0) + 1
            save_json(user_stats, SCORE_FILE)

            keyboard = [
                [
                    InlineKeyboardButton("➡ Növbəti söz", callback_data="next_word"),
                    InlineKeyboardButton("❌ Fikrimi dəyişdim", callback_data="cancel_game")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.reply_text("✅ Düzgün tapdınız!", reply_markup=reply_markup)
        else:
            await message.reply_text("❌ Yanlışdır!")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()

    if query.data == "next_word":
        current_word[chat_id] = get_new_word(chat_id)
        await query.message.reply_text("Yeni söz təyin edildi. Davam edin!")
    elif query.data == "cancel_game":
        active_games.pop(chat_id, None)
        current_word.pop(chat_id, None)
        await query.message.reply_text("Oyun ləğv edildi.")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("basla", start))
    app.add_handler(CommandHandler("dayan", stop))
    app.add_handler(CommandHandler("reyting", show_score))
    app.add_handler(CommandHandler("globalreyting", global_score))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Bot işə düşdü...")
    app.run_polling()

if __name__ == "__main__":
    main()

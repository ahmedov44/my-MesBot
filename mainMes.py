import json
import os
import random
import time
import nest_asyncio
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

nest_asyncio.apply()

TOKEN = os.getenv("BOT_TOKEN")
AUTHORIZED_USER_IDS = [5257767076, 7924310880]
SCORE_FILE = "scores.json"
PLAYER_FILE = "players.json"

# --- WORDS omitted for brevity in this snippet, assume it's the same ---
words = [ "Rusca", "Ingiliscə" ]

game_active = {}
game_master_id = {}
scoreboard = {}
global_scoreboard = {}
used_words = {}
current_word = {}
waiting_for_new_master = {}
player_names = {}
last_activity = {}

def az_lower(text):
    replacements = {"İ": "i", "I": "ı", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç", "Ə": "ə"}
    for big, small in replacements.items():
        text = text.replace(big, small)
    return text.casefold()

def get_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Növbəti söz♻️", callback_data="skip")],
        [InlineKeyboardButton("Sözü göstər🔎", callback_data="show")],
        [InlineKeyboardButton("Fikrimi dəyişdim❌", callback_data="change")],
    ])

def get_new_host_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Aparıcı olmaq istəyirəm! 🎤", callback_data="become_master")]
    ])

def load_scores():
    global scoreboard, player_names
    if os.path.exists(SCORE_FILE):
        with open(SCORE_FILE, "r", encoding="utf-8") as f:
            scoreboard.update(json.load(f))
    if os.path.exists(PLAYER_FILE):
        with open(PLAYER_FILE, "r", encoding="utf-8") as f:
            player_names.update(json.load(f))

def render_bar(score, max_score, length=10):
    filled_length = int(length * score / max_score) if max_score > 0 else 0
    return "▓" * filled_length + "░" * (length - filled_length)

def add_score(chat_id: str, user_id: int, user_name: str, points: int = 1):
    if chat_id not in scoreboard:
        scoreboard[chat_id] = {}
    if user_id not in scoreboard[chat_id]:
        scoreboard[chat_id][user_id] = {"name": user_name, "score": 0}
    scoreboard[chat_id][user_id]["score"] += points

    if user_id not in global_scoreboard:
        global_scoreboard[user_id] = {"name": user_name, "score": 0}
    global_scoreboard[user_id]["score"] += points

def save_scores():
    with open(SCORE_FILE, "w", encoding="utf-8") as f:
        json.dump(scoreboard, f, ensure_ascii=False)
    with open(PLAYER_FILE, "w", encoding="utf-8") as f:
        json.dump(player_names, f, ensure_ascii=False)

def update_activity(chat_id):
    last_activity[chat_id] = time.time()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salam! Oyun botuna xoş gəlmisiniz.\nBaşlamaq üçün /basla yazın.")

async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    user = update.effective_user

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Bu əmri yalnız qrup daxilində istifadə edə bilərsiniz.")
        return

    bot_member = await chat.get_member(context.bot.id)
    if bot_member.status != "administrator":
        await update.message.reply_text("‼️ Salam! Mən MəşBotam (Söz Tapmaq oyunu), botu aktivləşdirmək üçün zəhmət olmasa mesajları silmə və mesajları sabitləmək səlahiyyətini verin.")
        return

    member = await chat.get_member(user.id)
    if member.status not in ["administrator", "creator"] and user.id not in AUTHORIZED_USER_IDS:
        await update.message.reply_text("DƏFOL! ADMİNİN İŞİNƏ QARIŞMA.")
        return

    if game_active.get(chat_id, False):
        await update.message.reply_text("DƏFOL! OYUN AKTİVDİR.")
        return

    game_active[chat_id] = True
    waiting_for_new_master[chat_id] = False
    used_words.setdefault(chat_id, [])
    scoreboard.setdefault(chat_id, {})
    game_master_id[chat_id] = user.id

    while True:
        nxt = random.choice(words)
        if nxt not in used_words[chat_id]:
            current_word[chat_id] = nxt
            used_words[chat_id].append(nxt)
            break

    update_activity(chat_id)

    await update.message.reply_text(
        f"Oyun başladı!\nAparıcı: {user.first_name}\nSöz gizlidir.",
        reply_markup=get_keyboard()
    )

async def stopgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    user = update.effective_user

    bot_member = await chat.get_member(context.bot.id)
    if bot_member.status != "administrator":
        await update.message.reply_text("❌ Botun admin səlahiyyəti yoxdur.")
        return

    member = await chat.get_member(user.id)
    if member.status not in ["administrator", "creator"] and user.id not in AUTHORIZED_USER_IDS:
        await update.message.reply_text("DƏFOL! ADMİNİN İŞİNƏ QARIŞMA.")
        return

    if not game_active.get(chat_id, False):
        await update.message.reply_text("DƏFOL! OYUN AKTİV DEYİL.")
        return

    game_active[chat_id] = False
    waiting_for_new_master[chat_id] = False
    await update.message.reply_text("DƏFOL! OYUN DAYANDI.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = str(query.message.chat.id)
    user_id = query.from_user.id

    if not game_active.get(chat_id, False):
        if query.message.text != "DƏFOL! OYUN AKTİV DEYİL.":
            await query.edit_message_text("DƏFOL! OYUN AKTİV DEYİL.")
        else:
            await query.answer("DƏFOL! OYUN AKTİV DEYİL.", show_alert=True)
        return

    update_activity(chat_id)

    if query.data == "show":
        if user_id != game_master_id.get(chat_id) and user_id not in AUTHORIZED_USER_IDS:
            await query.answer("DƏFOL! APARICININ İŞİNƏ QARIŞMA.", show_alert=True)
            return
        await query.answer(f"Söz: {current_word.get(chat_id)}", show_alert=True)
        return

    if user_id != game_master_id.get(chat_id):
        await query.answer("DƏFOL! APARICININ İŞİNƏ QARIŞMA.", show_alert=True)
        return

    if query.data == "skip":
        attempts = 0
        while attempts < 10:
            nxt = random.choice(words)
            if nxt not in used_words[chat_id]:
                current_word[chat_id] = nxt
                used_words[chat_id].append(nxt)
                break
            attempts += 1
        else:
            used_words[chat_id] = []
            current_word[chat_id] = random.choice(words)
            used_words[chat_id].append(current_word[chat_id])

        await query.answer(f"Yeni söz: {current_word[chat_id]}", show_alert=True)

    try:
        if query.message.text != "Yeni söz gəldi!":
            await query.edit_message_text("Yeni söz gəldi!", reply_markup=get_keyboard())
        else:
            if query.message.reply_markup != get_keyboard():
                await query.edit_message_reply_markup(reply_markup=get_keyboard())
    except telegram.error.BadRequest as e:
        if "Message is not modified" not in str(e):
            raise
        else:
            await query.edit_message_reply_markup(reply_markup=get_keyboard())
    except Exception as e:
        print(f"Xəta: {e}")

    if query.data == "change":
        waiting_for_new_master[chat_id] = True
        current_word[chat_id] = None
        game_master_id[chat_id] = None
        await query.edit_message_text("Aparıcı Dəfoldu. Yeni aparıcı axtarılır...")
        await context.bot.send_message(chat_id, "Kim aparıcı olmaq istəyir?", reply_markup=get_new_host_button())

# Botun əsas funksiyası
async def main():
    load_scores()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("basla", startgame))
    app.add_handler(CommandHandler("dayandır", stopgame))
    app.add_handler(CallbackQueryHandler(button_handler))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

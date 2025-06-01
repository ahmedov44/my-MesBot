
import json
import os
import random
import time
import nest_asyncio
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)

nest_asyncio.apply()

TOKEN = os.getenv("BOT_TOKEN")
AUTHORIZED_USER_IDS = [5257767076, 7924310880]
SCORE_FILE = "scores.json"
PLAYER_FILE = "players.json"

words = ["Alma", "Armud", "Ərik", "Nar", "Mars", "Futbol", "Şahmat"]

user_stats = {}
player_names = {}

game_active = {}
game_master_id = {}
used_words = {}
current_word = {}
waiting_for_new_master = {}
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

def load_scores():
    global user_stats, player_names
    if os.path.exists(SCORE_FILE):
        with open(SCORE_FILE, "r", encoding="utf-8") as f:
            try:
                raw = json.load(f)
                for uid, data in raw.items():
                    if isinstance(data, dict) and "groups" in data and "total" in data and "name" in data:
                        user_stats[uid] = data
            except json.JSONDecodeError:
                user_stats = {}
    if os.path.exists(PLAYER_FILE):
        with open(PLAYER_FILE, "r", encoding="utf-8") as f:
            try:
                player_names = json.load(f)
            except json.JSONDecodeError:
                player_names = {}

def save_scores():
    with open(SCORE_FILE, "w", encoding="utf-8") as f:
        json.dump(user_stats, f, ensure_ascii=False)
    with open(PLAYER_FILE, "w", encoding="utf-8") as f:
        json.dump(player_names, f, ensure_ascii=False)

def render_bar(score, max_score, length=10):
    filled_length = int(length * score / max_score) if max_score > 0 else 0
    return "▓" * filled_length + "░" * (length - filled_length)

def add_score(chat_id: str, user_id: int, user_name: str, points: int = 1):
    uid = str(user_id)
    if uid not in user_stats:
        user_stats[uid] = {"name": user_name, "groups": {}, "total": 0}
    user_stats[uid]["name"] = user_name
    user_stats[uid]["groups"].setdefault(chat_id, 0)
    user_stats[uid]["groups"][chat_id] += points
    user_stats[uid]["total"] += points

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
        await update.message.reply_text("‼️ Mənə admin səlahiyyəti verin: mesajları silmə və sabitləmə.")
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

async def show_scoreboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    temp = []
    for uid, data in user_stats.items():
        if not isinstance(data, dict):
            continue
        groups = data.get("groups")
        if isinstance(groups, dict) and chat_id in groups:
            name = data.get("name", f"User {uid}")
            score = groups[chat_id]
            temp.append((uid, name, score))

    if not temp:
        await update.message.reply_text("📭 Hələ heç kim xal qazanmayıb.")
        return

    temp.sort(key=lambda x: x[2], reverse=True)
    max_score = temp[0][2]
    text = "🏆 <b>Reytinq:</b>\n\n"
    for i, (uid, name, score) in enumerate(temp, start=1):
        bar = render_bar(score, max_score)
        text += f"{i}. {name} – <b>{score} xal</b>\n{bar}\n\n"
    await update.message.reply_text(text, parse_mode="HTML")

async def show_global_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    temp = []
    for uid, data in user_stats.items():
        if not isinstance(data, dict):
            continue
        total = data.get("total")
        if isinstance(total, int):
            name = data.get("name", f"User {uid}")
            temp.append((uid, name, total))

    if not temp:
        await update.message.reply_text("Ümumi xal məlumatı yoxdur.")
        return

    temp.sort(key=lambda x: x[2], reverse=True)
    max_score = temp[0][2]

    text = "🌍 <b>Ümumi Reytinq:</b>\n\n"
    for i, (uid, name, score) in enumerate(temp[:10], start=1):
        bar = render_bar(score, max_score)
        text += f"{i}. {name} – <b>{score} xal</b>\n{bar}\n\n"
    await update.message.reply_text(text, parse_mode="HTML")

async def main():
    load_scores()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("basla", startgame))
    app.add_handler(CommandHandler("reyting", show_scoreboard))
    app.add_handler(CommandHandler("globalreyting", show_global_top))

    print("Bot işə düşdü...")
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot dayandırıldı.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat.id)

    if not game_active.get(chat_id, False):
        await query.message.reply_text("❌ Oyun aktiv deyil.")
        return

    if query.data == "show":
        word = current_word.get(chat_id, "Söz tapılmadı.")
        await query.message.reply_text(f"🔍 Söz: {word}")

    elif query.data == "skip":
        all_words = set(words)
        used = set(used_words.get(chat_id, []))
        remaining = list(all_words - used)

        if not remaining:
            used_words[chat_id] = []
            remaining = words[:]

        new_word = random.choice(remaining)
        current_word[chat_id] = new_word
        used_words.setdefault(chat_id, []).append(new_word)
        await query.message.reply_text("♻️ Yeni söz təyin edildi.")

    elif query.data == "change":
        game_master_id[chat_id] = None
        waiting_for_new_master[chat_id] = True
        await query.message.reply_text("❌ Aparıcı dəyişdi. Yeni aparıcı gözlənilir...")

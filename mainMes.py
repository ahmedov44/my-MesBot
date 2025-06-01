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
used_words = {}
current_word = {}
waiting_for_new_master = {}
player_names = {}

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

def save_scores():
    with open(SCORE_FILE, "w", encoding="utf-8") as f:
        json.dump(scoreboard, f, ensure_ascii=False)
    with open(PLAYER_FILE, "w", encoding="utf-8") as f:
        json.dump(player_names, f, ensure_ascii=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salam! Oyun botuna xoş gəlmisiniz.\nBaşlamaq üçün /basla yazın.")

async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    user = update.effective_user

    # Qrup yoxlaması
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Bu əmri yalnız qrup daxilində istifadə edə bilərsiniz.")
        return

    # Botun admin olub-olmadığını yoxla
    bot_member = await chat.get_member(context.bot.id)
    if bot_member.status != "administrator":
        await update.message.reply_text("❌ Botun bu qrupda admin səlahiyyəti yoxdur. Zəhmət olmasa bota mesaj silmə və mesaj sabitləmə yetkisi verin.")
        return

    # İstifadəçinin admin olduğunu yoxla
    member = await chat.get_member(user.id)
    if member.status not in ["administrator", "creator"] and user.id != AUTHORIZED_USER_ID:
        await update.message.reply_text("Bu əmri yalnız adminlər verə bilər.")
        return

    if game_active.get(chat_id, False):
        await update.message.reply_text("Oyun artıq aktivdir.")
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

    await update.message.reply_text(
        f"Oyun başladı!\nAparıcı: {user.first_name}\nSöz gizlidir.",
        reply_markup=get_keyboard()
    )

async def stopgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    user = update.effective_user

    # Bot admin deyilsə
    bot_member = await chat.get_member(context.bot.id)
    if bot_member.status != "administrator":
        await update.message.reply_text("❌ Botun admin səlahiyyəti yoxdur. Bot admin olmadıqca bu əmri yerinə yetirə bilməz.")
        return

    # İstifadəçi admin deyilsə
    member = await chat.get_member(user.id)
    if member.status not in ["administrator", "creator"] and user.id != AUTHORIZED_USER_ID:
        await update.message.reply_text("Bu əmri yalnız adminlər verə bilər.")
        return

    if not game_active.get(chat_id, False):
        await update.message.reply_text("Oyun aktiv deyil.")
        return

    game_active[chat_id] = False
    waiting_for_new_master[chat_id] = False
    await update.message.reply_text("Oyun dayandırıldı.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = str(query.message.chat.id)
    user_id = query.from_user.id

    if not game_active.get(chat_id, False):
        await query.edit_message_text("Oyun aktiv deyil.")
        return

    if query.data == "show":
        if user_id != game_master_id.get(chat_id) and user_id != AUTHORIZED_USER_ID:
            await query.answer("Bu sözü yalnız aparıcı görə bilər.", show_alert=True)
            return
        await query.answer(f"Söz: {current_word.get(chat_id)}", show_alert=True)
        return

    if user_id != game_master_id.get(chat_id):
        await query.answer("Bu düyməni yalnız aparıcı istifadə edə bilər.", show_alert=True)
        return

    if query.data == "skip":
        while True:
            nxt = random.choice(words)
            if nxt not in used_words[chat_id]:
                current_word[chat_id] = nxt
                used_words[chat_id].append(nxt)
                break
        await query.edit_message_text("Yeni söz gəldi!", reply_markup=get_keyboard())

    elif query.data == "change":
        waiting_for_new_master[chat_id] = True
        current_word[chat_id] = None
        game_master_id[chat_id] = None
        await query.edit_message_text("Aparıcı Dəfoldu. Yeni aparıcı axtarılır...")

    # Yeni seçim üçün ayrıca aktiv mesaj göndərilir
    await context.bot.send_message(
        chat_id=chat_id,
        text="Kim aparıcı olmaq istəyir? 🎤",
        reply_markup=get_new_host_button()
    

async def handle_become_master(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = str(query.message.chat.id)
    user = query.from_user

    if not waiting_for_new_master.get(chat_id, False):
        await query.answer("Hazırda aparıcıya ehtiyac yoxdur.", show_alert=True)
        return

    game_master_id[chat_id] = user.id
    waiting_for_new_master[chat_id] = False

    while True:
        nxt = random.choice(words)
        if nxt not in used_words[chat_id]:
            current_word[chat_id] = nxt
            used_words[chat_id].append(nxt)
            break

    await query.message.edit_text(
        f"Yeni aparıcı: {user.first_name}\nSöz yeniləndi!",
        reply_markup=get_keyboard()
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = update.effective_user
    text = az_lower(update.message.text.strip())

    if not game_active.get(chat_id) or waiting_for_new_master.get(chat_id):
        return

    if user.id == game_master_id.get(chat_id):
        return

    if text == az_lower(current_word.get(chat_id, "")):
        scoreboard.setdefault(chat_id, {})
        scoreboard[chat_id][user.id] = scoreboard[chat_id].get(user.id, 0) + 1
        player_names[str(user.id)] = user.first_name
        save_scores()
        await update.message.reply_text("DƏFOL! DOĞRUDUR!")

        while True:
            nxt = random.choice(words)
            if nxt not in used_words[chat_id]:
                current_word[chat_id] = nxt
                used_words[chat_id].append(nxt)
                break

        await update.message.reply_text("Yeni söz gəldi!", reply_markup=get_keyboard())

async def show_scoreboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    if chat_id not in scoreboard or not scoreboard[chat_id]:
        await update.message.reply_text("Hələ xal qazanan yoxdur.")
        return

    scores = scoreboard[chat_id]
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    seen_users = set()
    text = "🏆 Reytinq:\n"
    rank = 1

    for user_id, score in sorted_scores:
        uid_str = str(user_id)
        name = player_names.get(uid_str)

        if not name:
            try:
                member = await update.effective_chat.get_member(user_id)
                name = member.user.first_name
                player_names[uid_str] = name
                save_scores()
            except:
                name = f"ID {uid_str}"

        if name in seen_users:
            continue

        seen_users.add(name)
        text += f"{rank}. {name} — {score} xal\n"
        rank += 1

    await update.message.reply_text(text)

async def main():
    load_scores()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("basla", startgame))
    app.add_handler(CommandHandler("dayan", stopgame))
    app.add_handler(CommandHandler("reyting", show_scoreboard))

    app.add_handler(CallbackQueryHandler(handle_become_master, pattern="^become_master$"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Bot işə düşdü...")
    await app.run_polling()

# Replit üçün:
if __name__ == "__main__":
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot dayandırıldı.")


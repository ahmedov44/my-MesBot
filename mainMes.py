import json
import os
import random
import time
import nest_asyncio
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode  # 'ParseMode' buradan idxal olunur
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# Aparıcıya bildiriş göndərmək üçün funksiyanı əlavə edirik
async def send_mention_notification(chat_id, user_id, message, context):
    user_mention = f"[{user_id}](tg://user?id={user_id})"  # Istifadəçiyə tag əlavə etmək
    message = message.replace('!', r'\!')  # '!' simvolunu qaçırırıq
    await context.bot.send_message(chat_id, message.format(user_mention), parse_mode=ParseMode.MARKDOWN_V2, disable_notification=True)

nest_asyncio.apply()

TOKEN = os.getenv("BOT_TOKEN")
AUTHORIZED_USER_IDS = [5257767076, 7924310880]
SCORE_FILE = "scores.json"
PLAYER_FILE = "players.json"

# --- WORDS omitted for brevity in this snippet, assume it's the same ---
words = [ "Rusca", "Ingiliscə", "Fransizca", "Almanca", "Ispanca", "Çincə", "Ərəbcə", "Yaponca", "Hindcə", "Yunanca", "Latınca", "Türkcə", "Azərbaycanca", "Italyanca", "Isveçcə", "Portuqalca", "Farsca", "Gürcücə", "Ukraynaca", "Hollandca", "Norveçcə", "Qazaxca", "Qirğizca", "Özbəkcə", "Türkməncə", "Belarusca", "Serbcə", "Xorvatca", "Slovakca", "Slovencə", "Macarca", "Albanca", "Azərbaycan", "Baki", "Nizami", "Elvin", "Pişik", "Toyota", "Camry", "Samsung", "Riyaziyyat", "Rusca", "Islam", "Facebook", "Kür", "Xəzər", "Sakit", "Asiya", "Mars", "Futbol", "Şahmat", "Manchester City", "Haaland", "Braziliya", "Paris", "Yasamal", "Aysel", "It", "Bmw", "Mustang", "Apple", "Tarix", "Ingiliscə", "Xristianliq", "Instagram", "Araz", "Araliq", "Atlantik", "Avropa", "Yer", "Basketbol", "Dama", "Psg", "Mbappe", "Ronaldo", "Messi", "Ibrahimoviç", "Maradona", "Pele", "Kanada", "Moskva", "Sabunçu", "Kamran", "Qartal", "Mercedes", "A4", "Xiaomi", "Coğrafiya", "Fransizca", "Buddizm", "Twitter", "Nil", "Qara", "Hind", "Afrika", "Venera", "Voleybol", "Suraxani", "Liverpool", "Bellingham", "Türkiyə", "Ankara", "Xətai", "Nigar", "Ayi", "Subaru", "Oneplus", "Fizika", "Almanca", "Hinduizm", "Tiktok", "Amazon", "Baltik", "Şimal Buzlu", "Şimali Amerika", "Yupiter", "Tennis", "Sudoku", "Leipzig", "Yaponiya", "Tokiyo", "Binəqədi", "Tural", "Fil", "Audi", "S-Class", "Google", "Kimya", "Ispanca", "Yəhudilik", "Linkedin", "Volqa", "Hövsan", "Cənub", "Avstraliya", "Merkuri", "Xokkey", "Puzzle", "Atalanta", "Almaniya", "Berlin", "Qaradağ", "Murad", "Canavar", "Lexus", "Huawei", "Biologiya", "Çincə", "Ateizm", "Snapchat", "Dəmirçay", "Egey", "Karib", "Cənubi Amerika", "Saturn", "Yelkən", "Monopoly", "Balaxani", "Pedri", "Italiya", "Roma", "Səbail", "Ləman", "Tülkü", "Ford", "Focus", "Nokia", "Ədəbiyyat", "Ərəbcə", "Bilgəh", "Pinterest", "Tovuzçay", "Qirmizi", "Antarktida", "Uran", "Qilincoynatma", "Domino", "Emma", "Zarina", "Iran", "Tehran", "Gəncə", "Əli", "Aslan", "Kia", "Sportage", "Sony", "Əxlaq", "Koreyaca", "Zərdüştilik", "Wechat", "Əyriçay", "Qizil", "Sarı", "Avstraliya", "Neptun", "Atıcılıq", "Şüvəlan", "Al Nassr", "Mərdəkan", "Gürcüstan", "Tiflis", "Sibir Məryəm", "Timsah", "Chevrolet", "Cruze", "Htc", "Mədəniyyət", "Hindcə", "Bahailik", "Threads", "Göyçay", "Laptevlər", "Meksika Körfəzi", "Asiya", "Pluton", "Güləş", "Vmf", "İnter Miami", "Rodri", "Ülviyyə", "Rusiya", "Kazan", "Lənkəran", "Zaur", "Pələng", "Volkswagen", "Passat", "Realme", "Təsviri Incəsənət", "Yaponca", "Lotos", "Discord", "Ural", "Şimal Dənizi", "Filippin", "Avropa", "Karate", "Uno", "Ukrayna", "Kiyev", "Şəki", "Rəna", "Ayibaliği", "Peugeot", "308", "Oppo", "Musiqi", "Katolik", "Real", "Andaman", "Şərq Dənizi", "Afrika", "Boks", "Tabu", "Rafael", "Həmidə", "Fransa", "Lion", "Qusar", "Fərid", "Dovşan", "Mazda", "Cx-5", "Tecno", "Cəmiyyət", "Yunanca", "Telegram", "Suluq", "Araliq Dəniz", "Amerika", "Makemake", "Cüdo", "Loto", "Yara", "Ingiltərə", "London", "Quba", "Sevinc", "Meşə", "Seat", "Ibiza", "Vivo", "Təsərrüfat", "Latinca", "Buzova", "Vikipediya", "Əmircan", "Hudson", "Sakit Okean", "Avstraliya", "Eris", "Badminton", "Səbail", "Ördək", "Ispaniya", "Madrid", "Zaqatala", "Emil", "Çaqqal", "Honda", "Civic", "Neftçi", "Kimya", "Zirə", "Siqnal", "Fərat", "Dardanel", "Hind Okeani", "Antarktida", "Mars", "Su", "Mafia", "Imperator", "Polşa", "Varşava", "Oğuz", "Günel", "Dəvə", "Land Rover", "Infinix", "Həyat Bilgisi", "Dəniz", "Okean", "Cənubi Amerika", "Mars", "Nərd", "Twister", "Din", "Mn", "Dtx", "Dsx", "Ppx", "Abşeron", "Ağcabədi", "Ağdam", "Ağdaş", "Ağstafa", "Ağsu", "Astara", "Babək", "Balakən", "Beyləqan", "Biləsuvar", "Cəbrayil", "Cəlilabad", "Daşkəsən", "Dəvəçi", "Şabran", "Füzuli", "Gədəbəy", "Goranboy", "Göyçay", "Göygöl", "Hacıqabul", "Ismayilli", "Kəlbəcər", "Kürdəmir", "Qax", "Qazax", "Qəbələ", "Qobustan", "Quba", "Qubadlı", "Qusar", "Laçin", "Lənkəran", "Lerik", "Lənkəran", "Masallı", "Neftçala", "Oğuz", "Ordubad", "Qəbələ", "Saatli", "Sabirabad", "Salyan", "Samux", "Şabran", "Şahbuz", "Şamaxi", "Şəmkir", "Siyəzən", "Sumqayit", "Şuşa", "Tərtər", "Tovuz", "Ucar", "Yardımlı", "Yevlax", "Zaqatala", "Zərdab", "Bakı", "Gəncə", "Mingəçevir", "Şəki", "Qəbələ", "Şirvan", "Yevlax", "Naftalan", "Naxçivan", "Lənkəran", "Ağdaş", "Bərdə", "Beyləqan", "Biləsuvar", "Cəlilabad", "Fizuli", "Göyçay", "Hacıqabul", "Ismayıllı", "Kürdəmir", "Qazax", "Quba", "Qusar", "Salyan", "Saatlı", "Sabirabad", "Şamaxi", "Şəmkir", "Tərtər", "Tovuz", "Ucar", "Xaçmaz", "Xızı", "Xirdalan", "Yevlax", "Zaqatala", "Alma", "Armud", "Ərik", "Gavali", "Albalı", "Gilas", "Şaftali", "Nərgiz", "Nar", "Portağal", "Mandalin", "Limon", "Qreypfrut", "Kivi", "Ananas", "Banan", "Üzüm", "Əncir", "Narinci", "Kələm", "Qarağat", "Moruq", "Qarağac", "Böyürtkən", "Qovun", "Qarğidali", "Qarpız", "Xurma", "Incir", "Qoz", "Findiq", "Sorento", "Yemək", "Içmək", "Doymaq", "Acmaq", "Bişirmək", "Çeynəmək", "Udmaq", "Dadmaq", "Toxluq", "Aclıq", "Susamaq", "Doyurmaq", "Soyutmaq", "Isitmək", "Qizartmaq", "Qaynatmaq", "Qovurmaq", "Doğramaq", "Təmizləmək", "Hazırlamaq", "Yatmaq", "Oyanmaq", "Uzanmaq", "Dincəlmək", "Yorulmaq", "Istirahət Etmək", "Oturmaq", "Durmaq", "Gərnəmək", "Əsnəmək", "Üşümək", "Tərləmək", "Isinmək", "Soyumaq", "Nəfəs Almaq", "Öskürmək", "Asqirmaq", "Gəyirmək", "Hiçqirmaq", "Qusmaq", "Düşünmək", "Fikirləşmək", "Anlamaq", "Başa Düşmək", "Dərk Etmək", "Öyrənmək", "Yadda Saxlamaq", "Unutmaq", "Təxmin Etmək", "Təhlil Etmək", "Müqayisə Etmək", "Qərar Vermək", "Yadda Saxlamaq", "Nəzər Yetirmək", "Müşahidə Etmək", "Sevmək", "Nifrət Etmək", "Qorxmaq", "Utanmaq", "Darıxmaq", "Kədərlənmək", "Sevinmək", "Təəccüblənmək", "Rahatlanmaq", "Narahat Olmaq", "Qəzəblənmək", "Əylənmək", "Həyəcanlanmaq", "Xoşlanmaq", "Sıxılmaq", "Getmək", "Gəlmək", "Qaçmaq", "Yerimək", "Tullanmaq", "Dırmaşmaq", "Sürünmək", "Gəzmək", "Düşmək", "Qalxmaq", "Sürmək", "Daşımaq", "Atmaq", "Tutmaq", "Çəkmək", "İtələmək", "Döymək", "Vurmaq", "Yelləmək", "Fırlatmaq", "Danışmaq", "Demək", "Cavab Vermək", "Soruşmaq", "Susmaq", "Qışqırmaq", "Pıçıldamaq", "Mübahisə Etmək", "Razılaşmaq", "İnandırmaq", "Şikayət Etmək", "Xahiş Etmək", "Xəbər Vermək", "Çağirmaq", "Təklif Etmək", "Durmaq", "Oturmaq", "Uzanmaq", "Yaşamaq", "Olmaq", "Mövcud Olmaq", "Görünmək", "Hiss Olunmaq", "Dəyişmək", "Artmaq", "Azalmaq", "Böyümək", "Kiçilmək", "Donmaq", "Əriyib Getmək", "Kələm", "Qarğıdalı", "Pomidor", "Xiyar", "Badımcan", "Bibər", "Soğan", "Sarımsaq", "Kartof", "Kök", "Turp", "Brokoli", "Gül Kələm", "İspanaq", "Şüyüd", "Cəfəri", "Kahı", "Balqabaq", "Lobya", "Noxud", "Mərci", "Çuğundur", "Vəzəri", "Reyhan", "Nanə", "Mərcimək", "Göy Soğan", "Acı Bibər", "Yaşıl Lobya", "İçərişəhər", "Sahil", "28 May", "Cəfər Cabbarlı", "Nizami", "Elmlər Akademiyasi", "İnşaatçılar", "20 Yanvar", "Memar Əcəmi", "Nəsimi", "Azadliq Prospekti", "Dərnəgül", "Avtovağzal", "8 Noyabr", "Xocəsən", "Gənclik", "Nəriman Nərimanov", "Ulduz", "Koroğlu", "Qara Qarayev", "Neftçilər", "Xalqlar Dostluğu", "Əhmədli", "Həzi Aslanov", "İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana", "Konya", "Gaziantep", "Eskişehir", "Trabzon", "Samsun", "Kayseri", "Mersin", "Şanlıurfa", "Diyarbakır", "Van", "Moskva", "Sankt Peterburq", "Kazan", "Soçi", "Novosibirsk", "Yekaterinburq", "Samara", "Ufa", "Volqoqrad", "Krasnoyarsk", "Vladivostok", "Hyundai", "Porsche", "Vaz", "Lada", "Bently", "Lambo", "Opel", "Elantra", "Accent", "Skoda", "Elcan", "Vüqar", "Söz", "Məşədi", "Bibiheybət", "Bayıl", "Lökbatan", "Bülbülə", "Kürdəxanı", "Ramana", "Novxanı", "Bakıxanov", "Qaraçuxur", "Günəşli", "Temu", "Trendyol", "Ozon", "Oksigen", "Dəmir", "Gümüş", "Çobanyastiği", "Qizilgül", "Internet", "Saat", "Bluetooth", "Airpods", "Acer", "Hp", "Lenovo", "Macbook", "Bayraq", "Gerb", "Himn", "Papaq", "Ayaqqabi", "Kənan", "Diplom", "Vaxt", "Vedrə", "Qazan", "Boşqab", "Qaşıq", "Bulud", "Günəş", "Çəngəl", "Şimşək", "Ruslan", "Hidrometeorologiya" ]

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

def get_medal(score):
    if score >= 100:
        return "🥇"  # Gold medal
    elif score >= 50:
        return "🥈"  # Silver medal
    elif score >= 25:
        return "🥉"  # Bronze medal
    else:
        return "🏅"  # Participation medal

def add_score(chat_id: str, user_id: int, user_name: str, points: int = 1):
    if chat_id not in scoreboard:
        scoreboard[chat_id] = {}
    if user_id not in scoreboard[chat_id]:
        scoreboard[chat_id][user_id] = {"name": user_name, "score": 0}
    
    # Xalı artırırıq
    scoreboard[chat_id][user_id]["score"] += points

    if user_id not in global_scoreboard:
        global_scoreboard[user_id] = {"name": user_name, "score": 0}
    global_scoreboard[user_id]["score"] += points

    # Medal hesablama (xal əsasında)
    medal = get_medal(scoreboard[chat_id][user_id]["score"])

    # Bu, xalı artırıldıqdan sonra medalı qaytarır
    print(f"User {user_name} has earned a {medal}!")
    
    return medal  # Medal qaytarırıq ki, onu istifadə edə bilək

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

    # Aparıcıya bildiriş göndəririk
   await send_mention_notification(chat_id, user.id, "🔔 Yeni aparıcı: {0}!", context)

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

    elif query.data == "skip":
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

    # Yeni söz dəyişdirildikdə aparıcıya bildiriş göndəririk
    await send_mention_notification(chat_id, game_master_id[chat_id], "🔔 Yeni mərhələ başladı! Söz: {0}!", context)

    await query.answer(f"Yeni söz: {current_word[chat_id]}", show_alert=True)
    if query.message.text != "Yeni söz gəldi!":
        await query.edit_message_text("Yeni söz gəldi!", reply_markup=get_keyboard())
    else:
        await query.edit_message_reply_markup(reply_markup=get_keyboard())

    elif query.data == "change":
        waiting_for_new_master[chat_id] = True
        current_word[chat_id] = None
        game_master_id[chat_id] = None
        await query.edit_message_text("Aparıcı Dəfoldu. Yeni aparıcı axtarılır...")
        await context.bot.send_message(chat_id, "Kim aparıcı olmaq istəyir?", reply_markup=get_new_host_button())

async def handle_become_master(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = str(query.message.chat.id)
    user = query.from_user

    if not waiting_for_new_master.get(chat_id, False):
        await query.answer("Hazırda aparıcıya ehtiyac yoxdur.", show_alert=True)
        return

    game_master_id[chat_id] = user.id
    waiting_for_new_master[chat_id] = False

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

    update_activity(chat_id)

    await query.message.edit_text(
        f"Yeni aparıcı: {user.first_name}\nSöz yeniləndi!",
        reply_markup=get_keyboard()
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = str(update.effective_chat.id)
    user = update.effective_user
    text = az_lower(update.message.text.strip())

    if not game_active.get(chat_id) or waiting_for_new_master.get(chat_id):
        return

    if user.id == game_master_id.get(chat_id):
        return

    if text == az_lower(current_word.get(chat_id, "")):
        add_score(chat_id, user.id, user.first_name)
        player_names[str(user.id)] = user.first_name
        save_scores()

        await update.message.reply_text("DƏFOL! SÖZ DOĞRUDUR!")

        # Yeni söz tapıldığında, aparıcıya bildiriş göndəririk
        await send_mention_notification(chat_id, game_master_id[chat_id], "🔔 Yeni söz tapıldı! {0}!", context)

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

        update_activity(chat_id)
        await update.message.reply_text("Yeni söz gəldi!", reply_markup=get_keyboard())

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

        update_activity(chat_id)
        await update.message.reply_text("Yeni söz gəldi!", reply_markup=get_keyboard())

async def show_scoreboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    if chat_id not in scoreboard or not scoreboard[chat_id]:
        await update.message.reply_text("📭 Hələ heç kim xal qazanmayıb.")
        return

    scores = scoreboard[chat_id]
    # Handle both old format (int) and new format (dict)
    score_list = []
    for user_id, data in scores.items():
        if isinstance(data, dict):
            name = data["name"]
            score = data["score"]
        else:
            # Old format - data is just the score as integer
            score = data
            name = player_names.get(str(user_id), f"User {user_id}")
        score_list.append((user_id, {"name": name, "score": score}))
    
    sorted_scores = sorted(score_list, key=lambda x: x[1]["score"], reverse=True)
    max_score = sorted_scores[0][1]["score"] if sorted_scores else 1

    text = "🏆 <b>Reytinq:</b>\n\n"
    for i, (user_id, data) in enumerate(sorted_scores, start=1):
        name = data["name"]
        score = data["score"]
        bar = render_bar(score, max_score)
        text += f"{i}. {name} – <b>{score} xal</b>\n{bar}\n\n"

    await update.message.reply_text(text, parse_mode="HTML")

async def show_global_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not global_scoreboard:
        await update.message.reply_text("Ümumi xal məlumatı yoxdur.")
        return

    sorted_scores = sorted(global_scoreboard.items(), key=lambda x: x[1]["score"], reverse=True)
    max_score = sorted_scores[0][1]["score"]

    text = "🌍 <b>Ümumi Reytinq:</b>\n\n"
    for i, (user_id, data) in enumerate(sorted_scores[:10], start=1):
        name = data["name"]
        score = data["score"]
        bar = render_bar(score, max_score)
        text += f"{i}. {name} – <b>{score} xal</b>\n{bar}\n\n"

    await update.message.reply_text(text, parse_mode="HTML")

async def inactivity_watcher(app):
    while True:
        now = time.time()
        for chat_id in list(game_active.keys()):
            if game_active.get(chat_id, False):
                last = last_activity.get(chat_id, 0)
                if now - last > 180:
                    game_active[chat_id] = False
                    waiting_for_new_master[chat_id] = False
                    try:
                        await app.bot.send_message(int(chat_id), "⚠️ 3 dəqiqə aktivlik olmadığından oyun avtomatik dayandırıldı.")
                    except Exception as e:
                        print(f"Mesaj göndərilərkən xəta: {e}")
        await asyncio.sleep(30)

async def main():
    load_scores()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("basla", startgame))
    app.add_handler(CommandHandler("dayan", stopgame))
    app.add_handler(CommandHandler("reyting", show_scoreboard))
    app.add_handler(CommandHandler("globalreyting", show_global_top))
    app.add_handler(CallbackQueryHandler(handle_become_master, pattern="^become_master$"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    asyncio.create_task(inactivity_watcher(app))
    print("Bot işə düşdü...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
from telegram import ParseMode

# Function to send a message with a mention (tag)
async def send_mention_notification(chat_id, user_id, message, context):
    user_mention = f"[{user_id}](tg://user?id={user_id})"  # Create a tag for the user
    await context.bot.send_message(chat_id, message.format(user_mention), parse_mode=ParseMode.MARKDOWN_V2, disable_notification=True)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = str(update.effective_chat.id)
    user = update.effective_user
    text = az_lower(update.message.text.strip())

    if not game_active.get(chat_id) or waiting_for_new_master.get(chat_id):
        return

    if user.id == game_master_id.get(chat_id):
        return

    if text == az_lower(current_word.get(chat_id, "")):
        # Xal əlavə edir
        medal = add_score(chat_id, user.id, user.first_name)

        # İstifadəçiyə xal və medal bildiririk
        await update.message.reply_text(f"🎉 {user.first_name} {medal} Xal: {scoreboard[chat_id][user.id]['score']}")

        # Yeni söz tapıldı
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

        update_activity(chat_id)
        await update.message.reply_text("Yeni söz gəldi!", reply_markup=get_keyboard())

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

        update_activity(chat_id)
        await update.message.reply_text("Yeni söz gəldi!", reply_markup=get_keyboard())

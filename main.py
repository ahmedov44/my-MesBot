import json
import os
import random
import time
import asyncio
import nest_asyncio
import re
import unicodedata
from datetime import datetime
import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, ContextTypes, filters)
from telegram import ChatPermissions
import sqlite3
import io
import requests
from PIL import Image
import pytesseract
from flask import Flask, request, redirect, session, url_for
from threading import Thread
import logging

# Flask xəbərdarlıqlarını susdur
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Replit'də daim işləməsi üçün Flask serveri
flask_app = Flask('')
flask_app.secret_key = 'meshedi_super_secret'  # Şifrə qoruması üçün lazım

# Active chats for broadcast functionality
active_chats = set()


@flask_app.route('/')
def home():
    return "MəşBot işləyir!"


@flask_app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == "meshedi123":
            session['logged_in'] = True
            return redirect(url_for('broadcast'))
        return "Şifrə yalnışdır."
    return """
        <form method='post'>
            <h2>Admin Giriş</h2>
            <input type='password' name='password' placeholder='Şifrə'><br>
            <input type='submit' value='Giriş'>
        </form>
    """


@flask_app.route("/broadcast", methods=["GET", "POST"])
def broadcast():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == "POST":
        message = request.form.get("message")
        if not message:
            return "Mesaj boş ola bilməz!"
        asyncio.run(send_broadcast_to_chats(message))
        return "Mesaj uğurla göndərildi!"
    return """
        <form method='post'>
            <h2>Qruplara Mesaj Göndər</h2>
            <textarea name='message' rows='5' cols='40'></textarea><br>
            <input type='submit' value='Göndər'>
        </form>
    """


async def send_broadcast_to_chats(message):
    from telegram import Bot
    bot = Bot(TOKEN)
    success_count = 0
    failed_count = 0

    for chat_id in active_chats:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            success_count += 1
            print(f"Mesaj göndərildi: {chat_id}")
        except Exception as e:
            failed_count += 1
            print(f"Xəta ({chat_id}): {e}")

    print(
        f"Broadcast tamamlandı: {success_count} uğurlu, {failed_count} uğursuz"
    )


def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()


TOKEN = os.getenv("TOKEN")
MESHEDI_USER_ID = 5257767076
AUTHORIZED_USER_IDS = []
DB_NAME = "bot.db"

# Azərbaycan vaxtı üçün timezone
AZ_TZ = pytz.timezone("Asia/Baku")

# Səlahiyyətli şəxslər və adları (mention üçün)
AUTHORIZED_USERS = {
    5257767076: "Məşədi",
    # Buraya digər user_id: "Ad" əlavə edə bilərsən
}

# Son mesaj vaxtlarını saxlayan lüğət
last_message_times = {}  # user_id: datetime

# Video sticker protection - add allowed video sticker IDs here
ALLOWED_VIDEO_STICKER_IDS = [
]  # Add specific file_unique_id values here if needed
BLOCKED_STICKERS_FILE = "blocked_stickers.json"
BLOCKED_STICKER_IDS = []  # Initialize the list


def load_blocked_stickers():
    global BLOCKED_STICKER_IDS
    try:
        with open(BLOCKED_STICKERS_FILE, "r", encoding="utf-8") as f:
            BLOCKED_STICKER_IDS.clear()
            BLOCKED_STICKER_IDS.extend(json.load(f))
    except FileNotFoundError:
        BLOCKED_STICKER_IDS.clear()
    # Add specific blocked stickers
    BLOCKED_STICKER_IDS.extend(SPECIFIC_BLOCKED_STICKERS)


def save_blocked_stickers():
    with open(BLOCKED_STICKERS_FILE, "w", encoding="utf-8") as f:
        json.dump(BLOCKED_STICKER_IDS, f, ensure_ascii=False, indent=2)


# Add specific blocked sticker IDs from the enhanced version
SPECIFIC_BLOCKED_STICKERS = [
    "AgADr3MAAhexGEk", "AgADIV0AAqecCUo", "AgADg2sAAjwjGEk", "AgADHngAAkPsGEk", "AgADQRAAAq6qsVM", "AgADJgwAAlUdaVM", "AgAD73cAAvbL6Eg"
]

# Sticker icazələri və fərdi mesajlar
STICKER_RULES = {
    # Məsələn:
    # "AgADLnQAAizFGEk": {
    #     "allowed": [6894645405, 5257767076],
    #     "message": "bu stikeri yalnız Zarina göndərə bilər."
    # }
}

all_players = []

words = [
    "Anara", "Ayaz", "Bahar", "Babək", "Cəmilə", "Cavid", "Çiçək", "Çingiz",
    "Dilbər", "Daşqın", "Elnarə", "Elçin", "Əsmər", "Əli", "Fidan", "Fərid",
    "Gülnar", "Güntay", "Ruslan", "Qiyas", "Hicran", "Hikmət", "Xədicə",
    "Xəyyam", "İlhamə", "İsfəndiyar", "İlahə", "İlqar", "Ceyhun", "Caləddin",
    "Kamalə", "Kamran", "Qəmzə", "Qənimət", "Ləman", "Lətif", "Mələk",
    "Mənsur", "Nigar", "Natiq", "Oksana", "Oqtay", "Ömür", "Ömər", "Pəri",
    "Pünhan", "Rəna", "Rəşad", "Sevinc", "Samir", "Şəbnəm", "Şahin", "Təranə",
    "Tunar", "Ulduz", "Ülvi", "Ülviyyə", "Üzeyir", "Vəfa", "Yeganə",
    "Yusif", "Zümrüd", "Zaur", "Elcan", "Famil", "Həmidə", "Taleh", "Gül",
    "Nazlı", "Ismayıl", "Ayla", "Aliyə", "Cahandar", "Nurlan", "Leyla",
    "Içərişəhər", "Sahil", "28 May", "Cəfər Cabbarlı", "Nizami",
    "Elmlər Akademiyası", "İnşaatçılar", "20 Yanvar", "Memar Əcəmi", "Nəsimi",
    "Azadlıq Prospekti", "Dərnəgül", "Avtovağzal", "8 Noyabr", "Xocəsən",
    "Gənclik", "Nəriman Nərimanov", "Ulduz", "Koroğlu", "Qara Qarayev",
    "Neftçilər", "Xalqlar Dostluğu", "Əhmədli", "Həzi Aslanov", "istanbul",
    "Ankara", "İzmir", "Bursa", "Antalya", "Adana", "Konya", "Gaziantep",
    "Eskişehir", "Trabzon", "Samsun", "Kayseri", "Mersin", "Şanlıurfa",
    "Diyarbakır", "Van Moskva", "Sankt peterburq", "Kazan", "Soçi",
    "Novosibirsk", "Yekaterinburq", "Samara", "Ufa", "Volqoqrad",
    "Krasnoyarsk", "Vladivostok", "Kütlə", "Sürət", "Qüvvə", "Enerji",
    "İmpuls", "Sürətlənmə", "Cazibə", "Təzyiq", "İstilik", "İş", "Potensial",
    "Kinetik", "Dalğa", "Tezlik", "Amplitud", "Müqavimət", "Gərginlik",
    "Elektrik", "Cərəyan", "Kvant", "Foton", "Atom", "Nüvə", "Spektr", "Optik",
    "Rentgen", "Radiasiya", "Plazma", "Müşahidə", "Pntropiya", "Nəzəriyyə",
    "Eksperiment", "Nyuton", "Qaliley", "Eynşteyn", "Faraday", "Bor", "Fermi",
    "Durak", "Tesla", "Heisenberg", "Paul", "Kelvin", "Curie", "Lomonosov",
    "Atom", "Molekul", "Element", "Birləşmə", "Qarışıq", "İon", "Kation",
    "Anion", "Oksidləşmə", "Reduksiya", "Valent", "Turşu", "Əsas", "Duz", "Ph",
    "Katalizator", "Reaksiya", "Enerji Dəyişməsi", "İzotop", "Periodik Sistem",
    "Elektron", "Proton", "Neytron", "Kimyəvi", "Kovalent", "İon", "Metal",
    "Elektrolit", "Həllolma", "Moll", "Avogadro", "Termokimya", "Orqanik",
    "Qeyri orqanik", "Polimer", "Karbonhidrogen", "Alkan", "Alken", "Alkin",
    "Aromatik", "Sabunlaşma", "Neft", "Yanacaq", "Mendeleyev", "Dalton",
    "Küri", "Thomson", "Hüceyrə", "Nüvə", "Sitoplazma", "Membran", "Xromosom",
    "Gen", "DNT", "RNT", "Mitoxondri", "Ribosom", "Endoplazmatik Şəbəkə",
    "Lizosom", "Toxuma", "Orqan", "Sistem", "Orqanizm", "Fotosintez",
    "Tənəffüs", "Metabolizm", "Ferment", "Hormon", "Mutasiya", "İrsiyyət",
    "Adaptasiya", "Seleksiya", "Təkamül", "Klonlama", "Mitoz", "Meyoz",
    "Replikasiya", "Transkripsiya", "Translyasiya", "Protein", "Amin Turşusu",
    "Simbioz", "Parazit", "Virus", "Bakteriya", "Göbələk", "Yosun", "Bitki",
    "Heyvan", "İnsan", "İmmunitet", "Homeostaz", "Ekosistem", "Biosfer",
    "Populyasiya", "Növ", "Genetik Müxtəliflik", "Darvin", "Mendel", "Paster",
    "Hekkel", "Tarix", "Mənbə", "Salnamə", "Xronologiya", "Arxeologiya",
    "Etnoqrafiya", "Mədəniyyət", "Dövlət", "İmperiya", "Respublika",
    "Monarxiya", "Feodalizm", "Kapitalizm", "Sosializm", "İnqilab", "İslahat",
    "İstilalar", "Müharibə", "Sülh", "Müqavilə", "Sülalə", "Əhali", "Tayfa",
    "Qəbilə", "Köç", "Kolonizasiya", "Sənayeləşmə", "Azadlıq Hərəkatı",
    "genosid", "Beynəlxalq", "Soyqırım", "Deportasiya", "Cəbhə", "İttifaq",
    "Müxalifət", "İqtisadiyyat", "Diplomatiya", "Sərkərdə", "Fateh", "Lider",
    "Qanun", "İdarəetmə", "Vergi", "İşğal", "Müqavimət", "Mühacirət",
    "Müstəqillik", "Mərkəzləşmə", "Millət", "Din", "İdeologiya", "Herodot",
    "Ziya Bünyadov", "Fəridə", "Sara", "Litosfer", "Hidrosfer", "Atmosfer",
    "Biosfer", "Relyef", "Dağ", "Çökəklik", "Vulkan", "Zəlzələ", "Tektonik",
    "İqlim", "Temperatur", "Yağıntı", "Külək", "Rütubət", "Landşaft", "Okean",
    "Dəniz", "Çay", "Göl", "Buzlaq", "Ekvator", "Meridian", "Paralel",
    "Koordinat", "Xəritə", "Miqyas", "İzoxət", "Topoqrafiya", "Gps",
    "Urbanizasiya", "Miqrasiya", "Regionlaşdırma", "Təbii Ehtiyatlar",
    "Antropogen", "Eratosten", "Strabon", "Mövzu", "İdeya", "Süjet",
    "Konflikt", "Ekspozisiya", "Düyün", "Kulminasiya", "Kompozisiya", "Obraz",
    "Xarakter", "Qəhrəman", "Lirika", "Epika", "Drama", "Qoşma", "Gəraylı",
    "Bayatı", "Elegiya", "Poema", "Hekayə", "Povest", "Roman", "Komediya",
    "Faciə", "Dram", "Epitet", "Metafora", "Metonimiya", "Təşbeh", "Hiperbola",
    "Litota", "Simvol", "İroniya", "Sarkazm", "Personifikasiya", "Assonans",
    "Təkrir", "Poetika", "Janr", "Üslub", "Klassisizm", "Romantizm", "Realizm",
    "Naturalizm", "Modernizm", "Postmodernizm", "Alqoritm", "Proqram",
    "Proqramlaşdırma", "Kod", "Dəyişən", "Sabit", "Massiv", "Siyahı",
    "Funksiya", "Metod", "Obyekt", "Sinif", "Modul", "Fayl", "Verilənlər",
    "Məlumat", "İnformasiya", "Bit", "Bayt", "Kilobayt", "Megabayt",
    "Gigabayt", "Terabayt", "Interfeys", "Sürücü", "Bufer", "Yükləmə",
    "Yaddaş", "Operativ Yaddaş", "Daimi Yaddaş", "Prosessor", "Nüvə",
    "Ana Plata", "Şəbəkə", "İP", "URL", "Server", "Müştəri", "Bulud",
    "Şifrələmə", "Təhlükəsizlik", "Antivirus", "Ehtiyat Nüsxə",
    "Arxivləşdirmə", "Proqram Təminatı", "Tətbiq", "Terminal", "Komanda",
    "Skript", "Avtomatlaşdırma", "Emulyator", "Kompüter", "Animasiya",
    "Render", "Piksel", "Çözünürlük", "Rəqəmsal", "Analoq", "Sensor",
    "Robotexnika", "Süni İntellekt", "HTML", "Javascript", "Python", "Java",
    "SQL", "Fonem", "Grafem", "Sait", "Samit", "Söz", "Kök", "Şəkilçi",
    "Leksika", "Semantika", "Frazeologiya", "Etimologiya", "Morfologiya",
    "Sintaksis", "Fonetika", "Orfoqrafiya", "Cümlə", "Xəbər", "Mübtəda",
    "Tamamlıq", "Zərflik", "Təyin", "Qrammatika", "Nitq Hissələri", "İsim",
    "Sifət", "Say", "Əvəzlik", "Feil", "Zərf", "Qoşma", "Bağlayıcı", "Nida",
    "Zaman", "Təsrif", "Qeyri təsrif", "Fellik", "Məsdər", "Çoxalma", "Azalma",
    "Məcaz", "Birləşmə", "Dialekt", "Şivə", "Üslub", "Bədii", "Elmi", "Rəsmi",
    "Publisistik", "Danışıq", "Normativlik", "Danışıq", "Ədəbi", "Ünsür",
    "Quruluş", "Yazı", "Danışıq", "Ünsiyyət", "Kommunikasiya", "Dilçilik",
    "Nitq", "Ədəd", "Tam", "Kəsr", "Onluq", "Müsbət", "Mənfi", "Sıfır",
    "Tənlik", "Bərabərlik", "Bərabərsizlik", "Cəbr", "Funksiya", "Dəyişən",
    "Sabit", "Əmsal", "Kvadrat", "Kök", "Həll", "Toplama", "Çıxma", "Vurma",
    "Bölmə", "Faktor", "Sadə", "Mürəkkəb", "Ardıcıllıq", "Cəmi", "Hasil",
    "Həndəsə", "Nöqtə", "Düzxətt", "Şüa", "Kəsik", "Bucaq", "Üçbucaq",
    "Dördbucaq", "Düzbucaqlı", "Paraleloqram", "Romb", "Trapesiya", "Dairə",
    "Radius", "Diametr", "Perimetr", "Sahə", "Həcm", "Oxlar", "Qrafik",
    "Funksiya", "Kvadrat Funksiya", "Məntiq", "Düstur", "Harmonik",
    "Arifmetik", "Statistik", "Ehtimal", "Kombinatorika", "Matris",
    "Determinant", "Vektor", "Koordinat", "Inteqrasiya", "Törəmə", "Limit",
    "Analiz", "Diferensial", "Kompleks", "Induksiya", "Teorem", "Sübut",
    "merkuri", "Venera", "Yer", "Mars", "Yupiter", "Saturn", "Uran", "Neptun",
    "Pluton", "Günəş", "Planet", "Peyk", "Ay", "Ulduz", "Qalaktika", "Orbit",
    "Asteroid", "Kometa", "Meteorit", "Qara Dəlik", "Supernova",
    "Qalaktikalararası", "Kosmos", "Kainat", "Qravitasiya", "Işıqili",
    "Teleskop", "kosmonavt", "Astronom", "Astrofizika", "Qalaktik", "Planetar",
    "Pulsar", "Kvazar", "Teleskop", "Kəmiyyət", "Ölçü", "Məkân", "Zaman",
    "Teleskopiya", "Fotometriya", "Spektroskopiya", "Sabunçu", "Biləcəri",
    "Zabrat", "Goradil", "Ramana", "Maştağa", "Qaraçuxur", "Hövsan", "Türkan",
    "Buzovna", "Şağan", "Balaxanı", "Ramana", "Əmircan", "Mərdəkan", "Qala",
    "Nardaran", "Badamdar", "Bayıl", "İçərişəhər", "Fəvvarələr Meydanı",
    "Qız Qalası", "Binəqədi", "Nizami", "Nərimanov", "Yasamal", "Sabunçu",
    "Xətai", "Suraxanı", "Qaradağ", "Səbail", "Pirallahı", "Nəsimi", "Xəzər",
    "Abşeron", "Ağcabədi", "Ağdam", "Ağdaş", "Ağstafa", "Ağsu", "Astara",
    "Balakən", "Bərdə", "Beyləqan", "Biləsuvar", "Cəbrayıl", "Cəlilabad",
    "Daşkəsən", "Füzuli", "Gədəbəy", "Goranboy", "Göyçay", "Göygöl",
    "Hacıqabul", "İmişli", "İsmayıllı", "Kəlbəcər", "Kürdəmir", "Qax", "Qazax",
    "Qəbələ", "Qobustan", "Quba", "Qubadlı", "Qusar", "Laçın", "Lənkəran",
    "Lerik", "Masallı", "Neftçala", "Oğuz", "Ordubad", "Saatlı", "Sabirabad",
    "Salyan", "Samux", "Şabran", "Şəki", "Şamaxı", "Şəmkir", "Şərur",
    "Siyəzən", "Sumqayıt", "Şuşa", "Tərtər", "Tovuz", "Ucar", "Xaçmaz",
    "Xankəndi", "Xızı", "Xocalı", "Xocavənd", "Yardımlı", "Yevlax", "Zaqatala",
    "Zəngilan", "Zərdab", "Bakı", "Gəncə", "Sumqayıt", "Mingəçevir",
    "Naftalan", "Şəki", "Şirvan", "Lənkəran", "Yevlax", "Türkcə",
    "Azərbaycanca", "İngiliscə", "Rusca", "Fransızca", "Almanca", "Ərəbcə",
    "Farsca", "Çincə", "Yaponca", "İtalyanca", "İslam", "Xristianlıq",
    "Yəhudilik", "Buddizm", "Hinduizm", "Konfutsiçilik", "Taoizm", "Şintoizm",
    "Deist", "Ateist", "Müsəlman", "Ateizm", "Aqnostisizm", "Realmadrid",
    "Barselona", "Mançester Yunayted", "Mançester Siti", "Liverpul", "Çelsi",
    "Arsenal", "Bavariya", "Borussiya Dortmund", "PSG", "Yuventus", "İnter",
    "Milan", "Napoli", "Atletiko Madrid", "Ayaks", "Benfika", "Porto",
    "Sportinq", "Roma", "Sevilya", "leypsiq", "Tottenhem", "Marsel",
    "Qalatasaray", "Fənərbaxça", "Beşiktaş", "Zenit", "Şaxtyor Donetsk",
    "Qarabağ", "Neftçi", "Sabah", "Səbail", "Sumqayıt", "Zirə", "Turan Tovuz",
    "Kəpəz", "Şamaxı", "Araz", "Lionel Messi", "Cristiano Ronaldo", "Neymar",
    "Kilian Mbappe", "Haaland", "Kevin", "Luka Modriç", "Levandovski",
    "Harri Keyn", " Salah", "Lionel", "Messi", "Ronaldo", "Neymar", "Mbappe",
    "Modriç", "Robert", "Paris", "London", "New York", "Tokio", "Pekin",
    "Roma", "Madrid", "Berlin", "Moskva", "Dubay", "İstanbul", "Los Anceles",
    "Sinqapur", "Sidney", "Seul", "Toronto", "Şanxay", "Barselona", "Çikaqo",
    "Honq Konq", "Amsterdam", "Milan", "Vyana", "Kopenhagen", "Rio de janeyro",
    "Buenos Ayres", "Vaşinqton", "Bangkok", "İstanbul", "Toyota", "Corolla",
    "Camry", "Prius", "Honda", "Civic", "Accord", "Nissan", "Altima", "Sentra",
    "Patrol", "Mitsubishi", "Lancer", "Mazda", "Pajero", "Hyundai", "Elantra",
    "Sonata", "Tucson", "Santafe", "Kia", "Rio", "Sportage", "Cerato",
    "Sorento", "Ford", "Focus", "Fusion", "Explorer", "Mustang", "Chevrolet",
    "Malibu", "Cruze", "Tahoe", "Spark", "BMW", "Mercedes benz", "Audi",
    "Lexus", "Infiniti", "Porsche", "Landrover", "Jaguar", "Subaru", "Tesla",
    "Volvo", "Fiat", "Jeep", "Dodge", "Ram", "Cadillac", "Acura", "Alfaromeo",
    "Mercedes", "Maserati", "Bentley", "Rolls royce", "Bugatti", "Ferrari",
    "Lamborghini", "Mclaren", "Astonmartin", "Elantra", "Sonata", "Yemək",
    "Içmək", "Doymaq", "Acmaq", "Bişirmək", "Çeynəmək", "Udmaq", "Dadmaq",
    "Toxluq", "Aclıq", "Susamaq", "Doyurmaq", "Soyutmaq", "İsitmək",
    "Qızartmaq", "Qaynatmaq", "Qovurmaq", "doğramaq", "Təmizləmək",
    "Hazırlamaq", "Yatmaq", "Oyanmaq", "Uzanmaq", "Dincəlmək", "Yorulmaq",
    "Istirahət", "Oturmaq", "Durmaq", "Gərnəmək", "Əsnəmək", "Üşümək",
    "Tərləmək", "İsinmək", "Soyumaq", "Nəfəs", "Öskürmək", "Asqırmaq",
    "Gəyirmək", "Hıçqırmaq", "Qusmaq", "Düşünmək", "Fikirləşmək", "Anlamaq",
    "Başa Düşmək", "Dərk etmək", "Öyrənmək", "Yadda saxlamaq", "Unutmaq",
    "Təxmin etmək", "Təhlil etmək", "Müqayisə etmək", "Qərar vermək",
    "Yaddaşda saxlamaq", "Nəzər yetirmək", "Müşahidə etmək", "Sevmək",
    "Nifrət etmək", "Qorxmaq", "Utanmaq", "Darıxmaq", "Kədərlənmək",
    "Sevinmək", "Təəccüblənmək", "Rahatlanmaq", "Narahat olmaq", "Qəzəblənmək",
    "Əylənmək", "Həyəcanlanmaq", "Xoşlanmaq", "Sıxılmaq", "Getmək", "Gəlmək",
    "Qaçmaq", "Yerimək", "Tullanmaq", "Dırmaşmaq", "Sürünmək", "Gəzmək",
    "Düşmək", "Qalxmaq", "Sürmək", "Daşımaq", "Atmaq", "Tutmaq", "Çəkmək",
    "İtələmək", "Döymək", "Vurmaq", "Yelləmək", "Fırlatmaq", "Danışmaq",
    "Demək", "Cavab Vermək", "Soruşmaq", "Susmaq", "Qışqırmaq", "Pıçıldamaq",
    "Mübahisə Etmək", "Razılaşmaq", "İnandırmaq", "Şikayət Etmək",
    "Xahiş etmək", "Xəbər vermək", "Çağırmaq", "Təklif etmək", "Durmaq",
    "Oturmaq", "Uzanmaq", "Yaşamaq", "Olmaq", "alma", "Armud", "Banan",
    "Portağal", "Mandarin", "Limon", "Nar", "Üzüm", "Ərik", "Gilas", "Çiyələk",
    "Ananas", "Kivi", "Manqo", "Narıngi", "Qarpız", "Heyva", "Şaftalı",
    "Qovun", "Avokado", "Pomidor", "Xiyar", "Kartof", "Yerkökü", "Soğan",
    "Sarımsaq", "Kələm", "Karnabahar", "Brokoli", "İspanaq", "Lobya", "Noxud",
    "Mərcimək", "Badımcan", "Bibər", "Balqabaq", "Turp", "Kahı", "Cəfəri",
    "Şüyüd", "Reyhan", "Nanə", "Şirin", "Turş", "Məşədi", "Hidrometeorologiya",
    "Novruz", "Ramazan Bayramı", "Qurban Bayramı", "Yeniil", "Respublika Günü",
    "Qələbə", "Halloween", "Milad", "Şaxta", "Pasxa", "Valentin", "Yanvar",
    "Fevral", "Mart", "Aprel", "May", "İyun", "İyul", "Avqust", "Sentyabr",
    "Oktyabr", "Noyabr", "Dekabr", "Qoç", "Buğa", "Əkizlər", "Xərçəng", "Şir",
    "Qız", "Tərəzi", "Əqrəb", "Oxatan", "Oğlaq", "Dolça", "Balıqlar", "Nike",
    "Adidas", "Puma", "VMF", "BMW", "Apple", "Samsung", "Huawei", "Xiaomi",
    "Oppo", "Vivo", "Realme", "Nokia", "Sony", "OnePlus", "Motorola", "ZTE",
    "Tecno", "Infinix", "Lenovo", "Asus", "Honor", "Meizu", "Alcatel",
    "Google", "HTC", "Dell", "HP", "Lenovo", "Asus", "Acer", "Apple", "Razer",
    "Samsung", "Microsoft", "Toshiba", "Fujitsu", "LG", "Huawei", "Gigabyte",
    "Sony", "Panasonic", "Azərbaycan", "Türkiyə", "Rusiya", "Almaniya",
    "Fransa", "İtaliya", "İspaniya", "Portuqaliya", "Polşa", "Ukrayna",
    "Belarus", "Qazaxıstan", "Çin", "Yaponiya", "Cənubi Koreya",
    "Şimali Koreya", "Hindistan", "Pakistan", "İran", "İraq", "Suriya",
    "Misir", "Liviya", "Tunis", "Əlcəzair", "Mərakeş", "ABŞ", "Kanada",
    "Meksika", "Braziliya", "Argentina", "Çili", "Kolumbiya", "Avstraliya",
    "Yeni Zelandiya", "İngiltərə", "İsveç", "Norveç", "Finlandiya",
    "Danimarka", "Niderland", "Belçika", "İsveçrə", "Avstriya", "Çexiya",
    "Slovakiya", "Macarıstan", "Serbiya", "Gürcüstan", "İsrail", "Qartal",
    "Bayquş", "Qaranquş", "Kəklik", "Göyərçin", "Tutuquşu", "Sazağan", "Qarğa",
    "Sərçə", "Turna", "Durna", "Leylək", "Ququş", "Alabaxta", "Aslan",
    "Pələng", "Fil", "Zürafə", "Canavar", "Ayı", "Çaqqal", "Tülkü", "Dovşan",
    "At", "İnək", "Qoyun", "Keçi", "Siçan", "Delfin", "PA", "Milliməclis",
    "Məhkəmə", "Ali Məhkəmə", "DİN", "XİN", "Müdafiə", "Təhsil Nazirliyi",
    "Ədliyyə", "DTX", "ETSN", "Yarasa", "Yaşma", "XTQ", "BDU", "Aztu", "ATU",
    "ADU", "ADA", "Universitet", "GDU", "NDU", "Harvard University",
    "Oxford", "Stanford", "MIT", "Cambridge", "Yale", "Toronto", "Etna",
    "Vezuv", "Krakatau", "Fuji", "Kilimanjaro", "Elbrus", "Ararat", "Everest",
    "Himalay", "Alplar", "Andes", "Kafkas", "Ural", "Facebook", "İnstagram",
    "Twitter", "TikTok", "Snapchat", "YouTube", "WhatsApp", "Telegram",
    "LinkedIn", "Reddit", "Pinterest", "Viber", "Discord", "WeChat", "Tumblr",
    "Clubhouse", "Threads", "BeReal", "VK", "Messenger", "Ördək", "Vaxt",
    "Zaman", "Kapital", "Paşa Bank", "ABB", "Unibank", "Bank Respublika",
    "XalqBank", "Access Bank", "Ziraat ", "YapıKredi", "Rabitəbank", "ARB",
    "Xəzər", "Space", "Az", "Lider", "ATV", "İctimai ", "TRT", "CNNTürk",
    "Televizor", "Michael Jackson", "Beyonce", "Adele", "Shakira", "Rihanna",
    "Justin Bieber", "TaylorSwift", "Ed Sheeran", "Lady Gaga", "Bank",
    "Friends", "Game of Thrones", "Breaking Bad", "Televiziya", "Kanal",
    "Diplom", "Simpsons", "Milyonçu"
]

# Dict-per-chat storage
teams = {}  # chat_id -> {"red": [], "blue": []}
team_scores = {}  # chat_id -> {"red": 0, "blue": 0}

game_active = {}
game_master_id = {}
scoreboard = {}
used_words = {}
current_word = {}
waiting_for_new_master = {}
player_names = {}
last_activity = {}
game_mode = {}
pinned_message_id = {}
pending_team_choice = {}
initial_scores = {}

ZALGO_MARKERS = [
    '\u0300', '\u0301', '\u0302', '\u0303', '\u0304', '\u0305', '\u0306',
    '\u0307', '\u0308', '\u0309', '\u030A', '\u030B', '\u030C', '\u030D',
    '\u030E', '\u030F', '\u0310', '\u0311', '\u0312', '\u0313', '\u0314',
    '\u0315', '\u0316', '\u0317', '\u0318', '\u0319', '\u031A', '\u031B',
    '\u031C', '\u031D', '\u031E', '\u031F', '\u0320', '\u0321', '\u0322',
    '\u0323', '\u0324', '\u0325', '\u0326', '\u0327', '\u0328', '\u0329',
    '\u032A', '\u032B', '\u032C', '\u032D', '\u032E', '\u032F', '\u0330',
    '\u0331', '\u0332', '\u0333', '\u0334', '\u0335', '\u0336', '\u0337',
    '\u0338', '\u0339', '\u033A', '\u033B', '\u033C', '\u033D', '\u033E',
    '\u033F'
]

# === Ultra-level Homoglyph map (enhanced with more variants) ===
HOMOGLYPHS = {
    "ᴏ": "o",
    "ԁ": "d",
    "ḍ": "d",
    "ɗ": "d",
    "ď": "d",
    "𝖉": "d",
    "𝒅": "d",
    "𝓭": "d",
    "𝑑": "d",
    "ᴅ": "d",
    "𝐝": "d",
    "ə": "e",
    "Ə": "e",
    "ɛ": "e",
    "є": "e",
    "ε": "e",
    "е": "e",
    "3": "e",
    "𝒆": "e",
    "𝖊": "e",
    "𝓮": "e",
    "ᴇ": "e",
    "𝐞": "e",
    "ë": "e",
    "ê": "e",
    "è": "e",
    "é": "e",
    "ｅ": "e",
    "ℯ": "e",
    "ƒ": "f",
    "ғ": "f",
    "ꞙ": "f",
    "ꝼ": "f",
    "ʄ": "f",
    "𝒇": "f",
    "𝖋": "f",
    "𝓯": "f",
    "ꜰ": "f",
    "𝐟": "f",
    "ö": "o",
    "о": "o",
    "σ": "o",
    "ɵ": "o",
    "ò": "o",
    "ó": "o",
    "ọ": "o",
    "ơ": "o",
    "º": "o",
    "°": "o",
    "○": "o",
    "●": "o",
    "◎": "o",
    "ο": "o",
    "ø": "o",
    "𝖔": "o",
    "𝒐": "o",
    "𝓸": "o",
    "🅾": "o",
    "ⓞ": "o",
    "ⅼ": "l",
    "|": "l",
    "ı": "l",
    "ӏ": "l",
    "1": "l",
    "!": "l",
    "¡": "l",
    "׀": "l",
    "l̵": "l",
    "𝖑": "l",
    "𝓵": "l",
    "𝒍": "l",
    "🄻": "l",
    "Ⓛ": "l",
    "ʟ": "l",
    "𝐥": "l",
    "🅳": "d",
    "🅵": "f",
    "🅾": "o",
    "🅻": "l",
    "Д": "d",
    "д": "d",
    "е": "e",
    "Е": "e",
    "ф": "f",
    "Ф": "f",
    "о": "o",
    "О": "o",
    "л": "l",
    "Л": "l"
}

ZERO_WIDTH = ["​", "‌", "‍", "⁠", "﻿"]
INVISIBLE = ["­", "͏", "؜", "ᅟ", "ᅠ"]


def normalize_word(word: str) -> str:
    replacements = {
        "ı": "i",
        "İ": "i",
        "I": "i",
        "ß": "s",
        "Ə": "e",
        "ə": "e",
        "Ö": "o",
        "ö": "o",
        "Ü": "u",
        "ü": "u",
        "Ğ": "g",
        "ğ": "g",
        "Ç": "c",
        "ç": "c",
        "Ş": "s",
        "ş": "s"
    }
    word = word.lower()
    word = ''.join(replacements.get(c, c) for c in word)
    word = unicodedata.normalize("NFKD", word)
    return ''.join([c for c in word if not unicodedata.combining(c)])


def normalize_word(word: str) -> str:
    """Enhanced word normalization for Azerbaijani"""
    replacements = {
        "ı": "i",
        "İ": "i",
        "I": "i",
        "ß": "s",
        "Ə": "e",
        "ə": "e",
        "Ö": "o",
        "ö": "o",
        "Ü": "u",
        "ü": "u",
        "Ğ": "g",
        "ğ": "g",
        "Ç": "c",
        "ç": "c",
        "Ş": "s",
        "ş": "s"
    }
    word = word.lower()
    word = ''.join(replacements.get(c, c) for c in word)
    word = unicodedata.normalize("NFKD", word)
    return ''.join([c for c in word if not unicodedata.combining(c)])


def clean_text(text):
    """Enhanced text normalization with better line break handling"""
    text = text.replace("\n", "").replace("\r",
                                          "").replace("\x0b",
                                                      "").replace("\x0c", "")
    text = normalize_word(text)
    text = unicodedata.normalize("NFKC", text)
    for z in ZERO_WIDTH + INVISIBLE:
        text = text.replace(z, "")
    for mark in ZALGO_MARKERS:
        text = text.replace(mark, "")
    for bad, good in HOMOGLYPHS.items():
        text = text.replace(bad, good)
    text = re.sub(r'[^\w\s]', '', text)
    return text


def az_lower(text):
    """Azerbaijani-specific lowercase conversion"""
    replacements = {
        "İ": "i",
        "I": "ı",
        "Ş": "ş",
        "Ğ": "ğ",
        "Ü": "ü",
        "Ö": "ö",
        "Ç": "ç",
        "Ə": "ə"
    }
    for big, small in replacements.items():
        text = text.replace(big, small)
    return text.casefold()


# Enhanced defol detection with comprehensive homoglyph support
def normalize_defol_text(text):
    """Enhanced text normalization for better defol detection"""
    replacements = {
        "а": "a",
        "А": "A",  # Kiril
        "е": "e",
        "Е": "E",
        "о": "o",
        "О": "O",
        "р": "p",
        "Р": "P",
        "с": "c",
        "С": "C",
        "у": "y",
        "У": "Y",
        "х": "x",
        "Х": "X",
        "ə": "e",
        "Ə": "e",
        "ş": "sh",
        "Ş": "sh",
        "ı": "i",
        "I": "i",
        "ö": "o",
        "Ö": "o",
        "ü": "u",
        "Ü": "u",
        "ğ": "g",
        "Ğ": "g",
        "ç": "ch",
        "Ç": "ch",
        "İ": "i",
        "ß": "ss",
        "1": "i",
        "!": "i",
        "|": "i"
    }

    text = text.lower()
    for k, v in replacements.items():
        text = text.replace(k, v)

    # Remove diacritics and special characters
    text = unicodedata.normalize("NFKD", text)
    text = ''.join([c for c in text if not unicodedata.combining(c)])
    text = re.sub(r'[^\w\s]', '', text)
    return text


def contains_defol(text):
    """Check if text contains defol variations using enhanced regex"""
    normalized = normalize_defol_text(text)
    pattern = r"@?d[əe3еė][fph]+[o0öо]{1,3}l{1,5}"
    if re.search(pattern, normalized):
        return True

    defol_variants = [
        "defol",
        "dəfol",
        "defoI",
        "dəfo1",
        "deƒol",
        "dёfol",
        "dеfоl",
        "defoldum",
        "defoldu",
        "defolun",
    ]
    return any(variant in normalized for variant in defol_variants)


def enhanced_defol_detection(text):
    """Enhanced defol detection with improved text cleaning"""
    text = text.replace("\n", "").replace("\r",
                                          "").replace("\x0b",
                                                      "").replace("\x0c", "")
    return contains_defol(text)


# Enhanced bad words list for permanent muting
BAD_WORDS = {
    "cındır", "siktir", "dalbayob", "amına", "oruspu", "sik", "göt", "qəhbə",
    "gijdillaq", "cindir", "sikim", "qancıq", "fuck", "fucker", "qoduğ",
    "amciq", "amq", "vajina", "sikər", "sikdir", "amk", "gotun", "gotverən",
    "gotune", "daşaq", "qehbe", "orosp", "qanciq", "Pidaraz", "daşşaq",
    "bicbala", "fahişə", "qandon", "blət", "soxum", "dıllaq", "dıllağ", "pidr",
    "cindir", "penis", "daşşaq", "dassaq", "pox", "qehbe", "sikim", "sikərəm",
    "sikilmişəm", "sikməm", "sikməliyəm", "sikməliyik", "sikməliyik",
    "sikməliyəm", "sikməliyik", "sikmək", "sikməliyəm", "sikməliyik",
    "sikməliyəm", "sikməliyik", "sikməliyəm", "sikməliyik", "sikərəm",
    "sikəcəm"
}

# Enhanced exceptions list
BAD_WORD_EXCEPTIONS = {
    "sikayet", "sikinti", "saxlamışıq", "salmaq", "götür", "şikayət", "daşın",
    "daşımışıq", "cıdır", "götrük", "götrəng", "götrülmək", "dalbadal",
    "verməmişik", "vermək", "vermədim", "verməliyik", "verməyik", "verməmişəm",
    "vermeyik", "vermeyib", "vermeyibik", "gelmisik", "gelmishik", "gelmiwik",
    "gəlmişik", "görüşecik", "görüşəcəyik", "vermisik", "vermishik",
    "vermishem", "verməmişik", "vermeyik", "sozvermisik", "sozvermishem",
    "sozvermisem", "mənlikdi", "menlikdi", "şotu", "shotu", "shoto", "manlidi",
    "sakit", "pisik", "pişik", "pisiyik", "pishik", "pisiq", "pisi", "pisiyəm",
    "demisik", "demisiz", "demisem", "kesik", "kesıq", "kəsik", "kəsiq",
    "kəsık", "leksika", "lexika", "ləksika", "ləxika", "meksika", "meksiko",
    "mexsika", "mexsiko", "məksika", "məksiko", "məxika", "məxiko"
}


def normalize_bad_word_text(text):
    """Enhanced text normalization for bad word detection"""
    replacements = {
        "а": "a",
        "е": "e",
        "о": "o",
        "р": "p",
        "с": "c",
        "у": "y",
        "х": "x",
        "ə": "e",
        "Ə": "e",
        "ş": "sh",
        "Ş": "sh",
        "ı": "i",
        "I": "i",
        "ö": "o",
        "Ö": "o",
        "ü": "u",
        "Ü": "u",
        "ğ": "g",
        "Ğ": "g",
        "ç": "ch",
        "Ç": "ch",
        "İ": "i",
        "ß": "ss",
        "1": "i",
        "!": "i",
        "|": "i"
    }

    text = text.lower()
    for k, v in replacements.items():
        text = text.replace(k, v)

    text = unicodedata.normalize("NFKD", text)
    text = ''.join([c for c in text if not unicodedata.combining(c)])
    text = re.sub(r'[^\w\s]', '', text)
    return text


def contains_bad_word(text: str) -> bool:
    """Enhanced bad word detection using word-based matching"""
    normalized = normalize_bad_word_text(text)
    words = normalized.split()

    for word in words:
        for bad in BAD_WORDS:
            if word.startswith(bad) and word not in BAD_WORD_EXCEPTIONS:
                return True
    return False


def is_forbidden(text):
    """Enhanced defol detection with comprehensive filtering"""
    return enhanced_defol_detection(text)


def get_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Növbəti söz♻️", callback_data="skip")],
         [InlineKeyboardButton("Sözü göstər🔎", callback_data="show")],
         [InlineKeyboardButton("Fikrimi dəyişdim❌", callback_data="change")]])


def get_team_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔴 Qırmızı", callback_data="join_red")],
         [InlineKeyboardButton("🔵 Mavi", callback_data="join_blue")],
         [
             InlineKeyboardButton("Oyunu başlat",
                                  callback_data="start_team_game")
         ]])


def get_new_host_button():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Aparıcı olmaq istəyirəm! 🎤",
                             callback_data="become_master")
    ]])


def get_late_joiner_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔴 Qırmızı", callback_data="join_red_from_choice")
    ], [InlineKeyboardButton("🔵 Mavi",
                             callback_data="join_blue_from_choice")]])


def init_db():
    """Initialize SQLite database for the Telegram bot."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            user_id INTEGER,
            chat_id TEXT,
            name TEXT,
            score INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, chat_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            name TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized successfully!")


def load_scores():
    """Load scores and player names from SQLite database into memory."""
    global scoreboard, player_names
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Load scores
    c.execute("SELECT user_id, chat_id, name, score FROM scores")
    for user_id, chat_id, name, score in c.fetchall():
        if chat_id not in scoreboard:
            scoreboard[chat_id] = {}
        scoreboard[chat_id][str(user_id)] = {"name": name, "score": score}

    # Load player names
    c.execute("SELECT user_id, name FROM players")
    for user_id, name in c.fetchall():
        player_names[str(user_id)] = name

    conn.close()


def render_bar(score, max_score, length=10):
    filled_length = int(length * score / max_score) if max_score > 0 else 0
    return "▓" * filled_length + "░" * (length - filled_length)


def add_score(chat_id: str, user_id: int, user_name: str, points: int = 1):
    if chat_id not in scoreboard:
        scoreboard[chat_id] = {}
    if str(user_id) not in scoreboard[chat_id]:
        scoreboard[chat_id][str(user_id)] = {"name": user_name, "score": 0}
    scoreboard[chat_id][str(user_id)]["score"] += points


def add_team_score(user_id, points=1, chat_id=None, user_name=None):
    if chat_id is None or chat_id not in teams or chat_id not in team_scores:
        return

    if user_id in teams[chat_id]["red"]:
        team_scores[chat_id]["red"] += points
    elif user_id in teams[chat_id]["blue"]:
        team_scores[chat_id]["blue"] += points

    if chat_id and user_name:
        add_score(chat_id, user_id, user_name, points)


def save_scores():
    """Save scores and player names to SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Save scores
    for chat_id, users in scoreboard.items():
        for user_id, data in users.items():
            c.execute(
                """
                INSERT INTO scores (user_id, chat_id, name, score)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, chat_id) DO UPDATE SET
                score = EXCLUDED.score,
                name = EXCLUDED.name
            """, (int(user_id), chat_id, data["name"], data["score"]))

    # Save player names
    for user_id, name in player_names.items():
        c.execute(
            """
            INSERT INTO players (user_id, name)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            name = EXCLUDED.name
        """, (int(user_id), name))

    conn.commit()
    conn.close()


def update_activity(chat_id):
    last_activity[chat_id] = time.time()


def reset_scores(chat_id):
    if chat_id in scoreboard:
        for user_id in scoreboard[chat_id]:
            scoreboard[chat_id][user_id]["score"] = 0


def reset_game_state(chat_id):
    game_active[chat_id] = False
    game_master_id.pop(chat_id, None)
    used_words.pop(chat_id, None)
    current_word.pop(chat_id, None)
    waiting_for_new_master[chat_id] = False
    game_mode.pop(chat_id, None)
    pinned_message_id.pop(chat_id, None)
    last_activity.pop(chat_id, None)
    initial_scores.pop(chat_id, None)

    # Əgər komandalar varsa, onların user_id-lərini yığ
    all_ids = []
    if chat_id in teams:
        all_ids.extend(teams[chat_id].get("red", []))
        all_ids.extend(teams[chat_id].get("blue", []))

    # Ad siyahısından təmizlə
    for user_id in all_ids:
        player_names.pop(str(user_id), None)

    teams.pop(chat_id, None)
    team_scores.pop(chat_id, None)

    # pending_team_choice təmizlə (yalnız bu qrupa aid olanlar)
    keys_to_remove = [
        uid for uid, d in pending_team_choice.items()
        if d.get('chat_id') == chat_id
    ]
    for uid in keys_to_remove:
        pending_team_choice.pop(uid, None)


async def update_team_selection_message(context, chat_id, message_id):
    # Initialize teams if not exists
    if chat_id not in teams:
        teams[chat_id] = {"red": [], "blue": []}

    # Qırmızı komanda üzvlərinin adları
    red_names = []
    for player_id in teams[chat_id]["red"]:
        name = player_names.get(str(player_id), f"User {player_id}")
        red_names.append(f"- {name}")

    # Mavi komanda üzvlərinin adları
    blue_names = []
    for player_id in teams[chat_id]["blue"]:
        name = player_names.get(str(player_id), f"User {player_id}")
        blue_names.append(f"- {name}")

    # Mesaj mətni
    red_list = "\n".join(red_names) if red_names else "-"
    blue_list = "\n".join(blue_names) if blue_names else "-"

    team_text = f"Komandadan birini seçin:\n\n🔴 Qırmızı:\n{red_list}\n\n🔵 Mavi:\n{blue_list}"

    # Mesajı edit et
    await context.bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=team_text,
                                        reply_markup=get_team_keyboard())


async def safe_reply(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     text: str, **kwargs):
    """Safely reply to a message, handling potential deletion errors."""
    try:
        await update.message.reply_text(text, **kwargs)
    except Exception as e:
        print(f"Reply failed (message likely deleted): {e}")


# ================= ACTIVITY TRACKING =====================

ACTIVITY_FILE = "admin_activity.json"


# Load activity data from file at startup
def load_activity_data():
    global last_message_times
    if os.path.exists(ACTIVITY_FILE):
        with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                last_message_times = {
                    int(k): datetime.fromisoformat(v)
                    for k, v in data.items()
                }
            except Exception as e:
                print(f"Xəta: admin activity faylı yüklənmədi — {e}")
                last_message_times = {}
    else:
        last_message_times = {}


# Save current activity data to file
def save_activity_data():
    with open(ACTIVITY_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                str(k): v.isoformat()
                for k, v in last_message_times.items()
            },
            f,
            ensure_ascii=False,
            indent=2)


# Track admin activity when message is received
async def track_admin_activity(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if chat.type not in ["group", "supergroup"]:
        return

    member = await chat.get_member(user.id)
    if member.status in ["administrator", "creator"] and not user.is_bot:
        last_message_times[user.id] = datetime.now(AZ_TZ)
        save_activity_data()


# Show admin activity via /aktivlik command with sorting by activity level (Məşədi only)
async def show_admin_activity(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != MESHEDI_USER_ID:
        await update.message.reply_text("DƏFOL! Məşədinin işinə qarışma.")
        return

    chat = update.effective_chat
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Bu komanda yalnız qrupda işləyir.")
        return

    now = datetime.now(AZ_TZ)
    activity_list = []

    admins = await chat.get_administrators()

    for admin in admins:
        user = admin.user
        if user.is_bot or user.id == MESHEDI_USER_ID:
            continue

        mention = f"[{user.full_name}](tg://user?id={user.id})"
        if user.id in last_message_times:
            diff = int(
                (now - last_message_times[user.id]).total_seconds() / 60)
            if diff <= 30:
                status = "🟢"
            elif diff <= 60:
                status = "🟡"
            else:
                status = "🔴"
            activity_list.append((diff, mention, status))
        else:
            activity_list.append((9999, mention, "🔴"))  # aktivlik yoxdur

    activity_list.sort(
        key=lambda x: x[0])  # Sort by time difference (ascending)

    group_name = chat.title or "Qrup"
    emoji = "🔥"
    header = f"*{group_name}* — 🔥 üçün Admin aktivliyi\n\n"

    text_lines = []
    last_status = None
    for i, (diff, mention, status) in enumerate(activity_list, start=1):
        if diff != 9999:
            if diff >= 60:
                hours = diff // 60
                minutes = diff % 60
                time_str = f"{hours} saat" + (f" {minutes} dəqiqə"
                                              if minutes > 0 else "")
            else:
                time_str = f"{diff} dəqiqə"

            if last_status and last_status != status:
                text_lines.append("")

            text_lines.append(f"{i}. {mention} — {time_str} {status}")
            last_status = status
        else:
            if last_status != "🔴":
                text_lines.append("")
            text_lines.append(f"{i}. {mention} — aktivlik yoxdur {status}")
            last_status = "🔴"

    group_name = chat.title or "Qrup"
    emoji = "🔥"
    header = f"*{group_name}* — {emoji} üçün Admin aktivliyi\n\n"
    text = header + "\n".join(text_lines)
    await update.message.reply_text(text, parse_mode="Markdown")


# =========================================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "➕ Botu Qrupa Əlavə Et",
                url="https://t.me/MesBotCRO_bot?startgroup=true")
        ]])
        await update.message.reply_text(
            "🎉 Xoş gəlmisən! Bu, MəşBot — rəqabət və komanda oyun dünyasıdır..😊\n\n🗣 Başlamaq üçün:   \n1. Məni qrupa əlavə et   \n2. Admin icazəsi ver (📌 pin, 🧹 sil)  \n3. /basla yaz və oyuna başla!",
            reply_markup=keyboard)
    else:
        await update.message.reply_text(
            "Salam! Oyun botuna xoş gəlmisiniz.\nBaşlamaq üçün /basla yazın.")


async def is_admin_or_authorized(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    member = await chat.get_member(user.id)
    return member.status in ["administrator", "creator"
                             ] or user.id in AUTHORIZED_USER_IDS


async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    user = update.effective_user

    # Add chat to active chats for broadcast functionality
    active_chats.add(chat.id)

    if chat.type not in ["group", "supergroup"]:
        await safe_reply(
            update, context,
            "Bu əmri yalnız qrup daxilində istifadə edə bilərsiniz.")
        return

    bot_member = await chat.get_member(context.bot.id)
    if bot_member.status != "administrator":
        await update.message.reply_text(
            "‼️ Salam! Mən MəşBotam (Söz Tapmaq oyunu), botu aktivləşdirmək üçün zəhmət olmasa mesajları silmə və mesajları sabitləmək səlahiyyətini verin."
        )
        return

    if not await is_admin_or_authorized(update, context):
        await safe_reply(update, context, "DƏFOL! ADMİNİN İŞİNƏ QARIŞMA.")
        return

    if game_active.get(chat_id, False):
        await safe_reply(update, context, "DƏFOL! OYUN AKTİVDİR.")
        return

    # Oyun rejimi seçim keyboard
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🧠 Söz tapmaq", callback_data="word_game")
    ], [InlineKeyboardButton("🔴🔵 Komanda yarışı", callback_data="team_mode")]])
    await update.message.reply_text("Oyun başlamaq üçün seçim edin:",
                                    reply_markup=keyboard)
    game_master_id[chat_id] = user.id


async def stopgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)

    if not await is_admin_or_authorized(update, context):
        await safe_reply(update, context, "DƏFOL! ADMİNİN İŞİNƏ QARIŞMA.")
        return

    if not game_active.get(chat_id, False):
        await safe_reply(update, context, "DƏFOL! OYUN AKTİV DEYİL.")
        return

    if game_mode.get(chat_id) == "team":
        if chat_id not in team_scores:
            team_scores[chat_id] = {"red": 0, "blue": 0}

        red_total = team_scores[chat_id]["red"]
        blue_total = team_scores[chat_id]["blue"]

        if red_total > blue_total:
            winner = "🔴 Qırmızı Komanda"
            difference = red_total - blue_total
        elif blue_total > red_total:
            winner = "🔵 Mavi Komanda"
            difference = blue_total - red_total
        else:
            winner = "Heç bir komanda (bərabər)"
            difference = 0

        team_results = [("🔴 Qırmızı Komanda", red_total),
                        ("🔵 Mavi Komanda", blue_total)]
        team_results.sort(key=lambda x: x[1], reverse=True)

        result_message = "🏁 Oyun bitdi!\n\n"
        for team_name, score in team_results:
            result_message += f"{team_name}: {score} xal\n"
        result_message += "\n"

        result_message += f"🏆 Qalib: {winner}\n"
        if difference > 0:
            result_message += f"📊 Xal fərqi: {difference} xal\n\n"

        def get_session_score(chat_id, user_id):
            initial = initial_scores.get(chat_id, {}).get(str(user_id), 0)
            current = scoreboard.get(chat_id, {}).get(str(user_id),
                                                      {}).get("score", 0)
            return current - initial

        def get_top_session_players(chat_id):
            players = []
            if chat_id not in teams:
                return players
            for team_color in ["red", "blue"]:
                for uid in teams[chat_id][team_color]:
                    delta = get_session_score(chat_id, uid)
                    if delta > 0:
                        name = player_names.get(str(uid), f"User {uid}")
                        players.append((name, delta, uid,
                                        '🔴' if team_color == "red" else '🔵'))
            return sorted(players, key=lambda x: x[1], reverse=True)

        top_players = get_top_session_players(chat_id)

        if top_players:
            result_message += "🌟 Ən yaxşı oyunçular:\n"
            medals = ['🥇', '🥈']
            for i, (name, score, pid,
                    team_emoji) in enumerate(top_players[:2]):
                medal = medals[i] if i < len(medals) else ''
                result_message += f"{i+1}. {medal} <a href='tg://user?id={pid}'>{name}</a> – {score} xal {team_emoji}\n"

        await update.message.reply_text(result_message, parse_mode="HTML")

        save_scores()
        reset_game_state(chat_id)

    else:
        if chat_id in scoreboard and scoreboard[chat_id]:
            scores = scoreboard[chat_id]
            score_list = []
            for user_id, data in scores.items():
                if isinstance(data, dict):
                    name = data["name"]
                    score = data["score"]
                else:
                    score = data
                    name = player_names.get(str(user_id), f"User {user_id}")
                score_list.append((user_id, {"name": name, "score": score}))

            if score_list:
                sorted_scores = sorted(score_list,
                                       key=lambda x: x[1]["score"],
                                       reverse=True)
                result_text = "🏁 Oyun başa çatdı!\n\n🏆 Son nəticələr:\n\n"
                medals = ['🥇', '🥈', '🥉']
                top_score = sorted_scores[0][1]["score"] if sorted_scores else 0

                for i, (user_id, data) in enumerate(sorted_scores, start=1):
                    name = data["name"]
                    score = data["score"]
                    medal = medals[i - 1] if i <= len(medals) else ''
                    crown = ' 👑' if score == top_score and i == 1 else ''
                    result_text += f"{i}. {medal} {name} – {score} xal{crown}\n"
                await safe_reply(update, context, result_text)
            else:
                await safe_reply(
                    update, context,
                    "🏁 Oyun başa çatdı!\n\nHeç kim xal qazanmadı.")
        else:
            await safe_reply(update, context,
                             "🏁 Oyun başa çatdı!\n\nHeç kim xal qazanmadı.")

        save_scores()
        reset_game_state(chat_id)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = str(query.message.chat.id)
    user_id = query.from_user.id

    # Initialize teams and scores if not exists
    if chat_id not in teams:
        teams[chat_id] = {"red": [], "blue": []}
    if chat_id not in team_scores:
        team_scores[chat_id] = {"red": 0, "blue": 0}

    # Aparıcı olmayan istifadəçilər üçün ümumi düymə yoxlanışı
    allowed_for_all = [
        "join_red", "join_blue", "join_red_from_choice",
        "join_blue_from_choice", "become_master"
    ]
    if query.data not in allowed_for_all:
        if user_id != game_master_id.get(chat_id) and user_id != MESHEDI_USER_ID:
            await query.answer("DƏFOL! APARICIYA QARIŞMA.", show_alert=True)
            return

    # "word_game" və "team_mode" butonlarını yalnız game master seçilə biləcək şəxs klikləyə bilər
    if query.data in ["word_game", "team_mode"]:
        if chat_id in game_active and game_active[chat_id]:
            await query.answer("DƏFOL! OYUN ARTIQ BAŞLAMIŞDIR.",
                               show_alert=True)
            return
        if user_id != game_master_id.get(chat_id):
            await query.answer("DƏFOL! BU DÜYMƏYƏ YALNIZ APARICI BASA BİLƏR.",
                               show_alert=True)
            return

    if query.data == "team_mode":
        game_mode[chat_id] = "team"
        await query.answer()

        # Əvvəlki pinlənmiş mesajı sil
        if chat_id in pinned_message_id:
            try:
                await context.bot.unpin_chat_message(
                    chat_id=chat_id, message_id=pinned_message_id[chat_id])
                await context.bot.delete_message(
                    chat_id=chat_id, message_id=pinned_message_id[chat_id])
                del pinned_message_id[chat_id]
            except:
                pass

        # Komanda siyahılarını hazırla
        red_names = [
            f"- {player_names.get(str(pid), f'User {pid}')}"
            for pid in teams[chat_id]["red"]
        ]
        blue_names = [
            f"- {player_names.get(str(pid), f'User {pid}')}"
            for pid in teams[chat_id]["blue"]
        ]
        red_list = "\n".join(red_names) if red_names else "-"
        blue_list = "\n".join(blue_names) if blue_names else "-"
        team_text = f"Komandadan birini seçin:\n\n🔴 Qırmızı:\n{red_list}\n\n🔵 Mavi:\n{blue_list}"

        # Yeni mesaj göndər və pinlə (bildirişlə)
        sent_msg = await context.bot.send_message(
            chat_id=chat_id, text=team_text, reply_markup=get_team_keyboard())
        await context.bot.pin_chat_message(chat_id=chat_id,
                                           message_id=sent_msg.message_id,
                                           disable_notification=False)
        pinned_message_id[chat_id] = sent_msg.message_id

        # Köhnə callback mesajını sil
        await query.message.delete()
        return

    elif query.data == "word_game":
        game_mode[chat_id] = "normal"
        game_active[chat_id] = True
        waiting_for_new_master[chat_id] = False
        used_words.setdefault(chat_id, [])
        scoreboard.setdefault(chat_id, {})
        game_master_id[chat_id] = user_id

        while True:
            nxt = random.choice(words)
            if nxt not in used_words[chat_id]:
                current_word[chat_id] = nxt
                used_words[chat_id].append(nxt)
                break

        # Oyun başlayanda mövcud skorları qeyd et
        initial_scores[chat_id] = {}
        for user_id in scoreboard.get(chat_id, {}):
            initial_scores[chat_id][user_id] = scoreboard[chat_id][
                user_id].get("score", 0)

        update_activity(chat_id)

        await query.answer()
        await query.edit_message_text(
            f"Oyun başladı!\nAparıcı: <a href=\"tg://user?id={query.from_user.id}\">{query.from_user.full_name}</a>",
            reply_markup=get_keyboard(),
            parse_mode="HTML")
        return

    elif query.data == "join_red":
        if user_id == game_master_id.get(chat_id):
            await query.answer("‼️Aparıcı komandaya qoşula bilməz.❌",
                               show_alert=True)
            return
        if user_id not in teams[chat_id]["red"] and user_id not in teams[
                chat_id]["blue"]:
            teams[chat_id]["red"].append(user_id)
            player_names[str(user_id)] = query.from_user.first_name
            await query.answer("🔴 Qırmızı komandaya qoşuldun!",
                               show_alert=True)
            await update_team_selection_message(context, chat_id,
                                                query.message.message_id)
        else:
            await query.answer("Sən artıq komandadasan!", show_alert=True)
        return

    elif query.data == "join_blue":
        if user_id == game_master_id.get(chat_id):
            await query.answer("‼️Aparıcı komandaya qoşula bilməz.❌",
                               show_alert=True)
            return
        if user_id not in teams[chat_id]["red"] and user_id not in teams[
                chat_id]["blue"]:
            teams[chat_id]["blue"].append(user_id)
            player_names[str(user_id)] = query.from_user.first_name
            await query.answer("🔵 Mavi komandaya qoşuldun!", show_alert=True)
            await update_team_selection_message(context, chat_id,
                                                query.message.message_id)
        else:
            await query.answer("Sən artıq komandadasan!", show_alert=True)
        return

    elif query.data == "start_team_game":
        # Check if there's already a game master and if current user is not the master
        if user_id != game_master_id.get(chat_id):
            await query.answer("DƏFOL! BU DÜYMƏYƏ YALNIZ APARICI BASA BİLƏR.",
                               show_alert=True)
            return

        if len(teams[chat_id]["red"]) == 0 or len(teams[chat_id]["blue"]) == 0:
            await query.answer(
                "‼️Hər iki komandada ən azı bir oyunçu olmalıdır!",
                show_alert=True)
            return

        game_active[chat_id] = True
        waiting_for_new_master[chat_id] = False
        used_words.setdefault(chat_id, [])
        game_master_id[chat_id] = user_id

        while True:
            nxt = random.choice(words)
            if nxt not in used_words[chat_id]:
                current_word[chat_id] = nxt
                used_words[chat_id].append(nxt)
                break

        # Oyun başlayanda mövcud skorları qeyd et
        initial_scores[chat_id] = {}
        for user_id in scoreboard.get(chat_id, {}):
            initial_scores[chat_id][user_id] = scoreboard[chat_id][
                user_id].get("score", 0)

        update_activity(chat_id)

        # Pinlənmiş komanda siyahısını sil
        if chat_id in pinned_message_id:
            try:
                await context.bot.unpin_chat_message(
                    chat_id=chat_id, message_id=pinned_message_id[chat_id])
                await context.bot.delete_message(
                    chat_id=chat_id, message_id=pinned_message_id[chat_id])
                del pinned_message_id[chat_id]
            except:
                pass

        team_red = ", ".join([
            str(player_names.get(str(player), "Ad Tapılmadı"))
            for player in teams[chat_id]["red"]
        ])
        team_blue = ", ".join([
            str(player_names.get(str(player), "Ad Tapılmadı"))
            for player in teams[chat_id]["blue"]
        ])

        # Yeni oyun mesajı göndər
        await context.bot.send_message(
            chat_id=chat_id,
            text=
            f"Oyun başladı!\nAparıcı: <a href=\"tg://user?id={query.from_user.id}\">{query.from_user.full_name}</a>",
            reply_markup=get_keyboard(),
            parse_mode="HTML")
        return

    elif query.data == "join_red_from_choice":
        if user_id == game_master_id.get(chat_id):
            await query.answer("‼️Aparıcı komandaya qoşula bilməz.",
                               show_alert=True)
            return
        # Check if user is already in a team
        if user_id in teams[chat_id]["red"] or user_id in teams[chat_id][
                "blue"]:
            await query.answer("Sən artıq komandadasan!", show_alert=True)
            return

        # Safely get points with default value
        pending_data = pending_team_choice.get(user_id, {})
        points = pending_data.get('points', 0)
        if points > 0:
            teams[chat_id]["red"].append(user_id)
            team_scores[chat_id]["red"] += points
            player_names[str(user_id)] = query.from_user.first_name

            # Add to individual scoreboard too
            add_score(chat_id, user_id, query.from_user.first_name, points)
            save_scores()

            # Remove from pending choices
            pending_team_choice.pop(user_id, None)
            await query.answer(
                f"🔴 Qırmızı komandaya qoşuldun! {points} xal əlavə edildi.",
                show_alert=True)
            await query.edit_message_text(
                f"<a href='tg://user?id={user_id}'>{query.from_user.first_name}</a> 🔴 Qırmızı komandaya qoşuldu!",
                parse_mode="HTML")
        else:
            await query.answer("Xəta baş verdi!", show_alert=True)
        return

    elif query.data == "join_blue_from_choice":
        if user_id == game_master_id.get(chat_id):
            await query.answer("‼️Aparıcı komandaya qoşula bilməz.",
                               show_alert=True)
            return
        # Check if user is already in a team
        if user_id in teams[chat_id]["red"] or user_id in teams[chat_id][
                "blue"]:
            await query.answer("Sən artıq komandadasan!", show_alert=True)
            return

        # Safely get points with default value
        pending_data = pending_team_choice.get(user_id, {})
        points = pending_data.get('points', 0)
        if points > 0:
            teams[chat_id]["blue"].append(user_id)
            team_scores[chat_id]["blue"] += points
            player_names[str(user_id)] = query.from_user.first_name

            # Add to individual scoreboard too
            add_score(chat_id, user_id, query.from_user.first_name, points)
            save_scores()

            # Remove from pending choices
            pending_team_choice.pop(user_id, None)
            await query.answer(
                f"🔵 Mavi komandaya qoşuldun! {points} xal əlavə edildi.",
                show_alert=True)
            await query.edit_message_text(
                f"<a href='tg://user?id={user_id}'>{query.from_user.first_name}</a> 🔵 Mavi komandaya qoşuldu!",
                parse_mode="HTML")
        else:
            await query.answer("Xəta baş verdi!", show_alert=True)
        return

    if not game_active.get(chat_id, False):
        if query.message.text != "DƏFOL! OYUN AKTİV DEYİL.":
            await query.edit_message_text("DƏFOL! OYUN AKTİV DEYİL.")
        else:
            await query.answer("DƏFOL! OYUN AKTİV DEYİL.")
        return

    update_activity(chat_id)

    if query.data == "show":
        # chat_id həm str, həm int ola bilər – hər ikisini yoxla
        master_id = game_master_id.get(chat_id) or game_master_id.get(str(chat_id))

        if user_id != master_id and user_id != MESHEDI_USER_ID:
            await query.answer("DƏFOL! APARICIYA QARIŞMA.", show_alert=True)
            return

        word = current_word.get(chat_id)
        if word:
            await query.answer(f"Söz: {word}", show_alert=True)
        else:
            await query.answer("Hazırda heç bir söz aktiv deyil.", show_alert=True)
        return

    if user_id != game_master_id.get(chat_id):
        await query.answer("DƏFOL! APARICIYA QARIŞMA.", show_alert=True)
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

        await query.answer(f"Yeni söz: {current_word[chat_id]}",
                           show_alert=True)

    elif query.data == "change":
        waiting_for_new_master[chat_id] = True
        current_word[chat_id] = None
        game_master_id[chat_id] = None
        await query.answer("Aparıcı dəyişdirildi", show_alert=True)
        await query.edit_message_text(
            "Aparıcı Dəfoldu. Yeni aparıcı axtarılır...")
        await context.bot.send_message(chat_id,
                                       "Kim aparıcı olmaq istəyir?",
                                       reply_markup=get_new_host_button())


async def handle_become_master(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = str(query.message.chat.id)
    user = query.from_user

    if not waiting_for_new_master.get(chat_id, False):
        await query.answer("Hazırda aparıcıya ehtiyac yoxdur.")
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
        f"Yeni aparıcı: <a href=\"tg://user?id={user.id}\">{user.full_name}</a>\nSöz yeniləndi!",
        reply_markup=get_keyboard(),
        parse_mode="HTML")


async def image_message_handler(update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
    if update.message.sticker:
        user = update.effective_user
        sticker = update.message.sticker
        sticker_id = sticker.file_unique_id

        # Check granular sticker rules first (check both file_unique_id and file_id)
        if sticker_id in STICKER_RULES or sticker.file_id in STICKER_RULES:
            rule = STICKER_RULES.get(sticker_id) or STICKER_RULES.get(sticker.file_id)
            allowed_users = rule.get("allowed", [])
            warning_message = rule.get("message", "bu stikeri yalnız icazəlilər göndərə bilər.")

            if user.id not in allowed_users and user.id != MESHEDI_USER_ID:
                try:
                    await update.message.delete()
                except Exception as e:
                    print(f"Sticker silinərkən xəta: {e}")

                warning_text = f"🚫 {user.mention_html()} — {warning_message}"
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=warning_text,
                    parse_mode="HTML")
                return

        # Check general blocked stickers
        if sticker_id in BLOCKED_STICKER_IDS and user.id != MESHEDI_USER_ID:
            try:
                await update.message.delete()
            except Exception as e:
                print(f"Stiker silinmədi: {e}")

            mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"{mention}, bu stikeri yalnız Məşədi göndərə bilər. ❌",
                parse_mode="HTML")
            return
    """Handle images and stickers for OCR text extraction and forbidden word checking"""
    try:
        # Get the file object
        if update.message.photo:
            # Get the largest photo
            file_obj = update.message.photo[-1]
        elif update.message.sticker:
            # Handle video sticker protection
            if update.message.sticker.is_video:
                user = update.effective_user
                sticker = update.message.sticker

                # Block specific stickers unless sent by Məşədi
                if sticker.file_unique_id in BLOCKED_STICKER_IDS and user.id != MESHEDI_USER_ID:
                    try:
                        await update.message.delete()
                    except Exception as e:
                        print(f"Stiker silinmədi: {e}")

                    mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=
                        f"{mention}, bu video stikeri yalnız Məşədi göndərə bilər. ❌",
                        parse_mode="HTML")
                    return

                # Allow all other video stickers or those from Məşədi - skip OCR processing
                print("Video stiker - OCR atlandı.")
                return

            # Skip animated stickers
            if update.message.sticker.is_animated:
                print("Animasiya stikeri atlandı.")
                return

            file_obj = update.message.sticker
        elif update.message.document and update.message.document.mime_type.startswith(
                'image/'):
            file_obj = update.message.document
        else:
            return

        # Get file from Telegram
        file = await context.bot.get_file(file_obj.file_id)

        # Download the image with better error handling
        try:
            response = requests.get(file.file_path)
            response.raise_for_status()

            # Try to open the image with better error handling
            image_data = io.BytesIO(response.content)
            image = Image.open(image_data)

            # Validate image format using PIL
            if image.format not in ["PNG", "JPEG", "WEBP", "GIF"]:
                print("Uyğunsuz şəkil formatı:", image.format)
                return

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
        except Exception as img_error:
            print(f"Could not process image: {img_error}")
            return

        # Enhanced OCR preprocessing for better text extraction
        try:
            # Resize small images for better OCR accuracy
            if image.width < 400 or image.height < 400:
                image = image.resize((image.width * 2, image.height * 2))

            # Convert to grayscale and apply binary threshold for cleaner text
            gray_image = image.convert('L')
            binary_image = gray_image.point(lambda x: 0
                                            if x < 150 else 255, '1')

            # Enhanced OCR with better PSM mode
            extracted_text = pytesseract.image_to_string(binary_image,
                                                         lang='eng+aze',
                                                         config='--psm 6')

            # If no meaningful text found, try with original image
            if len(extracted_text.strip()) < 3:
                try:
                    extracted_text = pytesseract.image_to_string(
                        image, lang='eng+aze')
                except:
                    pass  # Fall back to processed result
        except:
            extracted_text = ""

        # Check for forbidden words in extracted text
        if extracted_text.strip() and is_forbidden(extracted_text):
            user = update.effective_user
            if user.id != MESHEDI_USER_ID:
                try:
                    await update.message.delete()
                except Exception as e:
                    print(f"Could not delete message: {e}")

                mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=
                    f"{mention}, bu stikeri yalnız Məşədi göndərə bilər. ❌",
                    parse_mode="HTML")
                return

        # If in game mode, check if extracted text matches current word
        chat_id = str(update.effective_chat.id)
        if (game_active.get(chat_id)
                and not waiting_for_new_master.get(chat_id)
                and update.effective_user.id != game_master_id.get(chat_id)
                and extracted_text.strip()):

            # Check if any word in extracted text matches current word
            words_in_text = re.findall(r'\b\w+\b', extracted_text.lower())
            current_game_word = az_lower(current_word.get(chat_id, ""))

            for word in words_in_text:
                if az_lower(word) == current_game_word:
                    # Handle same as text message - give points and continue game
                    user = update.effective_user

                    # Team mode scoring
                    if game_mode.get(chat_id) == "team":
                        if chat_id not in teams:
                            teams[chat_id] = {"red": [], "blue": []}

                        if user.id in teams[chat_id][
                                "red"] or user.id in teams[chat_id]["blue"]:
                            add_team_score(user.id, 1, chat_id,
                                           user.first_name)
                            team_message = ""
                            if user.id in teams[chat_id]["red"]:
                                team_message = "🔴 Qırmızı komandaya xal!"
                            elif user.id in teams[chat_id]["blue"]:
                                team_message = "🔵 Mavi komandaya xal!"
                            await update.message.reply_text(
                                f"🖼️ ŞƏKILDƏN DOĞRU SÖZ TAPDIN!\n{team_message}"
                            )
                        else:
                            # Late joiner
                            pending_team_choice[user.id] = {
                                'points': 1,
                                'chat_id': chat_id
                            }
                            await update.message.reply_text(
                                "🖼️ Təbriklər! Şəkildən düzgün cavab!\n\nKomandalardan birini seç:",
                                reply_markup=get_late_joiner_keyboard())
                            player_names[str(user.id)] = user.first_name
                            save_scores()
                    else:
                        # Normal mode
                        add_score(chat_id, user.id, user.first_name)
                        await update.message.reply_text(
                            "🖼️ ŞƏKILDƏN DOĞRU SÖZ TAPDIN!")

                    player_names[str(user.id)] = user.first_name
                    save_scores()

                    # Generate new word
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
                    host_id = game_master_id.get(chat_id)
                    name = player_names.get(str(host_id), "Aparıcı")
                    await update.message.reply_text(
                        f"Yeni söz gəldi!\nAparıcı: <a href=\"tg://user?id={host_id}\">{name}</a>",
                        reply_markup=get_keyboard(),
                        parse_mode="HTML")
                    break

    except Exception as e:
        print(f"Error processing image: {e}")


async def handle_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bad words with permanent mute and report to Məşədi"""
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text
    if not contains_bad_word(text):
        return

    user = update.effective_user
    chat = update.effective_chat
    mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

    # Skip if it's Məşədi
    if user.id == MESHEDI_USER_ID:
        return

    # Delete the message
    try:
        await message.delete()
    except Exception as e:
        print(f"Mesaj silinə bilmədi: {e}")

    # Permanently mute the user (until Məşədi unmutes them)
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user.id,
            permissions=ChatPermissions(can_send_messages=False))
    except Exception as e:
        print(f"Mute xətası: {e}")

    # Send warning to group
    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=
            f"{mention}, ❌Qeyri-etik sözə görə susduruldun. Söz Məşədiyə göndərlidi.",
            parse_mode="HTML")
    except Exception as e:
        print(f"Qrup mesajı xətası: {e}")

    # Report to Məşədi and additional user
    msg = f"🚫 {mention} bu sözü yazdı: <code>{text}</code>\n\n📍Qrup: <b>{chat.title}</b>"
    for admin_id in [
            MESHEDI_USER_ID,
    ]:
        try:
            await context.bot.send_message(chat_id=admin_id,
                                           text=msg,
                                           parse_mode="HTML")
        except Exception as e:
            print(f"İstifadəçi {admin_id} üçün mesaj xətası: {e}")


async def edited_message_handler(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
    msg = update.edited_message
    if not msg or not msg.text:
        return

    # Skip if it's Məşədi
    if msg.from_user.id == MESHEDI_USER_ID:
        return

    text = msg.text
    mention = f"<a href='tg://user?id={msg.from_user.id}'>{msg.from_user.first_name}</a>"

    # Check for bad words first (higher priority)
    if contains_bad_word(text):
        try:
            await context.bot.delete_message(chat_id=msg.chat.id,
                                             message_id=msg.message_id)
        except Exception as e:
            print(f"❌ Redaktə olunmuş mesaj silinərkən xəta: {e}")

        # Permanently mute the user for bad words in edited messages
        try:
            await context.bot.restrict_chat_member(
                chat_id=msg.chat.id,
                user_id=msg.from_user.id,
                permissions=ChatPermissions(can_send_messages=False))
        except Exception as e:
            print(f"❌ Mute xətası (redaktə olunmuş mesaj): {e}")

        await context.bot.send_message(
            chat_id=msg.chat.id,
            text=f"{mention}, ❌Redaktə olunmuş mesajda qeyri-etik ifadəyə görə susduruldun.",
            parse_mode="HTML")

        # Report to Məşədi
        report_msg = f"🚫 {mention} redaktə olunmuş mesajda bu sözü yazdı: <code>{text}</code>\n\n📍Qrup: <b>{msg.chat.title}</b>"
        try:
            await context.bot.send_message(chat_id=MESHEDI_USER_ID,
                                           text=report_msg,
                                           parse_mode="HTML")
        except Exception as e:
            print(f"❌ Məşədiyə hesabat göndərilmədi: {e}")
        return

    # Check for forbidden words (defol variations)
    if is_forbidden(text):
        try:
            await context.bot.delete_message(chat_id=msg.chat.id,
                                             message_id=msg.message_id)
        except Exception as e:
            print(f"❌ Redaktə olunmuş mesaj silinmədi: {e}")

        await context.bot.send_message(
            chat_id=msg.chat.id,
            text=f"{mention}, bu sözü yalnız Məşədi yaza bilər. ❌",
            parse_mode="HTML")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = str(update.effective_chat.id)
    user = update.effective_user
    text = update.message.text.strip()

    # Check for bad words first (higher priority than defol check)
    if contains_bad_word(text) and user.id != MESHEDI_USER_ID:
        await handle_bad_words(update, context)
        return

    # Qadağan olunmuş söz, amma Məşədi yazmayıbsa
    if is_forbidden(text) and user.id != MESHEDI_USER_ID:
        try:
            await update.message.delete()
        except Exception as e:
            print(f"Mesaj silinərkən xəta: {e}")

        mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{mention}, bu sözü yalnız Məşədi yaza bilər. ❌",
            parse_mode="HTML")
        return

    # Normalize both the user input and current word for comparison
    normalized_text = normalize_word(text)

    if not game_active.get(chat_id) or waiting_for_new_master.get(chat_id):
        return

    if user.id == game_master_id.get(chat_id):
        return

    if normalized_text == normalize_word(current_word.get(chat_id, "")):
        # Komanda rejimində xal əlavə etmə
        if game_mode.get(chat_id) == "team":
            # Initialize teams if not exists
            if chat_id not in teams:
                teams[chat_id] = {"red": [], "blue": []}

            # Check if user is in a team
            if user.id in teams[chat_id]["red"] or user.id in teams[chat_id][
                    "blue"]:
                add_team_score(user.id, 1, chat_id, user.first_name)
                team_message = ""
                if user.id in teams[chat_id]["red"]:
                    team_message = "🔴 Qırmızı komandaya xal!"
                elif user.id in teams[chat_id]["blue"]:
                    team_message = "🔵 Mavi komandaya xal!"
                await update.message.reply_text(
                    f"DƏFOL! SÖZ DOĞRUDUR!\n{team_message}")
            else:
                # Late joiner - no team selected yet
                pending_team_choice[user.id] = {
                    'points': 1,
                    'chat_id': chat_id
                }  # Store the point and chat_id
                await update.message.reply_text(
                    "✅ Təbriklər! Düzgün cavab!\n\nKomandalardan birini seç, xalın ora əlavə olunacaq:",
                    reply_markup=get_late_joiner_keyboard())
                # Continue with game flow - don't return here
                player_names[str(user.id)] = user.first_name
                save_scores()
        else:
            # Normal rejim
            add_score(chat_id, user.id, user.first_name)
            await update.message.reply_text("DƏFOL! SÖZ DOĞRUDUR!")

        player_names[str(user.id)] = user.first_name
        save_scores()

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
        host_id = game_master_id.get(chat_id)
        name = player_names.get(str(host_id), "Aparıcı")
        await update.message.reply_text(
            f"Yeni söz gəldi!\nAparıcı: <a href=\"tg://user?id={host_id}\">{name}</a>",
            reply_markup=get_keyboard(),
            parse_mode="HTML")


async def show_scoreboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    if chat_id not in scoreboard or not scoreboard[chat_id]:
        await update.message.reply_text("📭 Hələ heç kim xal qazanmayıb.")
        return

    scores = scoreboard[chat_id]
    score_list = []
    for user_id, data in scores.items():
        if isinstance(data, dict):
            name = data["name"]
            score = data["score"]
        else:
            score = data
            name = player_names.get(str(user_id), f"User {user_id}")
        score_list.append((user_id, {"name": name, "score": score}))

    sorted_scores = sorted(score_list,
                           key=lambda x: x[1]["score"],
                           reverse=True)
    top_score = sorted_scores[0][1]["score"] if sorted_scores else 0

    text = "🏆 <b>Reytinq:</b>\n\n"
    medals = ['🥇', '🥈', '🥉']

    for i, (user_id, data) in enumerate(sorted_scores, start=1):
        name = data["name"]
        score = data["score"]
        medal = medals[i - 1] if i <= len(medals) else ''
        crown = ' 👑' if score == top_score and i == 1 else ''
        text += f"{i}. {medal} {name} – <b>{score} xal</b>{crown}\n"

    await update.message.reply_text(text, parse_mode="HTML")


async def sticker_logger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log sticker information to help identify file_unique_id values"""
    if update.message.sticker:
        sticker = update.message.sticker
        await update.message.reply_text(
            f"🧾 Stiker Məlumatı:\n\n"
            f"file_id: `{sticker.file_id}`\n"
            f"file_unique_id: `{sticker.file_unique_id}`\n"
            f"is_video: {sticker.is_video}\n"
            f"is_animated: {sticker.is_animated}",
            parse_mode="Markdown")


async def stikerinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("✅ /stikerinfo komandası alındı")  # Debug üçün log

    message = update.message
    if not message.reply_to_message:
        await message.reply_text(
            "❗Bu əmr yalnız bir stikeri cavablayaraq işləyir.")
        return

    sticker = message.reply_to_message.sticker
    if not sticker:
        await message.reply_text("❗Cavab verdiyin mesaj stiker deyil.")
        return

    info = (
        f"🆔 <b>File ID:</b> <code>{sticker.file_id}</code>\n"
        f"🆔 <b>Unique ID:</b> <code>{sticker.file_unique_id}</code>\n"
        f"📦 <b>Set adı:</b> {sticker.set_name or 'Yoxdur'}\n"
        f"📐 <b>Ölçü:</b> {sticker.width}x{sticker.height}\n"
        f"🎞️ <b>Tip:</b> {'Animasiya' if sticker.is_animated else 'Video' if sticker.is_video else 'Sadə'}\n"
        f"🔤 <b>Emoji:</b> {sticker.emoji or 'Yoxdur'}")
    await message.reply_text(info, parse_mode="HTML")


async def show_team_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    if chat_id not in team_scores:
        team_scores[chat_id] = {"red": 0, "blue": 0}

    red_score = team_scores[chat_id]["red"]
    blue_score = team_scores[chat_id]["blue"]
    text = f"🔴 Qırmızı Komanda: {red_score} xal\n🔵 Mavi Komanda: {blue_score} xal"
    await update.message.reply_text(text)


async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    user = update.effective_user

    if chat.type not in ["group", "supergroup"]:
        await safe_reply(
            update, context,
            "Bu əmri yalnız qrup daxilində istifadə edə bilərsiniz.")
        return

    if not await is_admin_or_authorized(update, context):
        await safe_reply(update, context, "DƏFOL! ADMİNİN İŞİNƏ QARIŞMA.")
        return

    if not game_active.get(chat_id, False):
        await safe_reply(update, context, "DƏFOL! OYUN AKTİV DEYİL.")
        return

    # Komanda oyunu rejimində qalib komanda bildiriləcək
    if game_mode.get(chat_id) == "team":
        if chat_id not in team_scores:
            team_scores[chat_id] = {"red": 0, "blue": 0}

        # Komanda xallarını göstər
        red_score = team_scores[chat_id]["red"]
        blue_score = team_scores[chat_id]["blue"]

        if red_score > blue_score:
            winner = "🔴 Qırmızı Komanda"
            difference = red_score - blue_score
            winning_team = "red"
        elif blue_score > red_score:
            winner = "🔵 Mavi Komanda"
            difference = blue_score - red_score
            winning_team = "blue"
        else:
            winner = "Heç bir komanda (bərabər)"
            difference = 0
            winning_team = None

        # Qalib komanda oyunçularının sıralanması - həmişə göstər
        player_rankings = ""
        if winning_team and chat_id in teams:
            team_players = teams[chat_id][winning_team]
            player_scores = []

            for player_id in team_players:
                # Get player name from stored names or fallback
                player_name = player_names.get(str(player_id),
                                               f"User {player_id}")

                # Get player score from scoreboard or default to 0
                if chat_id in scoreboard and str(
                        player_id) in scoreboard[chat_id]:
                    player_score = scoreboard[chat_id][str(player_id)]["score"]
                else:
                    player_score = 0

                player_scores.append((player_name, player_score))

            # Always show players, even with 0 scores
            if player_scores:
                player_scores.sort(key=lambda x: x[1], reverse=True)
                player_rankings = "\n".join([
                    f"{i + 1}. {name} – {score} xal"
                    for i, (name, score) in enumerate(player_scores)
                ])
            else:
                player_rankings = "Heç bir oyunçu tapılmadı"
        else:
            player_rankings = "Heç bir oyunçu tapılmadı"

        # Nəticə mesajını göstər
        result_message = (f"🏁 Oyun başa çatdı!\n\n"
                          f"🔴 Qırmızı Komanda: {red_score} xal\n"
                          f"🔵 Mavi Komanda: {blue_score} xal\n\n"
                          f"🏆 Qalib: {winner}\n")

        if difference > 0:
            result_message += f"📊 Xal fərqi: {difference} xal\n\n"

        if winning_team:
            result_message += f"🌟 Qalib komanda oyunçuları:\n{player_rankings}"

        await update.message.reply_text(result_message)

        # Reset team scores and clear teams
        if chat_id in team_scores:
            team_scores[chat_id]["red"] = 0
            team_scores[chat_id]["blue"] = 0
        if chat_id in teams:
            teams[chat_id]["red"].clear()
            teams[chat_id]["blue"].clear()
    else:
        # Normal oyun rejimi - istifadəçilər xal sırası ilə göstərilir
        if chat_id in scoreboard and scoreboard[chat_id]:
            scores = scoreboard[chat_id]
            score_list = []
            for user_id, data in scores.items():
                if isinstance(data, dict):
                    name = data["name"]
                    score = data["score"]
                else:
                    score = data
                    name = player_names.get(str(user_id), f"User {user_id}")
                score_list.append((user_id, {"name": name, "score": score}))

            if score_list:
                sorted_scores = sorted(score_list,
                                       key=lambda x: x[1]["score"],
                                       reverse=True)
                result_text = "🏁 Oyun başa çatdı!\n\n🏆 Son nəticələr:\n\n"
                for i, (user_id, data) in enumerate(sorted_scores, start=1):
                    name = data["name"]
                    score = data["score"]
                    result_text += f"{i}. {name} – {score} xal\n"
                await safe_reply(update, context, result_text)
            else:
                await safe_reply(
                    update, context,
                    "🏁 Oyun başa çatdı!\n\nHeç kim xal qazanmadı.")
        else:
            await safe_reply(update, context,
                             "🏁 Oyun başa çatdı!\n\nHeç kim xal qazanmadı.")

    # Nəticələri saxla
    save_scores()

    # Oyun məlumatlarını təmizlə
    game_active[chat_id] = False
    waiting_for_new_master[chat_id] = False
    game_mode[chat_id] = None


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
                        await app.bot.send_message(
                            int(chat_id),
                            "⚠️ 3 dəqiqə aktivlik olmadığından oyun avtomatik dayandırıldı."
                        )
                    except Exception as e:
                        print(f"Mesaj göndərilərkən xəta: {e}")
        await asyncio.sleep(30)


async def main():
    # Replit'də daim işlək qalması üçün keep-alive serveri başlat
    print("Keep-alive serveri başladı...")

    init_db()
    load_scores()
    load_blocked_stickers()
    load_activity_data()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("basla", startgame))
    app.add_handler(CommandHandler("dayan", stopgame))
    app.add_handler(CommandHandler("reyting", show_scoreboard))
    app.add_handler(CommandHandler("bitir", end_game))
    app.add_handler(CommandHandler("stikerinfo", stikerinfo_cmd))
    app.add_handler(CommandHandler("online", show_admin_activity))
    app.add_handler(
        CallbackQueryHandler(handle_become_master, pattern="^become_master$"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            lambda update, context: asyncio.gather(
                message_handler(update, context),
                track_admin_activity(update, context))))
    app.add_handler(
        MessageHandler(filters.UpdateType.EDITED_MESSAGE,
                       edited_message_handler))
    app.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Sticker.ALL | filters.Document.IMAGE,
            image_message_handler))
    
    # Add edited message handler from the patch
    async def handle_edited_message_patch(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.edited_message:
            return

        message = update.edited_message
        text = message.text or ""

        if is_forbidden(text):  # DƏFOL və digər senzura sözləri üçün yoxlama
            try:
                await message.delete()
                # Send notification message to user
                mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
                await context.bot.send_message(
                    chat_id=message.chat.id,
                    text=f"{mention}, bu sözü yalnız Məşədi yaza bilər.❌",
                    parse_mode="HTML"
                )
                print(f"[DELETED] Redaktə olunmuş mesaj silindi: {text}")
            except Exception as e:
                print(f"[XƏTA] Redaktə mesajı silinmədi: {e}")

    app.add_handler(MessageHandler(filters.ALL, handle_edited_message_patch), group=100)

    # Start the inactivity watcher task
    asyncio.create_task(inactivity_watcher(app))
    print("Bot işə düşdü...")

    try:
        await app.run_polling()
    except Exception as e:
        print(f"Bot xətası: {e}")
    finally:
        await app.shutdown()


if __name__ == "__main__":
    nest_asyncio.apply()
    keep_alive()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot dayandırıldı.")
    except Exception as e:
        print(f"Bot xətası: {e}")
    finally:
        print("Bot prosesi bitdi.")

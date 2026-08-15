import random
import sqlite3
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class SimpleHandler(BaseHTTPRequestHandler):
    do_GET = lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"Bot is alive!"))

def run_server():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
    server.serve_forever()

# Botla birlikte arka planda port dinlemesi için bunu başlatıyoruz:
threading.Thread(target=run_server, daemon=True).start()

TOKEN = "8945607116:AAHMB_So_Ei8t1LjFJ6WUGvE1VwTGv455Xw"
ADMIN_ID = 7580862478

# --- VERİTABANI BAŞLANGICI ---
conn = sqlite3.connect('casino.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 1000,
    last_daily TEXT
)
''')
conn.commit()

# Aktif uçuşları takip etmek için sözlük
aviator_aktif_oyunlar = {}
def get_user(user_id, username="Oyuncu"):
    cursor.execute('SELECT balance, last_daily FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute('INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)', (user_id, username, 1000))
        conn.commit()
        return 1000, None
    else:
        cursor.execute('UPDATE users SET username = ? WHERE user_id = ?', (username, user_id))
        conn.commit()
    return row[0], row[1]
    

def update_balance(user_id, amount):
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()

def miktar_coz(arg, bakiye):
    if arg.lower() == "max":
        return bakiye
    try:
        val = int(arg)
        return val if val > 0 else None
    except ValueError:
        return None

# --- BAŞLANGIÇ VE YARDIM KOMUTLARI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.first_name)
    text = (
        f"👋 Hoş geldin **{user.first_name}**!\n\n"
        "🎰 En eğlenceli ve gelişmiş Telegram casino ve şans oyunu botuna giriş yaptın. "
        "Başlangıç hediyesi olarak hesabına **1000 TL** tanımlandı!\n\n"
        "💡 *Not: Miktar yazan yerlere istersen **max** yazarak tüm bakiyeni tek seferde yatırabilirsin!*\n\n"
        "📋 Tüm oyunları ve bakiye komutlarını görmek için **/help** veya **/komutlar** yazabilirsin."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 **Casino Komutları** *(Miktar yerine **max** yazabilirsin)*\n\n"
        "🎰 `/slot [miktar/max]` — Slot makinesi\n"
        "🪙 `/yt [yazı/tura] [miktar/max]` — Yazı tura\n"
        "🎲 `/zar [miktar/max] [1-6]` — Zar at\n"
        "🎡 `/rulet [miktar/max] [0-36]` — Rulet\n"
        "💣 `/mayin [miktar/max]` — Mayın tarlası\n"
        "✈️ `/aviator [miktar/max]` — Aviator uçuş\n"
        "🃏 `/blackjack [miktar/max]` — Blackjack\n"
        "🎯 `/merdiven [miktar/max]` — Merdiven / Çarpan oyunu\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💰 `/bakiye` — Bakiyeni gör\n"
        "💸 `/bagis [id] [miktar]` — Bağış yap\n"
        "🏆 `/zenginler` — En zengin 10 oyuncu\n"
        "🧾 `/getir` — İstatistiklerin\n"
        "🎁 `/gunluk` — Günlük ödül\n"
        "🎟️ `/promo [kod]` — Promo kodu kullan\n"
        "🪪 `/id` — Telegram ID'n\n"
        "ℹ️ `/help` — Yardım"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def bakiye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bal, _ = get_user(user.id, user.first_name)
    await update.message.reply_text(f"💰 Güncel Bakiyen: **{bal}** TL", parse_mode="Markdown")

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🪪 Telegram ID'n: `{update.effective_user.id}`", parse_mode="Markdown")

async def gunluk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    _, last_daily = get_user(user.id, user.first_name)
    now = datetime.now()
    
    if last_daily:
        last_time = datetime.fromisoformat(last_daily)
        if now - last_time < timedelta(days=1):
            kalan = timedelta(days=1) - (now - last_time)
            saat, dakika = divmod(int(kalan.total_seconds() / 60), 60)
            await update.message.reply_text(f"⏳ Günlük ödülünü zaten aldın! Tekrar alabilmek için {saat} saat {dakika} dakika beklemelisin.")
            return

    update_balance(user.id, 5000)
    cursor.execute('UPDATE users SET last_daily = ? WHERE user_id = ?', (now.isoformat(), user.id))
    conn.commit()
    await update.message.reply_text("🎁 Günlük ödülün olan **5000 TL** hesabına eklendi!")

async def zenginler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.first_name)

    cursor.execute('SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10')
    rows = cursor.fetchall()
    
    text = "🏆 **En Zengin 10 Oyuncu**\n\n"
    if not rows:
        text += "Henüz kayıtlı oyuncu yok."
    else:
        for i, row in enumerate(rows, 1):
            isin = row[0] if row[0] else "Oyuncu"
            bakiye_miktari = row[1] if row[1] is not None else 0
            text += f"{i}. {isin} — **{bakiye_miktari:,}** TL\n"
            
    await update.message.reply_text(text, parse_mode="Markdown")
    
def get_user(user_id, username="Oyuncu"):
    cursor.execute('SELECT balance, last_daily FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute('INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)', (user_id, username, 1000))
        conn.commit()
        return 1000, None
    else:
        cursor.execute('UPDATE users SET username = ? WHERE user_id = ?', (username, user_id))
        conn.commit()
    return row[0], row[1]
    
async def getir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bal, _ = get_user(user.id, user.first_name)
    await update.message.reply_text(f"🧾 **İstatistiklerin**\nİsim: {user.first_name}\nID: {user.id}\nBakiye: {bal} TL", parse_mode="Markdown")

async def bagis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ Kullanım: `/bagis [kullanıcı_id] [miktar]`", parse_mode="Markdown")
        return
    try:
        hedef_id = int(args[0])
        miktar = int(args[1])
    except ValueError:
        await update.message.reply_text("⚠️ ID ve miktar sayı olmalıdır.")
        return

    bal, _ = get_user(user.id, user.first_name)
    if bal < miktar or miktar <= 0:
        await update.message.reply_text("❌ Yetersiz bakiye veya geçersiz miktar!")
        return
    
    get_user(hedef_id, "Bilinmeyen")
    update_balance(user.id, -miktar)
    update_balance(hedef_id, miktar)
    await update.message.reply_text(f"✅ Başarıyla `{hedef_id}` ID'li kullanıcıya {miktar} TL bağışladın.", parse_mode="Markdown")

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Kullanım: `/promo [kod]`", parse_mode="Markdown")
        return
    kod = args[0]
    if kod == "BEDAVA1000":
        user = update.effective_user
        update_balance(user.id, 1000)
        await update.message.reply_text("🎉 Promo kod aktifleşti! Hesabına **1000 TL** eklendi.")
    else:
        await update.message.reply_text("❌ Geçersiz veya süresi dolmuş promo kod!")

# --- ADMIN PANELİ ---
async def addpara(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Admin kontrolü
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bu komutu sadece botun admini kullanabilir!")
        return

    # Komuttan gelen metni doğrudan parçalayalım (boşluk sorununu kökten çözer)
    text_args = update.message.text.split()
    
    if len(text_args) < 3:
        await update.message.reply_text("⚠️ **Hatalı Kullanım!**\nDoğru Örnek: `/addpara 7580862478 100000`", parse_mode="Markdown")
        return

    try:
        hedef_id = int(text_args[1])
        miktar = int(text_args[2])
    except ValueError:
        await update.message.reply_text("⚠️ ID ve miktar sadece sayı olmalıdır.")
        return

    # Kullanıcıyı veritabanında kontrol et / oluştur
    get_user(hedef_id, "Admin_Eklemesi")
    
    # Bakiyeyi güncelle
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (miktar, hedef_id))
    conn.commit()
    
    yeni_durum, _ = get_user(hedef_id, "Admin_Eklemesi")
    await update.message.reply_text(f"✅ **Başarılı!**\nID: `{hedef_id}`\nEklenen: `+{miktar:,} TL`\n💳 Yeni Bakiye: `{yeni_durum:,} TL`", parse_mode="Markdown")
    

    # Sadece bakiyeyi güncelliyoruz, isme dokunmuyoruz ki veritabanı bozulmasın
async def slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bakiye, _ = get_user(user.id, user.first_name)
    
    # 1. BAHİS MİKTARI OKUMA (KÖKTEN ÇÖZÜM)
    bahis = 100 # Hiçbir şey yazılmazsa 100 TL
    
    if context.args:
        if context.args[0].lower() == "max":
            bahis = bakiye
        else:
            try:
                bahis = int(context.args[0])
            except ValueError:
                await update.message.reply_text("⚠️ **Hatalı miktar!** Lütfen sayı veya 'max' girin.")
                return

    if bahis <= 0:
        await update.message.reply_text("⚠️ **Geçersiz bahis!**")
        return

    if bakiye < bahis:
        await update.message.reply_text(f"❌ **Yetersiz Bakiye!**\nBahis miktarından ({bahis:,} TL) az bakiyen var.", parse_mode="Markdown")
        return

    msg = await update.message.reply_text(
        "🎰  **SİBİRYA KASİNO • SLOT**  🎰\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "          [  🔄  |  🔄  |  🔄  ]          \n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ *Makaralar hızla dönüyor...*", 
        parse_mode="Markdown"
    )
    
    await asyncio.sleep(1.5)
    
    semboller = ["🍒", "🍋", "🍊", "🪎", "🔔", "💎", "7️⃣"]
    
    # 2. KAZANMA ORANINI ZORLA YÜKSELTME (%55 KAZANMA ŞANSI)
    if random.random() < 0.55:
        # Kod zorla üç sembolü aynı seçer ve kazandırır
        s1 = s2 = s3 = random.choice(semboller)
    else:
        # Geri kalan %45'lik kısımda tamamen rastgele döner
        s1 = random.choice(semboller)
        s2 = random.choice(semboller)
        s3 = random.choice(semboller)
    
    kazanc = 0
    carpici = 0
    ozel_mesaj = ""

    if s1 == s2 == s3:
        if s1 == "🍒": carpici = 3; ozel_mesaj = "🍒 **VİŞNE SERİSİ!**"
        elif s1 == "🍋": carpici = 5; ozel_mesaj = "🍋 **LİMON KAZANCI!**"
        elif s1 == "🍊": carpici = 8; ozel_mesaj = "🍊 **PORTAKAL RÜYASI!**"
        elif s1 == "🪎": carpici = 12; ozel_mesaj = "🪎 **PARA YAĞMURU!**"
        elif s1 == "🔔": carpici = 15; ozel_mesaj = "🔔 **ALTIN ÇANLAR!**"
        elif s1 == "💎": carpici = 25; ozel_mesaj = "💎 **ELMAS YAĞMURU!**"
        elif s1 == "7️⃣": carpici = 50; ozel_mesaj = "🔥 **EFSANEVİ JACKPOT 777!**"
        
        kazanc = bahis * carpici
    
    if kazanc > 0:
        net_fark = kazanc - bahis
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (net_fark, user.id))
        conn.commit()
        
        yeni_bakiye, _ = get_user(user.id, user.first_name)
        sonuc = (
            f"🎰  **SİBİRYA KASİNO • SLOT**  🎰\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"          [  **{s1}**  |  **{s2}**  |  **{s3}**  ]          \n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"{ozel_mesaj}\n"
            f"🚀  **Çarpan:** `{carpici}X`\n"
            f"💰  **Kazanılan:** `+{kazanc:,} TL`\n"
            f"💵  **Yatırılan:** `{bahis:,} TL`"
        )
    else:
        cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (bahis, user.id))
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (bahis, 7580862478)) 
        conn.commit()
        
        yeni_bakiye, _ = get_user(user.id, user.first_name)
        sonuc = (
            f"🎰  **SİBİRYA KASİNO • SLOT**  🎰\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"          [  **{s1}**  |  **{s2}**  |  **{s3}**  ]          \n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"🥀  **Durum:** Kaybettin\n"
            f"💸  **Kaybedilen:** `-{bahis:,} TL`\n"
            f"💵  **Yatırılan:** `{bahis:,} TL`"
        )

    await msg.edit_text(f"{sonuc}\n\n💳  **Güncel Bakiye:** `{yeni_bakiye:,} TL`", parse_mode="Markdown")
        
# --- DİĞER OYUNLAR ---

async def yt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ Kullanım: `/yt [yazı/tura] [miktar/max]`", parse_mode="Markdown")
        return
    tahmin = args[0].lower()
    if tahmin not in ["yazı", "tura"]:
        await update.message.reply_text("⚠️ Seçim sadece 'yazı' veya 'tura' olmalıdır.")
        return
    
    bal, _ = get_user(user.id, user.first_name)
    miktar = miktar_coz(args[1], bal)

    if not miktar or bal < miktar or miktar <= 0:
        await update.message.reply_text("❌ Yetersiz bakiye veya geçersiz miktar!")
        return

    update_balance(user.id, -miktar)
    sonuc = random.choice(["yazı", "tura"])
    if tahmin == sonuc:
        update_balance(user.id, miktar * 2)
        await update.message.reply_text(f"🪙 Para atıldı: **{sonuc.upper()}**!\n🎉 Tebrikler, kazandın!")
    else:
        await update.message.reply_text(f"🪙 Para atıldı: **{sonuc.upper()}**!\n😢 Kaybettin.")

async def zar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ Kullanım: `/zar [miktar/max] [1-6]`", parse_mode="Markdown")
        return
    
    bal, _ = get_user(user.id, user.first_name)
    miktar = miktar_coz(args[0], bal)
    
    try:
        tahmin = int(args[1])
        if not (1 <= tahmin <= 6) or not miktar: raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Geçersiz miktar veya zar tahmini (1-6 arası olmalı).")
        return

    if bal < miktar or miktar <= 0:
        await update.message.reply_text("❌ Yetersiz bakiye!")
        return

    update_balance(user.id, -miktar)
    atilan = random.randint(1, 6)
    if tahmin == atilan:
        kazanc = miktar * 5
        update_balance(user.id, kazanc + miktar)
        await update.message.reply_text(f"🎲 Zar: {atilan}\n🎉 Doğru tahmin! **{kazanc}** TL kazandın!")
    else:
        await update.message.reply_text(f"🎲 Zar: {atilan}\n😢 Bilemedin, kaybettin.")

async def rulet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ Kullanım: `/rulet [miktar/max] [0-36]`", parse_mode="Markdown")
        return
    
    bal, _ = get_user(user.id, user.first_name)
    miktar = miktar_coz(args[0], bal)
    
    try:
        tahmin = int(args[1])
        if not (0 <= tahmin <= 36) or not miktar: raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Geçersiz miktar veya rulet sayısı (0-36 arası olmalı).")
        return

    if bal < miktar or miktar <= 0:
        await update.message.reply_text("❌ Yetersiz bakiye!")
        return

    update_balance(user.id, -miktar)
    gelen = random.randint(0, 36)
    if tahmin == gelen:
        kazanc = miktar * 35
        update_balance(user.id, kazanc + miktar)
        await update.message.reply_text(f"🎡 Rulet Çarkı: {gelen}\n🎯 Nokta atışı! **{kazanc}** TL kazandın!")
    else:
        await update.message.reply_text(f"🎡 Rulet Çarkı: {gelen}\n😢 Kaybettin.")

async def mayin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Kullanım: `/mayin [miktar/max]`", parse_mode="Markdown")
        return
    
    bal, _ = get_user(user.id, user.first_name)
    miktar = miktar_coz(args[0], bal)

    if not miktar or bal < miktar or miktar <= 0:
        await update.message.reply_text("❌ Yetersiz bakiye veya geçersiz miktar!")
        return
        
    update_balance(user.id, -miktar)
    if random.choice([True, False]):
        kazanc = miktar * 2
        update_balance(user.id, kazanc + miktar)
        await update.message.reply_text(f"💣 Mayın tarlasından sağ salim geçtin!\n🎉 **{kazanc}** TL kazandın!")
    else:
        await update.message.reply_text("💣 Mayına bastın!\n😢 Kaybettin.")

# --- İNTERAKTİF AVİATOR ---

import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Oyun durumlarını saklamak için bir sözlük (Kullanıcı ID : Oyun Bilgisi)
aviator_games = {}

async def aviator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bakiye, _ = get_user(user.id, user.first_name)
    
    # Kullanıcıdan hem bahsi hem de hedef çarpanı alıyoruz
    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ **Kullanım:** `/aviator <bahis> <hedef_x>`\n"
            "Örnek: `/aviator 100 2.5` (100 TL yatırır, 2.5x'te otomatik çeker)", 
            parse_mode="Markdown"
        )
        return
        
    try:
        bahis = float(context.args[0])
        hedef_x = float(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ **Hatalı format!** Bahis ve hedef çarpan sayı olmalıdır.")
        return

    # Sınırlandırmalar ve kontroller
    if bahis <= 0:
        await update.message.reply_text("⚠️ Geçersiz bahis miktarı!")
        return
        
    if hedef_x < 1.01 or hedef_x > 250:
        await update.message.reply_text("⚠️ Hedef çarpan **1.01x** ile **250x** arasında olmalıdır.")
        return

    if bakiye < bahis:
        await update.message.reply_text(f"❌ **Yetersiz Bakiye!**\n(Bakiyen: {bakiye:,.2f} TL)")
        return

    # Oyuna girerken parayı bakiyeden düşüyoruz
    cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (bahis, user.id))
    conn.commit()

    # Başlangıç mesajı
    msg = await update.message.reply_text(
        f"🛫 **AVIATOR BAŞLIYOR!**\n\n"
        f"💵 **Bahis:** `{bahis:,.2f} TL`\n"
        f"🎯 **Hedeflenen Çarpan:** `{hedef_x}x`\n\n"
        f"☁️ *Uçak havalanıyor...*", 
        parse_mode="Markdown"
    )
    
    # Uçağın uçma hissini vermek için ufak bir bekleme süresi
    await asyncio.sleep(2.5)
    
    # 1.00 ile 250.00 arası rastgele patlama noktasını belirliyoruz
    patlama_x = round(random.uniform(1.0, 250.0), 2)
    
    # Sonuçları değerlendiriyoruz
    if hedef_x <= patlama_x:
        # Uçak hedefi buldu veya geçti (KAZANÇ)
        kazanc = bahis * hedef_x
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (kazanc, user.id))
        conn.commit()
        
        yeni_bakiye, _ = get_user(user.id, user.first_name)
        
        await msg.edit_text(
            f"🛬 **UÇAK UÇTU!** (Patlama Noktası: `{patlama_x}x`)\n\n"
            f"✅ **KAZANDIN!** Uçak belirlediğin hedefe ulaştı.\n\n"
            f"🎯 **Bozdurulan Hedef:** `{hedef_x}x`\n"
            f"💰 **Kazanılan:** `+{kazanc:,.2f} TL`\n"
            f"💳 **Güncel Bakiye:** `{yeni_bakiye:,.2f} TL`",
            parse_mode="Markdown"
        )
    else:
        # Uçak hedefe ulaşamadan patladı (KAYIP)
        # Bakiye zaten en başta düşüldüğü için sadece mesaj güncelliyoruz
        yeni_bakiye, _ = get_user(user.id, user.first_name)
        
        await msg.edit_text(
            f"💥 **UÇAK DÜŞTÜ!** (Patlama Noktası: `{patlama_x}x`)\n\n"
            f"❌ **KAYBETTİN!** Uçak sen bozduramadan patladı.\n\n"
            f"🎯 **Hedefin:** `{hedef_x}x`\n"
            f"💸 **Kaybedilen:** `-{bahis:,.2f} TL`\n"
            f"💳 **Güncel Bakiye:** `{yeni_bakiye:,.2f} TL`",
            parse_mode="Markdown"
        )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    
    if user.id not in aviator_games or not aviator_games[user.id]["aktif"]:
        await query.answer("❌ Oyun zaten bitti veya başlamadı!")
        return

    game = aviator_games[user.id]
    # Şu anki rastgele bir anlık çarpan üret (patlama noktasını geçemez)
    anlik_carpan = round(random.uniform(1.0, game["patlama"]), 2)
    
    kazanc = int(game["bahis"] * anlik_carpan)
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (kazanc, user.id))
    conn.commit()
    
    game["aktif"] = False
    await query.message.edit_text(
        f"✅ **KAZANDIN!**\n\n"
        f"Çarpan: `{anlik_carpan}x`\n"
        f"Toplam Ödeme: `{kazanc} TL`"
    )

async def blackjack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Kullanım: `/blackjack [miktar/max]`", parse_mode="Markdown")
        return
    
    bal, _ = get_user(user.id, user.first_name)
    miktar = miktar_coz(args[0], bal)

    if not miktar or bal < miktar or miktar <= 0:
        await update.message.reply_text("❌ Yetersiz bakiye veya geçersiz miktar!")
        return
        
    update_balance(user.id, -miktar)
    oyuncu = random.randint(15, 21)
    kasa = random.randint(16, 21)
    msg = f"🃏 Senin Kartların Toplamı: {oyuncu}\n🤖 Kasanın Kartları: {kasa}\n\n"
    if oyuncu > kasa or kasa > 21:
        update_balance(user.id, miktar * 2)
        msg += "🎉 Blackjack! Kazandın!"
    elif oyuncu == kasa:
        update_balance(user.id, miktar)
        msg += "🤝 Berabere, paran iade edildi."
    else:
        msg += "😢 Kasa kazandı!"
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- MERDİVEN ---

async def merdiven_komut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Kullanım: `/merdiven [miktar/max]`\nÖrnek: `/merdiven max`", parse_mode="Markdown")
        return
    
    bal, _ = get_user(user.id, user.first_name)
    miktar = miktar_coz(args[0], bal)

    if not miktar or bal < miktar or miktar <= 0:
        await update.message.reply_text("❌ Bakiyen yetersiz veya geçersiz miktar!")
        return

    keyboard = [
        [
            InlineKeyboardButton("1.5x", callback_data=f"m_oyna_{miktar}_1.5"),
            InlineKeyboardButton("2x", callback_data=f"m_oyna_{miktar}_2.0"),
            InlineKeyboardButton("3x", callback_data=f"m_oyna_{miktar}_3.0"),
        ],
        [
            InlineKeyboardButton("5x", callback_data=f"m_oyna_{miktar}_5.0"),
            InlineKeyboardButton("10x", callback_data=f"m_oyna_{miktar}_10.0"),
            InlineKeyboardButton("50x", callback_data=f"m_oyna_{miktar}_50.0"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🎯 **Merdiven Oyunu**\n💰 Bahis Miktarınız: **{miktar}** TL\n\nŞimdi hedeflemek istediğin çarpanı seç:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def merdiven_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    user = query.from_user

    if data[1] == "oyna":
        miktar = int(data[2])
        secilen_carpan = float(data[3])

        bal, _ = get_user(user.id, user.first_name)
        if bal < miktar:
            await query.edit_message_text("❌ Yetersiz bakiye!")
            return

        update_balance(user.id, -miktar)

        olasi_patlamalar = [1.5, 2.0, 3.0, 5.0, 10.0, 50.0]
        patlama_noktasi = random.choice(olasi_patlamalar)

        await query.edit_message_text(f"🎯 Merdiven tırmanılıyor... Bahis: {miktar} TL | Hedef: **{secilen_carpan}x** 🧗‍♂️ Bekle...")
        await asyncio.sleep(1.2)

        if secilen_carpan <= patlama_noktasi:
            kazanc = int(miktar * secilen_carpan)
            update_balance(user.id, kazanc)
            await query.edit_message_text(
                f"🎯 Bot **{patlama_noktasi}x**'te patladı!\n"
                f"🎉 Seçtiğin **{secilen_carpan}x** hedefine başarıyla ulaştın!\n"
                f"💰 Kazancın: **{kazanc}** TL",
                parse_mode="Markdown"
            )
        else:
             await query.edit_message_text(
                f"💥 Bot **{patlama_noktasi}x**'te patladı, sen **{secilen_carpan}x** seçmiştin!\n"
                f"😢 Merdivenden düştün, kaybettin.",
                parse_mode="Markdown"
            )

# --- ANA ÇALIŞTIRICI ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("komutlar", help_command))
    app.add_handler(CommandHandler("bakiye", bakiye))
    app.add_handler(CommandHandler("id", my_id))
    app.add_handler(CommandHandler("gunluk", gunluk))
    app.add_handler(CommandHandler("zenginler", zenginler))
    app.add_handler(CommandHandler("getir", getir))
    app.add_handler(CommandHandler("bagis", bagis))
    app.add_handler(CommandHandler("promo", promo))
    
    app.add_handler(CommandHandler("addpara", addpara))

    app.add_handler(CommandHandler("slot", slot))
    app.add_handler(CommandHandler("yt", yt))
    app.add_handler(CommandHandler("zar", zar))
    app.add_handler(CommandHandler("rulet", rulet))
    app.add_handler(CommandHandler("mayin", mayin))
    app.add_handler(CommandHandler("aviator", aviator))
    app.add_handler(CommandHandler("blackjack", blackjack))
    app.add_handler(CommandHandler("merdiven", merdiven_komut))

    app.add_handler(CallbackQueryHandler(merdiven_callback, pattern="^m_"))
    app.add_handler(CallbackQueryHandler(aviator_callback, pattern="^av_"))

    print("--- BOT BAŞARIYLA AKTİF EDİLDİ ---")
    app.run_polling()

if __name__ == '__main__':
    main()

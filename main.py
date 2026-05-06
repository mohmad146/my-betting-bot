import telebot
from telebot import types
import sqlite3
import random
import os
from threading import Thread

# --- Flask لضمان استمرارية الخدمة على Render ---
from flask import Flask
app = Flask('')
@app.route('/')
def home(): return "Bot is Online"
def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
Thread(target=run).start()

# --- الإعدادات الأساسية ---
TOKEN = "8794915463:AAFbV4970zrM3A4__2yRBAnUPWPB0j6a0XU"
ADMIN_ID = 8005234076
CHANNEL_ID = "@winninglot"  # معرف القناة
CHANNEL_URL = "https://t.me/winninglot"
MY_USER_URL = "https://t.me/M_2_4_4"

bot = telebot.TeleBot(TOKEN)

# --- قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('winners.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, referred_by INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS rooms 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, creator_id INTEGER, amount REAL, participants TEXT, count INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# --- التحقق من الاشتراك في القناة ---
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

# --- لوحة التحكم الأساسية ---
def main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎯 القرعات المفتوحة", callback_data="view_rooms"),
        types.InlineKeyboardButton("➕ إنشاء قرعة جديدة", callback_data="create_room"),
        types.InlineKeyboardButton("💰 رصيدي", callback_data="my_balance"),
        types.InlineKeyboardButton("👥 نظام الإحالة", callback_data="referral"),
        types.InlineKeyboardButton("🏦 سحب الأرباح", url=f"{MY_USER_URL}?text=سحب_أرباح"),
        types.InlineKeyboardButton("💳 شحن رصيد", url=f"{MY_USER_URL}?text=شحن_رصيد"),
        types.InlineKeyboardButton("📜 شرح النظام", callback_data="how_it_works")
    )
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    
    # التحقق من الاشتراك أولاً
    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 اشترك في القناة هنا", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("✅ تم الاشتراك، ابدأ الآن", callback_data="check_sub"))
        bot.send_message(user_id, "⚠️ عفواً، يجب عليك الاشتراك في القناة أولاً لاستخدام البوت.", reply_markup=markup)
        return

    # معالجة الإحالة
    conn = sqlite3.connect('winners.db', check_same_thread=False)
    user_exists = conn.cursor().execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
    
    if not user_exists:
        referred_by = None
        if len(message.text.split()) > 1:
            ref_id = message.text.split()[1]
            if ref_id.isdigit() and int(ref_id) != user_id:
                referred_by = int(ref_id)
                # إضافة 100 جنيه للمحيل
                conn.cursor().execute("UPDATE users SET balance = balance + 100 WHERE id = ?", (referred_by,))
                bot.send_message(referred_by, "🎁 حصلت على 100 جنيه مكافأة لإحالة مستخدم جديد!")
        
        conn.cursor().execute("INSERT INTO users (id, balance, referred_by) VALUES (?, 0, ?)", (user_id, referred_by))
        conn.commit()
    
    conn.close()
    bot.send_message(user_id, "🏆 مرحباً بك في Winners!\nأقوى نظام قرعة جماعية في السودان.", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.message.chat.id
    conn = sqlite3.connect('winners.db', check_same_thread=False)
    
    if call.data == "check_sub":
        if is_subscribed(user_id):
            bot.send_message(user_id, "✅ شكراً لاشتراكك! يمكنك الآن البدء.", reply_markup=main_keyboard())
        else:
            bot.answer_callback_query(call.id, "❌ لم تشترك في القناة بعد!", show_alert=True)

    elif call.data == "referral":
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        text = (f"👥 **نظام الإحالة:**\n\n"
                f"شارك رابطك واحصل على:\n"
                f"1️⃣ **100 جنيه** عند تسجيل أي شخص.\n"
                f"2️⃣ **10%** عمولة من كل فوز يحققه أصدقاؤك.\n\n"
                f"رابطك الخاص:\n`{ref_link}`")
        bot.send_message(user_id, text, parse_mode="Markdown")

    elif call.data == "my_balance":
        user = conn.cursor().execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
        bot.send_message(user_id, f"💰 رصيدك الحالي: {user[0]} جنيه\n🆔 معرفك: `{user_id}`", parse_mode="Markdown")

    elif call.data == "create_room":
        bot.send_message(user_id, "أرسل مبلغ القرعة (أرقام فقط، الحد الأدنى 1000 جنيه):")
        bot.register_next_step_handler(call.message, process_create_room)

    elif call.data == "view_rooms":
        rooms = conn.cursor().execute("SELECT * FROM rooms WHERE count < 10").fetchall()
        if not rooms:
            bot.send_message(user_id, "لا توجد قرعات مفتوحة حالياً.")
        else:
            markup = types.InlineKeyboardMarkup()
            for r in rooms:
                markup.add(types.InlineKeyboardButton(f"قرعة بـ {r[2]} جنيه ({r[4]}/10 مشاركين)", callback_data=f"join_{r[0]}"))
            bot.send_message(user_id, "اختر القرعة للانضمام:", reply_markup=markup)

    elif call.data.startswith("join_"):
        room_id = call.data.split("_")[1]
        room = conn.cursor().execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
        user_row = conn.cursor().execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
        
        if str(user_id) in (room[3] or "").split(","):
            bot.answer_callback_query(call.id, "❌ أنت مشارك بالفعل!")
        elif user_row[0] < room[2]:
            bot.send_message(user_id, "❌ رصيدك غير كافٍ.")
        else:
            new_participants = (room[3] + "," if room[3] else "") + str(user_id)
            new_count = room[4] + 1
            conn.cursor().execute("UPDATE users SET balance = balance - ? WHERE id = ?", (room[2], user_id))
            conn.cursor().execute("UPDATE rooms SET participants = ?, count = ? WHERE id = ?", (new_participants, new_count, room_id))
            conn.commit()
            bot.send_message(user_id, f"✅ تم انضمامك. المتبقي {10 - new_count} مشاركين.")
            if new_count == 10: process_draw(room_id, room[2])
    conn.close()

def process_create_room(message):
    try:
        amount = float("".join(filter(str.isdigit, message.text)))
        if amount < 1000:
            bot.send_message(message.chat.id, "❌ الحد الأدنى 1000 جنيه.")
            return
        user_id = message.chat.id
        conn = sqlite3.connect('winners.db', check_same_thread=False)
        balance = conn.cursor().execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()[0]
        if balance >= amount:
            conn.cursor().execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user_id))
            conn.cursor().execute("INSERT INTO rooms (creator_id, amount, participants, count) VALUES (?, ?, ?, ?)", (user_id, amount, str(user_id), 1))
            conn.commit()
            bot.send_message(user_id, f"✅ تم إنشاء قرعة بـ {amount} جنيه.")
        else:
            bot.send_message(user_id, "❌ رصيدك غير كافٍ.")
        conn.close()
    except: bot.send_message(message.chat.id, "⚠️ أرسل مبلغاً صحيحاً.")

def process_draw(room_id, bet_amount):
    conn = sqlite3.connect('winners.db', check_same_thread=False)
    room = conn.cursor().execute("SELECT participants FROM rooms WHERE id=?", (room_id,)).fetchone()
    p_list = room[0].split(",")
    random.shuffle(p_list)
    winners = p_list[:5]
    win_value = bet_amount * 1.5
    commission = win_value * 0.10 # عمولة المحيل 10%

    for p in p_list:
        if p in winners:
            conn.cursor().execute("UPDATE users SET balance = balance + ? WHERE id = ?", (win_value, p))
            bot.send_message(p, f"🎊 مبروك! لقد فزت في القرعة وحصلت على {win_value} جنيه!")
            
            # توزيع عمولة الإحالة
            ref = conn.cursor().execute("SELECT referred_by FROM users WHERE id=?", (p,)).fetchone()
            if ref and ref[0]:
                conn.cursor().execute("UPDATE users SET balance = balance + ? WHERE id = ?", (commission, ref[0]))
                bot.send_message(ref[0], f"📈 حصلت على {commission} جنيه كعمولة من فوز صديقك!")
        else:
            bot.send_message(p, "😔 حظ أوفر، اكتملت القرعة ولم يحالفك الحظ هذه المرة.")
            
    conn.cursor().execute("DELETE FROM rooms WHERE id = ?", (room_id,))
    conn.commit()
    conn.close()

# --- أوامر الإدارة ---
@bot.message_handler(commands=['pay', 'cut', 'user'])
def admin_commands(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            cmd, target_id = parts[0], parts[1]
            conn = sqlite3.connect('winners.db', check_same_thread=False)
            if cmd == "/user":
                res = conn.cursor().execute("SELECT balance FROM users WHERE id=?", (target_id,)).fetchone()
                bot.send_message(ADMIN_ID, f"👤 المستخدم: {target_id}\n💰 الرصيد: {res[0]} جنيه")
            elif cmd == "/pay":
                conn.cursor().execute("UPDATE users SET balance = balance + ? WHERE id = ?", (float(parts[2]), target_id))
                bot.send_message(target_id, f"🎉 تم شحن {parts[2]} جنيه لحسابك!")
                bot.send_message(ADMIN_ID, "✅ تم الشحن.")
            elif cmd == "/cut":
                conn.cursor().execute("UPDATE users SET balance = balance - ? WHERE id = ?", (float(parts[2]), target_id))
                bot.send_message(ADMIN_ID, "✅ تم الخصم.")
            conn.commit()
            conn.close()
        except: bot.send_message(ADMIN_ID, "الصيغة: /cmd ID amount")

bot.infinity_polling()

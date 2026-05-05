import telebot
from telebot import types
import sqlite3
import random

# --- بياناتك المحدثة ---
TOKEN = "8794915463:AAFbV4970zrM3A4__2yRBAnUPWPB0j6a0XU"
ADMIN_ID = 8005234076
MY_USER_URL = "https://t.me/M_2_4_4" 

bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('winners.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, creator_id INTEGER, bet_amount REAL, participants TEXT, count INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

def main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🎯 الرهانات المفتوحة", callback_data="view_rooms"),
        types.InlineKeyboardButton("➕ إنشاء رهان جديد", callback_data="create_room"),
        types.InlineKeyboardButton("💰 رصيدي", callback_data="my_balance"),
        types.InlineKeyboardButton("🏦 سحب الأرباح (أقل شيء 5000)", url=f"{MY_USER_URL}?text=أريد_سحب_أرباحي"),
        types.InlineKeyboardButton("💳 شحن رصيد", url=f"{MY_USER_URL}?text=أريد_شحن_رصيد"),
        types.InlineKeyboardButton("📜 شرح طريقة العمل", callback_data="how_it_works")
    )
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    conn = sqlite3.connect('winners.db', check_same_thread=False)
    conn.cursor().execute("INSERT OR IGNORE INTO users (id, balance) VALUES (?, 0)", (user_id,))
    conn.commit()
    conn.close()
    bot.send_message(user_id, "🏆 مرحباً بك في Winners!\nأقوى نظام قرعة جماعية في السودان.", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.message.chat.id
    conn = sqlite3.connect('winners.db', check_same_thread=False)
    
    if call.data == "how_it_works":
        text = ("📜 **نظام عمل البوت:**\n\n"
                "• الرهان يبدأ من **1000 نقطة**.\n"
                "• نحتاج لـ **10 مشاركين** لاكتمال الغرفة.\n"
                "• يختار البوت **5 فائزين** عشوائياً.\n"
                "• الفائز ينال مبلغه + 50% ربح.\n"
                "• السحب يبدأ من **5000 نقطة**.")
        bot.send_message(user_id, text, parse_mode="Markdown")

    elif call.data == "my_balance":
        user = conn.cursor().execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
        bot.send_message(user_id, f"💳 رصيدك الحالي: {user[0] if user else 0} نقطة")

    elif call.data == "create_room":
        bot.send_message(user_id, "أرسل مبلغ الرهان الآن (أرقام فقط، الحد الأدنى 1000):")
        bot.register_next_step_handler(call.message, process_create_room)

    elif call.data == "view_rooms":
        rooms = conn.cursor().execute("SELECT * FROM rooms WHERE count < 10").fetchall()
        if not rooms:
            bot.send_message(user_id, "لا توجد رهانات مفتوحة حالياً.")
        else:
            markup = types.InlineKeyboardMarkup()
            for r in rooms:
                markup.add(types.InlineKeyboardButton(f"رهان بـ {r[2]} نقطة ({r[4]}/10 مشاركين)", callback_data=f"join_{r[0]}"))
            bot.send_message(user_id, "اختر الرهان:", reply_markup=markup)

    elif call.data.startswith("join_"):
        room_id = call.data.split("_")[1]
        room = conn.cursor().execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
        user_row = conn.cursor().execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
        user_balance = user_row[0] if user_row else 0
        
        participants = room[3].split(",") if room[3] else []
        if str(user_id) in participants:
            bot.answer_callback_query(call.id, "❌ أنت مشارك بالفعل!")
        elif user_balance < room[2]:
            bot.send_message(user_id, "❌ رصيدك غير كافٍ للمشاركة في هذا الرهان.")
        else:
            new_participants = room[3] + f",{user_id}" if room[3] else f"{user_id}"
            new_count = room[4] + 1
            conn.cursor().execute("UPDATE users SET balance = balance - ? WHERE id = ?", (room[2], user_id))
            conn.cursor().execute("UPDATE rooms SET participants = ?, count = ? WHERE id = ?", (new_participants, new_count, room_id))
            conn.commit()
            bot.send_message(user_id, f"✅ تم انضمامك. المتبقي {10 - new_count} مشاركين.")
            if new_count == 10: process_draw(room_id, room[2])
    conn.close()

def process_create_room(message):
    try:
        amount_str = "".join(filter(str.isdigit, message.text))
        amount = float(amount_str)
        
        if amount < 1000:
            bot.send_message(message.chat.id, "❌ الحد الأدنى للرهان هو 1000 نقطة.")
            return
            
        user_id = message.chat.id
        conn = sqlite3.connect('winners.db', check_same_thread=False)
        user_row = conn.cursor().execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
        balance = user_row[0] if user_row else 0
        
        if balance >= amount:
            conn.cursor().execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user_id))
            conn.cursor().execute("INSERT INTO rooms (creator_id, bet_amount, participants, count) VALUES (?, ?, ?, ?)", (user_id, amount, str(user_id), 1))
            conn.commit()
            bot.send_message(user_id, f"✅ تم إنشاء رهان بـ {amount} نقطة.")
        else:
            bot.send_message(user_id, "❌ رصيدك غير كافٍ لإنشاء الرهان.")
        conn.close()
    except:
        bot.send_message(message.chat.id, "⚠️ يرجى إرسال مبلغ صحيح.")

def process_draw(room_id, bet_amount):
    conn = sqlite3.connect('winners.db', check_same_thread=False)
    room = conn.cursor().execute("SELECT participants FROM rooms WHERE id=?", (room_id,)).fetchone()
    p_list = room[0].split(",")
    random.shuffle(p_list)
    winners = p_list[:5]
    win_value = bet_amount * 1.5
    
    for p in p_list:
        if p in winners:
            conn.cursor().execute("UPDATE users SET balance = balance + ? WHERE id = ?", (win_value, p))
            bot.send_message(p, f"🎊 مبروك! فزت بـ {win_value} نقطة!")
        else:
            bot.send_message(p, "😔 حظ أوفر في المرة القادمة.")
            
    conn.cursor().execute("DELETE FROM rooms WHERE id = ?", (room_id,))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['pay', 'cut'])
def admin_commands(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            cmd, target, amount = parts[0], parts[1], float(parts[2])
            conn = sqlite3.connect('winners.db', check_same_thread=False)
            if cmd == "/pay":
                conn.cursor().execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, target))
                bot.send_message(target, f"🎉 تم شحن {amount} نقطة لحسابك!")
            else:
                conn.cursor().execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, target))
                bot.send_message(target, f"⚠️ تم خصم {amount} نقطة من حسابك.")
            conn.commit()
            conn.close()
            bot.send_message(ADMIN_ID, "✅ تمت العملية.")
        except:
            bot.send_message(ADMIN_ID, "⚠️ الصيغة: /pay ID amount")

bot.infinity_polling()

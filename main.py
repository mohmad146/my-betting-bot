import telebot
from telebot import types
import sqlite3

# --- الإعدادات (هنا تضع بياناتك) ---
TOKEN = "8794915463:AAFbV4970zrM3A4__2yRBAnUPWPB0j6a0XU"
ADMIN_ID = 8005234076  # ضع الايدي الخاص بك هنا (اطلبه من بوت @userinfobot)

bot = telebot.TeleBot(TOKEN)

# --- إعداد قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('winners.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# --- القوائم (Buttons) ---
def main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("⚽ المراهنة", callback_data="start_bet"),
               types.InlineKeyboardButton("💰 رصيدي", callback_data="my_balance"),
               types.InlineKeyboardButton("🏦 سحب الأرباح", callback_data="withdraw"),
               types.InlineKeyboardButton("📞 شحن حسابي", callback_data="support"))
    return markup

# --- الأوامر ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    conn = sqlite3.connect('winners.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    
    welcome_msg = "🏆 مرحباً بك في بوت Winners!\nأرسل الايدي الخاص بك للمدير لشحن رصيدك.\n\n🆔 الايدي الخاص بك: {}".format(user_id)
    bot.send_message(user_id, welcome_msg, reply_markup=main_keyboard(), parse_mode="Markdown")

# --- معالجة الأزرار ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.message.chat.id
    if call.data == "my_balance":
        conn = sqlite3.connect('winners.db', check_same_thread=False)
        user = conn.cursor().execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        bot.send_message(user_id, f"💳 رصيدك الحالي: {user[0]} نقطة")
    elif call.data == "support":
        bot.send_message(user_id, "لشحن النقاط، تواصل مع المدير وأرسل له الايدي الخاص بك.")

# --- أمر الشحن (للأدمن فقط) ---
@bot.message_handler(commands=['pay'])
def pay(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            target_id = parts[1]
            amount = float(parts[2])
            conn = sqlite3.connect('winners.db', check_same_thread=False)
            conn.cursor().execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, target_id))
            conn.commit()
            conn.close()
            bot.send_message(message.chat.id, f"✅ تم شحن {amount} نقطة.")
            bot.send_message(target_id, f"🎉 مبروك! تم إضافة {amount} نقطة لرصيدك.")
        except:
            bot.send_message(message.chat.id, "خطأ! استخدم الصيغة: /pay ID amount")

print("البوت يعمل بنجاح...")
bot.infinity_polling()
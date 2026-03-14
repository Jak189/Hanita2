# -------------------------------------------
# HANITA BOT — የ Render እና Railway ጥምር ስሪት
# -------------------------------------------

import telebot
from telebot import types
import time
import json
import os
import sys
from flask import Flask
from threading import Thread

# Gemini
from google import genai
from google.genai.errors import APIError

# --- Render/Railway Port Configuration ---
app = Flask('')

@app.route('/')
def home():
    return "Hanita Bot is Running!"

def run():
    # Render PORT ይጠቀማል፣ ካልተገኘ 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# -------------------------------------------
# 1. TOKEN & KEYS and CONFIG
# -------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
except ValueError:
    ADMIN_ID = 0

OWNER_TITLE = os.environ.get("OWNER_TITLE", "The Red Penguins Keeper")
TELEGRAM_GROUP_ID = -1003390908033
GROUP_LINK = "https://t.me/hackersuperiors"
OWNER_PHOTO_PATH = "owner_photo.jpg"

if not BOT_TOKEN or not GEMINI_API_KEY:
    print("❌ BOT_TOKEN ወይም GEMINI_API_KEY አልተገኘም።")
    sys.exit(1)

try:
    bot = telebot.TeleBot(BOT_TOKEN)
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"❌ BOT ወይም GEMINI Client ሲነሳ ስህተት ተፈጥሯል: {e}")
    sys.exit(1)

# Gemini 2.5 flash ገና ስላልተለቀቀ ወደ 2.0 ተስተካክሏል
GEMINI_MODEL = "gemini-2.0-flash"

# -------------------------------------------
# 2. FILES & JSON HANDLERS
# -------------------------------------------

USER_FILE = "users.json"
USER_DATA_FILE = "user_data.json"
CHAT_LOG_FILE = "chat_log.txt"

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def track_user(user_id):
    user_id = str(user_id)
    users = load_json(USER_FILE, [])
    if user_id not in users:
        users.append(user_id)
        save_json(USER_FILE, users)

def log_chat(user_id, question, answer):
    log_entry = f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\nUSER ID: {user_id}\nQ: {question}\nA: {answer}\n\n"
    with open(CHAT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

def get_user_data(uid):
    data = load_json(USER_DATA_FILE, {})
    return data.get(str(uid))

def send_long_message(chat_id, text, parse_mode='Markdown'):
    MAX = 4096
    if len(text) > MAX:
        for i in range(0, len(text), MAX):
            bot.send_message(chat_id, text[i:i+MAX], parse_mode=parse_mode)
            time.sleep(0.3)
    else:
        bot.send_message(chat_id, text, parse_mode=parse_mode)

def check_group_membership(user_id):
    try:
        chat_member = bot.get_chat_member(TELEGRAM_GROUP_ID, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# -------------------------------------------
# 3. COMMANDS
# -------------------------------------------

@bot.message_handler(commands=['start'])
def start(message):
    track_user(message.from_user.id)
    user_id = message.from_user.id
    if check_group_membership(user_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("/register"), types.KeyboardButton("/help"))
        send_long_message(message.chat.id, f"👋 ሰላም {message.from_user.first_name}!\n\nአሁን **/register** በመጫን ይመዝገቡ።")
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👉 ግሩፕ ይቀላቀሉ", url=GROUP_LINK))
        markup.add(types.InlineKeyboardButton("✅ ከተቀላቀሉ በኋላ ይጫኑ", callback_data='check_join'))
        bot.send_message(message.chat.id, "🛑 ለመጠቀም መጀመሪያ ግሩፑን ይቀላቀሉ።", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'check_join')
def callback_check_join(call):
    if check_group_membership(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ ተቀላቅለዋል! አሁን /start ይበሉ ወይም ይመዝገቡ።")
    else:
        bot.answer_callback_query(call.id, "❌ ግሩፑን ገና አልተቀላቀሉም።")

@bot.message_handler(commands=['usercount'])
def user_count(message):
    if message.from_user.id == ADMIN_ID:
        users = load_json(USER_FILE, [])
        bot.send_message(message.chat.id, f"👥 ጠቅላላ ተጠቃሚ: {len(users)}")

@bot.message_handler(commands=['help'])
def show_help(message):
    bot.send_message(message.chat.id, "📚 መመሪያዎች:\n1. /register\n2. ጥያቄ መላክ\n3. /ownerphoto")

@bot.message_handler(commands=['register'])
def ask_full_name(message):
    msg = bot.send_message(message.chat.id, "👉 ሙሉ ስምዎን ያስገቡ:", reply_markup=telebot.types.ForceReply())
    bot.register_next_step_handler(msg, get_full_name)

def get_full_name(message):
    user_id = str(message.from_user.id)
    data = load_json(USER_DATA_FILE, {})
    data[user_id] = {"full_name": message.text, "username": message.from_user.username}
    save_json(USER_DATA_FILE, data)
    msg = bot.send_message(message.chat.id, "👉 አድራሻዎን ያስገቡ:", reply_markup=telebot.types.ForceReply())
    bot.register_next_step_handler(msg, get_address)

def get_address(message):
    user_id = str(message.from_user.id)
    data = load_json(USER_DATA_FILE, {})
    if user_id in data:
        data[user_id]["address"] = message.text
        save_json(USER_DATA_FILE, data)
        bot.send_message(message.chat.id, "✅ ተመዝግበዋል። አሁን ጥያቄ መጠየቅ ይችላሉ።")
        if ADMIN_ID != 0:
            bot.send_message(ADMIN_ID, f"🔔 አዲስ ሰው ተመዝግቧል: {data[user_id]['full_name']}")

# -------------------------------------------
# 4. CHAT LOGIC
# -------------------------------------------

@bot.message_handler(func=lambda m: True)
def gemini_auto(message):
    track_user(message.from_user.id)
    user_id = str(message.from_user.id)
    if message.text.startswith("/"): return

    data = load_json(USER_DATA_FILE, {})
    if user_id not in data:
        bot.send_message(message.chat.id, "🛑 ለመጠቀም መጀመሪያ በ /register ይመዝገቡ።")
        return

    prompt = f"Hanita ነሽ። ብልህ እና ሙያዊ ረዳት። ባለቤትሽ {OWNER_TITLE} ነው። ጥያቄ: {message.text}"
    try:
        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        bot.send_message(message.chat.id, response.text)
        log_chat(user_id, message.text, response.text)
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ ስህተት ተፈጠረ።")

# -------------------------------------------
# 5. RUN BOT
# -------------------------------------------

print("🤖 Hanita Bot እየተነሳ ነው...")

# Flaskን ያስነሳል (ለ Render)
keep_alive()

while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=30)
    except Exception as e:
        print(f"❌ ስህተት: {e}")
        time.sleep(3)

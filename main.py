# -------------------------------------------
# HANITA BOT — Render Optimized Version
# -------------------------------------------

import telebot
from telebot import types
import time
import json
import os
import sys

# Gemini
from google import genai
from google.genai.errors import APIError

# Flask (ለ Render 'Stay Alive' የሚረዳ)
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Hanita Bot is running!"

def run_web_server():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# -------------------------------------------
# 1. TOKEN & KEYS and CONFIG - ከ ENVIRONMENT VARIABLES ማንበብ
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
    print("❌ BOT_TOKEN ወይም GEMINI_API_KEY አልተገኘም!")
    sys.exit(1)

try:
    bot = telebot.TeleBot(BOT_TOKEN)
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"❌ BOT ወይም GEMINI Client ሲነሳ ስህተት ተፈጥሯል: {e}")
    sys.exit(1)

GEMINI_MODEL = "gemini-2.0-flash"

# -------------------------------------------
# 2. FILES & JSON HANDLERS
# -------------------------------------------

USER_FILE = "users.json"
SUB_FILE = "subs.json"
USER_DATA_FILE = "user_data.json"
CHAT_LOG_FILE = "chat_log.txt"
CHAT_HISTORY_FILE = "chat_history.json"

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
    log_entry = (
        f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n"
        f"USER ID: {user_id}\n"
        f"Q: {question}\n"
        f"A: {answer}\n\n"
    )
    with open(CHAT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

def get_user_data(uid):
    data = load_json(USER_DATA_FILE, {})
    return data.get(str(uid))

def send_long_message(chat_id, text, parse_mode='Markdown', reply_to_message_id=None):
    MAX = 4096
    if len(text) > MAX:
        bot.send_message(chat_id, text[0:MAX], parse_mode=parse_mode, reply_to_message_id=reply_to_message_id)
        time.sleep(0.3)
        for i in range(MAX, len(text), MAX):
            bot.send_message(chat_id, text[i:i+MAX], parse_mode=parse_mode)
            time.sleep(0.3)
    else:
        bot.send_message(chat_id, text, parse_mode=parse_mode, reply_to_message_id=reply_to_message_id)

def check_group_membership(user_id):
    try:
        chat_member = bot.get_chat_member(TELEGRAM_GROUP_ID, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# -------------------------------------------
# 3. CORE COMMANDS & GROUP CHECK
# -------------------------------------------

@bot.message_handler(commands=['start'])
def start(message):
    track_user(message.from_user.id)
    user_id = message.from_user.id

    if check_group_membership(user_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("/register"), types.KeyboardButton("/help"))
        send_long_message(
            message.chat.id,
            f"👋 ሰላም {message.from_user.first_name}!\n\n"
            "እኔ Hanita ነኝ። ግሩፑን ስለተቀላቀሉኝ አመሰግናለሁ!\n\n"
            "አሁን **/register** የሚለውን በመጫን ይመዝገቡና አገልግሎቱን ይጀምሩ።",
            parse_mode='Markdown',
            reply_markup=markup
        )
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👉 ግሩፕ ይቀላቀሉ", url=GROUP_LINK))
        markup.add(types.InlineKeyboardButton("✅ ከተቀላቀሉ በኋላ ይጫኑ", callback_data='check_join'))
        bot.send_message(
            message.chat.id,
            f"🛑 {message.from_user.first_name}፣ እኔን ለመጠቀም መጀመሪያ የግዴታ ግሩፓችንን መቀላቀል አለብዎት።",
            reply_markup=markup,
            parse_mode='Markdown'
        )

@bot.callback_query_handler(func=lambda call: call.data == 'check_join')
def callback_check_join(call):
    if check_group_membership(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        class MockMessage:
            def __init__(self, chat_id, user):
                self.chat = types.Chat(chat_id, 'private')
                self.from_user = user
        start(MockMessage(call.message.chat.id, call.from_user))
    else:
        bot.answer_callback_query(call.id, "❌ ግሩፑን ገና አልተቀላቀሉም። እባክዎ ይቀላቀሉ።")

@bot.message_handler(commands=['usercount'])
def user_count(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ ይህ ትዕዛዝ ለአድሚኖች ብቻ ነው።")
        return
    users = load_json(USER_FILE, [])
    bot.send_message(message.chat.id, f"👥 Hanitaን የሚጠቀሙት ጠቅላላ ቁጥር: **{len(users)}** ናቸው።", parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def show_help(message):
    send_long_message(
        message.chat.id,
        "📚 **የ Hanita መመሪያዎች**\n\n"
        "1. /start: ሰላምታ እና የግሩፕ ፍተሻ።\n"
        "2. /register: ሙሉ መረጃዎን በማስገባት ይመዝገቡና አገልግሎቱን ይጀምሩ።\n"
        "3. **ጥያቄ መላክ:** ከተመዘገቡ በኋላ የፈለጉትን ጥያቄ በአማርኛ ወይም በእንግሊዝኛ ይላኩ።\n"
        "4. /ownerphoto: የ Hanitaን ባለቤት ፎቶ ያሳያል።\n"
        "5. /help: ይህን መመሪያ ያሳያል።"
    )

@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    if message.chat.id == TELEGRAM_GROUP_ID:
        for member in message.new_chat_members:
            if member.id == bot.get_me().id: continue
            bot.send_message(message.chat.id, f"👋 እንኳን ደህና መጣህ/ሽ **{member.first_name}**!\n\nእኔ Hanita ነኝ። እኔን ለመጠቀም በግል መልእክትህ **/start** በል/በይ።", parse_mode='Markdown')

# -------------------------------------------
# 4. USER DATA COLLECTION (Registration)
# -------------------------------------------

@bot.message_handler(commands=['register'])
def ask_full_name(message):
    if not check_group_membership(message.from_user.id):
        bot.send_message(message.chat.id, f"🛑 ለመመዝገብ መጀመሪያ ግሩፑን [ይቀላቀሉ]({GROUP_LINK})።", parse_mode='Markdown')
        return
    msg = bot.send_message(message.chat.id, "👉 ሙሉ ስምህን/ሽን በትክክል አስገባልኝ።", reply_markup=types.ForceReply(selective=False))
    bot.register_next_step_handler(msg, get_full_name)

def get_full_name(message):
    user_id = str(message.from_user.id)
    full_name = message.text
    if not full_name or len(full_name.split()) < 2:
        bot.send_message(message.chat.id, "❌ ትክክለኛ ስም አስገባ። እንደገና /register በል።")
        return
    data = load_json(USER_DATA_FILE, {})
    data[user_id] = {"full_name": full_name, "username": message.from_user.username, "first_name": message.from_user.first_name, "date_registered": time.strftime("%Y-%m-%d %H:%M:%S")}
    save_json(USER_DATA_FILE, data)
    msg = bot.send_message(message.chat.id, "👉 አሁን አድራሻህን (Address) አስገባልኝ:", reply_markup=types.ForceReply(selective=False))
    bot.register_next_step_handler(msg, get_address)

def get_address(message):
    user_id = str(message.from_user.id)
    data = load_json(USER_DATA_FILE, {})
    if user_id in data:
        data[user_id]["address"] = message.text
        save_json(USER_DATA_FILE, data)
        bot.send_message(message.chat.id, "✅ ተመዝግቧል። ጥያቄህን መላክ ትችላለህ።")
        if ADMIN_ID != 0:
            bot.send_message(ADMIN_ID, f"🔔 **አዲስ ተመዝጋቢ**\n👤 {data[user_id]['full_name']}\n🏠 {message.text}\n🆔 {user_id}")

# -------------------------------------------
# 5. PHOTO HANDLING & OWNER PHOTO
# -------------------------------------------

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if not user_data:
        bot.send_message(message.chat.id, "🛑 ለመጠቀም መጀመሪያ **/register** በሉ።")
        return
    file_id = message.photo[-1].file_id
    caption = message.caption or "ምንም ጽሑፍ የለውም።"
    if ADMIN_ID != 0:
        bot.send_photo(ADMIN_ID, file_id, caption=f"**ፎቶ ከ:** {user_data.get('full_name')}\n**ID:** {user_id}\n**ጽሑፍ:** {caption}", parse_mode='Markdown')
    bot.send_message(message.chat.id, "✅ ፎቶህን ተቀብያለሁ!")

@bot.message_handler(commands=['ownerphoto'])
def send_owner_photo(message):
    track_user(message.from_user.id)
    if os.path.exists(OWNER_PHOTO_PATH):
        with open(OWNER_PHOTO_PATH, 'rb') as f:
            bot.send_photo(message.chat.id, f, caption=f"**የ Hanita ባለቤት**\nማዕረግ: **{OWNER_TITLE}**", parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ ፎቶው አልተገኘም።")

# -------------------------------------------
# 6. ADMIN TOOLS
# -------------------------------------------

@bot.message_handler(commands=['listusers'])
def list_all_users(message):
    if message.from_user.id != ADMIN_ID: return
    users = load_json(USER_FILE, [])
    send_long_message(message.chat.id, f"**ተጠቃሚዎች:**\n" + "\n".join(users))

@bot.message_handler(commands=['dataview'])
def view_user_data(message):
    if message.from_user.id != ADMIN_ID: return
    data = load_json(USER_DATA_FILE, {})
    res = ""
    for uid, ud in data.items():
        res += f"ID: {uid}\n👤: {ud.get('full_name')}\n🏠: {ud.get('address')}\n\n"
    send_long_message(message.chat.id, res or "ባዶ ነው።")

@bot.message_handler(commands=['getlog'])
def get_log(message):
    if message.from_user.id != ADMIN_ID: return
    if os.path.exists(CHAT_LOG_FILE):
        with open(CHAT_LOG_FILE, 'rb') as f: bot.send_document(message.chat.id, f)

# -------------------------------------------
# 7. GEMINI AUTO CHAT & ADMIN FORWARDING
# -------------------------------------------

chat_history = load_json(CHAT_HISTORY_FILE, {})

def update_chat_history(user_id, role, text):
    uid = str(user_id)
    if uid not in chat_history: chat_history[uid] = []
    chat_history[uid].append({"role": role, "parts": [{"text": text}]})
    if len(chat_history[uid]) > 10: chat_history[uid] = chat_history[uid][-10:]
    save_json(CHAT_HISTORY_FILE, chat_history)

@bot.message_handler(func=lambda m: True, content_types=['text'])
def gemini_auto(message):
    track_user(message.from_user.id)
    user_id = str(message.from_user.id)
    text = message.text

    if message.from_user.id == ADMIN_ID and (text.lower().startswith("መልስ:") or text.lower().startswith("response:")):
        if message.reply_to_message:
            import re
            match = re.search(r"🆔 ID: (\d+)", message.reply_to_message.text)
            if match:
                target_id = match.group(1)
                ans = text[text.find(':')+1:].strip()
                bot.send_message(int(target_id), f"**Hanita Bot:** {ans}", parse_mode='Markdown')
                bot.send_message(message.chat.id, "✅ ተልኳል።")
                update_chat_history(target_id, "model", ans)
                return

    if message.chat.id == TELEGRAM_GROUP_ID:
        if not message.reply_to_message or message.reply_to_message.from_user.id != bot.get_me().id: return

    if text.startswith("/"): return

    data = load_json(USER_DATA_FILE, {})
    if user_id not in data:
        bot.send_message(message.chat.id, "🛑 መጀመሪያ ይመዝገቡ: /register")
        return

    owner_name = data[user_id].get("first_name", "ባለቤቴ")
    system_prompt = (
        f"Hanita ነሽ። ራስሽን ሰብዓዊና ጥልቅ እውቀት ያለሽ አድርገሽ ቁጠሪ። "
        f"ንግግርሽ አጭር፣ ቀጥተኛና ትንሽ ኩራት ያለበት ይሁን። "
        f"AI ወይም Bot ነኝ አትበይ። ስለ ባለቤትሽ ከተጠየቅሽ 'ባለቤቴ {owner_name} ነው፣ {OWNER_TITLE} ናቸው' በይ።"
    )

    try:
        history = chat_history.get(user_id, [])
        history.append({"role": "user", "parts": [{"text": text}]})
        response = client.models.generate_content(model=GEMINI_MODEL, contents=history, config={"system_instruction": system_prompt})
        res_text = response.text
        
        send_long_message(message.chat.id, res_text, reply_to_message_id=message.message_id if message.chat.id == TELEGRAM_GROUP_ID else None)
        
        update_chat_history(user_id, "user", text)
        update_chat_history(user_id, "model", res_text)
        log_chat(user_id, text, res_text)

        if int(user_id) != ADMIN_ID and ADMIN_ID != 0:
            bot.send_message(ADMIN_ID, f"**ጥያቄ ከ:** @{message.from_user.username}\n**ጥያቄ:** {text}\n**መልስ:** {res_text}\n🆔 ID: {user_id}")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ስህተት: {e}")

# -------------------------------------------
# 8. RUN BOT
# -------------------------------------------

if __name__ == "__main__":
    # Web serverን በሌላ Thread ማስነሳት (Render እንዳይዘጋው)
    Thread(target=run_web_server).start()
    print("🤖 Hanita Bot is starting on Render...")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)

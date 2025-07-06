import telebot
from telebot import types
import sqlite3
import time
import logging
import random
from datetime import datetime, timedelta
import uuid

from config import API_TOKEN , ADMINS , ADS_CHANNEL , FILES_CHANNEL

# تنظیم لاگ‌گیری
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)


bot = telebot.TeleBot(API_TOKEN)

# اتصال به دیتابیس
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()

# ساخت جدول‌ها
cursor.execute('''CREATE TABLE IF NOT EXISTS channels (channel TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS messages (msg_id INTEGER PRIMARY KEY, file_msg_id INTEGER, timestamp INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS stats (user_id INTEGER, timestamp INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS downloads (token TEXT, file_msg_id INTEGER, user_id INTEGER)''')

# ایجاد ایندکس برای بهینه‌سازی
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_file_msg_id ON messages(file_msg_id)''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_timestamp ON stats(timestamp)''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_token ON downloads(token)''')
conn.commit()

# مدیریت Rate Limit
def safe_api_call(func, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except telebot.apihelper.ApiTelegramException as e:
            if e.result_json['description'].startswith('Too Many Requests'):
                wait_time = random.uniform(1, 3)
                logging.warning(f"Rate limit hit, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
            else:
                raise
        except Exception as e:
            logging.error(f"Unexpected error in API call: {e}")
            raise
    raise Exception("Max retries reached for API call")

# دکمه‌های ادمین
@bot.message_handler(commands=['start'])
def start_handler(message):
    if message.from_user.id in ADMINS:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('➕ افزودن پیام تبلیغاتی', '📢 افزودن چنل جوین اجباری')
        markup.row('📂 مدیریت چنل‌ها', '📊 آمار')
        bot.send_message(message.chat.id, 'سلام ادمین عزیز، یکی از گزینه‌ها رو انتخاب کن:', reply_markup=markup)
    else:
        if message.text.startswith('/start dl'):
            handle_download_request(message)
        else:
            bot.send_message(message.chat.id, 'برای دریافت فایل، ابتدا روی لینک تبلیغاتی کلیک کنید.')

# افزودن چنل جوین اجباری
@bot.message_handler(func=lambda m: m.text == '📢 افزودن چنل جوین اجباری')
def add_channel_step(message):
    msg = bot.send_message(message.chat.id, 'لینک چنل را ارسال کن (مثال: @ChannelName):')
    bot.register_next_step_handler(msg, save_channel)

def save_channel(message):
    channel = message.text
    try:
        chat = safe_api_call(bot.get_chat, channel)
        member = safe_api_call(bot.get_chat_member, chat.id, bot.get_me().id)
        if member.status not in ['administrator', 'creator']:
            bot.send_message(message.chat.id, 'ربات در این چنل ادمین نیست. لطفاً ابتدا ربات را ادمین کنید.')
            return
        cursor.execute("INSERT INTO channels VALUES (?)", (channel,))
        conn.commit()
        bot.send_message(message.chat.id, f'چنل {channel} با موفقیت اضافه شد.')
        logging.info(f"Channel {channel} added by admin {message.from_user.id}")
    except telebot.apihelper.ApiTelegramException as e:
        bot.send_message(message.chat.id, f'خطا در افزودن چنل: {str(e)}. لطفاً لینک را بررسی کنید.')
        logging.error(f"Error adding channel {channel}: {e}")
    except Exception as e:
        bot.send_message(message.chat.id, 'خطای ناشناخته‌ای رخ داد. لطفاً دوباره تلاش کنید.')
        logging.error(f"Unexpected error adding channel: {e}")

# مدیریت چنل‌ها
@bot.message_handler(func=lambda m: m.text == '📂 مدیریت چنل‌ها')
def manage_channels(message):
    try:
        cursor.execute("SELECT * FROM channels")
        channels = cursor.fetchall()
        if not channels:
            bot.send_message(message.chat.id, 'هیچ چنلی ثبت نشده است.')
            return
        for ch in channels:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('❌ حذف', callback_data=f'delch|{ch[0]}'))
            bot.send_message(message.chat.id, ch[0], reply_markup=markup)
    except Exception as e:
        bot.send_message(message.chat.id, 'خطا در بارگذاری چنل‌ها.')
        logging.error(f"Error managing channels: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('delch'))
def delete_channel(call):
    ch_link = call.data.split('|')[1]
    try:
        cursor.execute("DELETE FROM channels WHERE channel=?", (ch_link,))
        conn.commit()
        bot.edit_message_text(f'چنل {ch_link} حذف شد.', call.message.chat.id, call.message.message_id)
        logging.info(f"Channel {ch_link} deleted by admin {call.from_user.id}")
    except Exception as e:
        bot.edit_message_text('خطا در حذف چنل.', call.message.chat.id, call.message.message_id)
        logging.error(f"Error deleting channel {ch_link}: {e}")

# افزودن پیام تبلیغاتی
@bot.message_handler(func=lambda m: m.text == '➕ افزودن پیام تبلیغاتی')
def add_ad_step1(message):
    msg = bot.send_message(message.chat.id, 'لطفاً متن تبلیغاتی را ارسال کنید:')
    bot.register_next_step_handler(msg, get_file_step)

def get_file_step(message):
    ad_text = message.text
    msg = bot.send_message(message.chat.id, 'اکنون فایل مرتبط را ارسال کنید (فقط فایل پشتیبانی می‌شود):')
    bot.register_next_step_handler(msg, lambda m: finish_ad_creation(m, ad_text))

def finish_ad_creation(message, ad_text):
    try:
        # بررسی نوع پیام (فقط فایل)
        if not (message.document or message.photo or message.video or message.audio):
            bot.send_message(message.chat.id, 'لطفاً یک فایل (سند، عکس، ویدئو یا صوت) ارسال کنید.')
            return

        # ارسال فایل به چنل فایل‌ها
        file_msg = safe_api_call(bot.forward_message, FILES_CHANNEL, message.chat.id, message.message_id)
        
        # ذخیره در دیتابیس
        cursor.execute("INSERT INTO messages (file_msg_id, timestamp) VALUES (?, ?)", 
                      (file_msg.message_id, int(time.time())))
        conn.commit()

        # ایجاد توکن برای دانلود
        token = str(uuid.uuid4())
        cursor.execute("INSERT INTO downloads (token, file_msg_id, user_id) VALUES (?, ?, ?)",
                      (token, file_msg.message_id, message.from_user.id))
        conn.commit()

        # دکمه دانلود
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('⬇️ دانلود', url=f"https://t.me/{bot.get_me().username}?start=dl{token}"))
        
        # ارسال تبلیغ به چنل تبلیغاتی
        safe_api_call(bot.send_message, ADS_CHANNEL, ad_text, reply_markup=markup)
        bot.send_message(message.chat.id, 'پیام تبلیغاتی با موفقیت ارسال شد.')
        logging.info(f"Ad created with file_msg_id {file_msg.message_id} by admin {message.from_user.id}")
    except telebot.apihelper.ApiTelegramException as e:
        bot.send_message(message.chat.id, f'خطا در ارسال تبلیغ: {str(e)}. لطفاً دوباره تلاش کنید.')
        logging.error(f"Error creating ad: {e}")
    except Exception as e:
        bot.send_message(message.chat.id, 'خطای ناشناخته‌ای رخ داد.')
        logging.error(f"Unexpected error creating ad: {e}")

# هندل دکمه دانلود برای کاربران
def handle_download_request(message):
    try:
        token = message.text.split('dl')[1]
        # بررسی توکن
        cursor.execute("SELECT file_msg_id FROM downloads WHERE token=?", (token,))
        result = cursor.fetchone()
        if not result:
            bot.send_message(message.chat.id, 'لینک دانلود نامعتبر است.')
            return
        file_id = result[0]

        # بررسی عضویت در کانال‌ها
        cursor.execute("SELECT channel FROM channels")
        channels = cursor.fetchall()
        not_joined = []
        for ch in channels:
            try:
                member = safe_api_call(bot.get_chat_member, ch[0], message.from_user.id)
                if member.status not in ['member', 'administrator', 'creator']:
                    not_joined.append(ch[0])
            except telebot.apihelper.ApiTelegramException as e:
                not_joined.append(ch[0])
                logging.error(f"Error checking membership for {ch[0]}: {e}")

        if not_joined:
            markup = types.InlineKeyboardMarkup()
            for ch in not_joined:
                markup.add(types.InlineKeyboardButton(f'عضویت در {ch}', url=f'https://t.me/{ch.replace("@", "")}'))
            markup.add(types.InlineKeyboardButton('✅ تایید عضویت', callback_data=f'checkjoin|{token}'))
            bot.send_message(message.chat.id, 'لطفاً در چنل‌های زیر عضو شوید و سپس تایید کنید:', reply_markup=markup)
        else:
            send_file_to_user(message.chat.id, file_id, token)
    except Exception as e:
        bot.send_message(message.chat.id, 'خطا در پردازش درخواست دانلود.')
        logging.error(f"Error handling download request: {e}")

# بررسی عضویت و ارسال فایل به کاربر
@bot.callback_query_handler(func=lambda call: call.data.startswith('checkjoin'))
def check_join(call):
    try:
        token = call.data.split('|')[1]
        # بررسی توکن
        cursor.execute("SELECT file_msg_id FROM downloads WHERE token=?", (token,))
        result = cursor.fetchone()
        if not result:
            bot.answer_callback_query(call.id, 'لینک دانلود نامعتبر است.')
            return
        file_id = result[0]

        # بررسی عضویت
        cursor.execute("SELECT channel FROM channels")
        channels = cursor.fetchall()
        for ch in channels:
            try:
                member = safe_api_call(bot.get_chat_member, ch[0], call.from_user.id)
                if member.status not in ['member', 'administrator', 'creator']:
                    bot.answer_callback_query(call.id, 'شما هنوز در همه چنل‌ها عضو نشده‌اید.')
                    return
            except telebot.apihelper.ApiTelegramException as e:
                bot.answer_callback_query(call.id, 'خطا در بررسی عضویت.')
                logging.error(f"Error checking membership for {ch[0]}: {e}")
                return

        bot.answer_callback_query(call.id, 'عضویت تایید شد.')
        send_file_to_user(call.from_user.id, file_id, token)
    except Exception as e:
        bot.answer_callback_query(call.id, 'خطا در پردازش درخواست.')
        logging.error(f"Error in check_join: {e}")

# ارسال فایل به کاربر
def send_file_to_user(user_id, file_id, token):
    try:
        # بررسی وجود فایل در دیتابیس
        cursor.execute("SELECT file_msg_id FROM messages WHERE file_msg_id=?", (file_id,))
        if not cursor.fetchone():
            bot.send_message(user_id, 'فایل مورد نظر یافت نشد.')
            return

        # ارسال فایل
        msg = safe_api_call(bot.forward_message, user_id, FILES_CHANNEL, file_id)
        bot.send_message(user_id, 'فایل برای شما ارسال شد. لطفاً آن را در Saved Messages ذخیره کنید. این پیام پس از 30 ثانیه حذف خواهد شد.')

        # ثبت آمار
        cursor.execute("INSERT INTO stats (user_id, timestamp) VALUES (?, ?)", (user_id, int(time.time())))
        conn.commit()

        # حذف پیام پس از 30 ثانیه
        time.sleep(30)
        try:
            safe_api_call(bot.delete_message, user_id, msg.message_id)
            logging.info(f"Message {msg.message_id} deleted for user {user_id} after 30 seconds")
        except telebot.apihelper.ApiTelegramException as e:
            logging.error(f"Error deleting message {msg.message_id} for user {user_id}: {e}")
            bot.send_message(user_id, 'خطا در حذف پیام. لطفاً پیام را به صورت دستی حذف کنید.')

        logging.info(f"File {file_id} sent to user {user_id}")
    except telebot.apihelper.ApiTelegramException as e:
        bot.send_message(user_id, f'خطا در ارسال فایل: {str(e)}. لطفاً دوباره تلاش کنید.')
        logging.error(f"Error sending file to user {user_id}: {e}")
    except Exception as e:
        bot.send_message(user_id, 'خطای ناشناخته‌ای رخ داد. لطفاً با پشتیبانی تماس بگیرید.')
        logging.error(f"Unexpected error sending file to user {user_id}: {e}")

# آمار
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats_handler(message):
    try:
        now = int(time.time())
        cursor.execute("SELECT COUNT(*) FROM stats WHERE timestamp > ?", (now - 86400,))
        today = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM stats WHERE timestamp > ?", (now - 604800,))
        week = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM stats WHERE timestamp > ?", (now - 2592000,))
        month = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM stats")
        total = cursor.fetchone()[0]

        # محاسبه کاربران فعال (به صورت ساده‌تر)
        active = total  # برای جلوگیری از بررسی سنگین عضویت، فرض می‌کنیم همه کاربران فعال هستند
        bot.send_message(message.chat.id, 
                        f'📊 آمار:\n\n'
                        f'دانلود امروز: {today}\n'
                        f'دانلود هفته: {week}\n'
                        f'دانلود ماه: {month}\n\n'
                        f'کاربران فعال: {active}\n'
                        f'کل کاربران: {total}')
        logging.info(f"Stats requested by admin {message.from_user.id}")
    except Exception as e:
        bot.send_message(message.chat.id, 'خطا در بارگذاری آمار.')
        logging.error(f"Error in stats_handler: {e}")

# اجرای ربات
if __name__ == '__main__':
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logging.error(f"Bot polling error: {e}")
        time.sleep(5)
        bot.polling(none_stop=True)
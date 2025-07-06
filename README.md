# source-uploader-bot
ربات تلگرام با قابلیت دریافت فایل فقط پس از عضویت در کانال 

Telegram bot with join-to-download feature



📦 Telegram File Downloader Bot | ربات دانلود فایل تلگرام

> 🇬🇧 A Telegram bot that sends downloadable files only to users who join specified channels. Includes an admin panel, auto-check join, secure access, and download statistics.  
> 🇮🇷 ربات تلگرام برای دریافت فایل فقط پس از عضویت در کانال‌های مشخص با پنل مدیریتی، بررسی عضویت خودکار و آمار دقیق دانلود.

---

🌟 Features | امکانات

- 🎛️ Admin panel for managing channels and ads  
  🎛️ پنل مدیریت برای افزودن چنل و پیام تبلیغاتی  
- 🔒 Force-join required channels  
  🔒 جوین اجباری قبل از دریافت فایل  
- ⬇️ Download button with token verification  
  ⬇️ دکمه دانلود با توکن اختصاصی  
- 📂 Hidden file storage channel  
  📂 ذخیره فایل‌ها در چنل مخفی  
- 📊 Statistics for downloads (daily, weekly, monthly)  
  📊 آمار دقیق دانلودها (روزانه، هفتگی، ماهانه)  
- 🧹 Auto-delete sent file after 30 seconds  
  🧹 حذف خودکار فایل پس از ارسال (۳۰ ثانیه بعد)

---

⚙️ Setup & Run | نصب و اجرا

📝 1. Clone the repo | کلون کردن مخزن
bash
git clone https://github.com/the-mr-amir/telegram-downloader-bot
cd telegram-downloader-bot


 📦 2. Install requirements | نصب وابستگی‌ها
bash
pip install -r requirements.txt


🛠️ 3. Configure your bot | تنظیم فایل config.py
Edit (config.py):
python
API_TOKEN = 'توکن ربات خود را اینجا قرار دهید'
ADMINS = [123456789]  # آیدی عددی ادمین‌ها
ADS_CHANNEL = '@your_ads_channel'  # چنل نمایش تبلیغات
FILES_CHANNEL = -1001234567890     # چنل مخفی ذخیره فایل


🚀 4. Run the bot | اجرای ربات
bash
python bot.py


---

🗂️ Database Structure | ساختار دیتابیس

- channels – Channels for force-join | کانال‌های جوین اجباری  
- messages – Sent files data | پیام‌ها و فایل‌های ارسال‌شده  
- downloads – Download tokens | توکن‌های دریافت  
- stats – Download history | آمار دانلود کاربران  

---

👤 Developer | توسعه‌دهنده

- Telegram: [ @MrAmir_ID ](https://t.me/@MrAmir_ID)  
- Channel: [@MrBot_CH](https://t.me/MrBot_CH)  

---

🪪 License | مجوز استفاده

This project is licensed under the MIT License.  
استفاده از این پروژه با مجوز MIT آزاد است.

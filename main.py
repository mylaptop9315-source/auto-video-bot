"""
Auto Telegram -> Text -> Audio -> Video Bot (Render + Python 3.13 fix)
"""

import os
import uuid
import threading
import time
import asyncio
import requests
from flask import Flask
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- Configuration ---
TELEGRAM_TOKEN = "8269322609:AAElFFE5YJ-ehl47CXq0JpjYug-zSpiO7NY"

TMP_DIR = "tmp_files"
os.makedirs(TMP_DIR, exist_ok=True)

# --- Telegram bot handler ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    await context.bot.send_message(chat_id=chat_id, text="🎬 Received — creating your video... Please wait 1–2 min.")

    uid = uuid.uuid4().hex
    audio_path = os.path.join(TMP_DIR, f"{uid}.mp3")
    bg_path = os.path.join(TMP_DIR, f"{uid}.jpg")
    video_path = os.path.join(TMP_DIR, f"{uid}.mp4")

    try:
        tts = gTTS(text=text, lang='hi')
        tts.save(audio_path)

        resp = requests.get("https://picsum.photos/1280/720", timeout=15)
        with open(bg_path, 'wb') as f:
            f.write(resp.content)

        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration

        clip = ImageClip(bg_path).set_duration(duration).set_fps(24).set_audio(audio_clip)
        clip.write_videofile(video_path, codec='libx264', audio_codec='aac', verbose=False, logger=None)

        with open(video_path, 'rb') as vf:
            await context.bot.send_video(chat_id=chat_id, video=vf)

        await context.bot.send_message(chat_id=chat_id, text="✅ Video ready — sent above!")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error: {e}")
        print("Error:", e)

    finally:
        for p in (audio_path, bg_path, video_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass


def run_telegram_bot():
    """Fix for Python 3.13: create and set event loop manually"""
    asyncio.set_event_loop(asyncio.new_event_loop())
    tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    tg_app.run_polling()


# --- Flask server (Render detection) ---
web_app = Flask("auto_video_bot")

@web_app.route('/')
def index():
    return "✅ Auto Video Bot is running on Render! Send a message on Telegram."


if __name__ == '__main__':
    thr = threading.Thread(target=run_telegram_bot, daemon=True)
    thr.start()

    def reporter():
        while True:
            print("🤖 Bot thread running?", thr.is_alive())
            time.sleep(30)

    rep = threading.Thread(target=reporter, daemon=True)
    rep.start()

    port = int(os.environ.get('PORT', 5000))
    web_app.run(host='0.0.0.0', port=port)

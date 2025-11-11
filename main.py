"""
Auto Telegram -> Text -> Audio -> Video Bot
(For Render deployment, beginner friendly)

✅ Features:
- Takes Telegram text messages
- Converts to audio (gTTS)
- Generates a short video with random background (moviepy)
- Sends back video to user
"""

import os
import uuid
import threading
import time
import requests
from flask import Flask
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- Configuration ---
# Fixed Telegram Bot Token (your token inserted directly)
TELEGRAM_TOKEN = "8269322609:AAElFFE5YJ-ehl47CXq0JpjYug-zSpiO7NY"

# Temporary folder for files
TMP_DIR = "tmp_files"
os.makedirs(TMP_DIR, exist_ok=True)

# --- Telegram bot ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming Telegram messages: converts text -> speech -> video."""
    text = update.message.text
    chat_id = update.effective_chat.id

    await context.bot.send_message(chat_id=chat_id, text="🎬 Received — creating your video... Please wait 1–2 min.")

    # Unique filenames
    uid = uuid.uuid4().hex
    audio_path = os.path.join(TMP_DIR, f"{uid}.mp3")
    bg_path = os.path.join(TMP_DIR, f"{uid}.jpg")
    video_path = os.path.join(TMP_DIR, f"{uid}.mp4")

    try:
        # 1️⃣ Text → Speech
        tts = gTTS(text=text, lang='hi')
        tts.save(audio_path)

        # 2️⃣ Download background image
        resp = requests.get("https://picsum.photos/1280/720", timeout=15)
        with open(bg_path, 'wb') as f:
            f.write(resp.content)

        # 3️⃣ Combine audio + image → video
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration

        clip = ImageClip(bg_path).set_duration(duration).set_fps(24).set_audio(audio_clip)
        clip.write_videofile(video_path, codec='libx264', audio_codec='aac', verbose=False, logger=None)

        # 4️⃣ Send video back
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
    """Run Telegram bot continuously in background."""
    tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    tg_app.run_polling()


# --- Flask server (so Render detects a running service) ---
web_app = Flask("auto_video_bot")

@web_app.route('/')
def index():
    return "✅ Auto Video Bot is live! Send me a message on Telegram."


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

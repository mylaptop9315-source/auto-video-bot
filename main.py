"""
Telegram -> Text -> gTTS -> Video -> Send back (Render-ready)

How to use:
1) Create a Telegram bot via @BotFather and get TELEGRAM_TOKEN.
2) Add TELEGRAM_TOKEN to Render environment variables.
3) Ensure your repo has a requirements.txt with these lines:
   flask
   requests
   python-telegram-bot==20.3
   gTTS
   moviepy

4) Deploy to Render as a Web Service (Start command: python main.py).

What this script does:
- Starts a small Flask webserver so Render detects an open port.
- Starts the Telegram bot in a background thread (polling).
- On receiving a text message, it converts text->speech (gTTS), downloads a random background image,
  makes a short mp4 (moviepy) and sends it back to the user in Telegram.

Notes & limits:
- This is a minimal, beginner-friendly version. It is not production hardened.
- Large scripts may produce large videos — Telegram has file size limits.
- If you later want automatic YouTube upload, we can add YouTube Data API code.
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
TELEGRAM_TOKEN = os.environ.get("8269322609:AAElFFE5YJ-ehl47CXq0JpjYug-zSpiO7NY")
if not TELEGRAM_TOKEN:
    raise RuntimeError("❌ TELEGRAM_TOKEN not found! Please set it in Render Environment Variables.")

# Temporary folder
TMP_DIR = "tmp_files"
os.makedirs(TMP_DIR, exist_ok=True)

# --- Telegram bot (runs in background thread) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages: creates audio+video and replies with the video file."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Acknowledge receipt
    await context.bot.send_message(chat_id=chat_id, text="🎬 Received — making your video now. Please wait...")

    # Unique filenames
    uid = uuid.uuid4().hex
    audio_path = os.path.join(TMP_DIR, f"{uid}.mp3")
    bg_path = os.path.join(TMP_DIR, f"{uid}.jpg")
    video_path = os.path.join(TMP_DIR, f"{uid}.mp4")

    try:
        # 1) Text -> speech
        tts = gTTS(text=text, lang='hi')  # change lang if needed
        tts.save(audio_path)

        # 2) Download a random background image (Picsum)
        #    Using a quick download to produce a background image file
        resp = requests.get("https://picsum.photos/1280/720", timeout=15)
        if resp.status_code == 200:
            with open(bg_path, 'wb') as f:
                f.write(resp.content)
        else:
            # fallback: create a tiny blank image if download fails
            # moviepy can create a color clip, but keep it simple: raise
            raise RuntimeError("Failed to download background image")

        # 3) Create video: image (duration = audio duration) + audio
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration

        # ImageClip expects a filepath
        clip = ImageClip(bg_path).set_duration(duration)
        clip = clip.set_fps(24)
        clip = clip.set_audio(audio_clip)

        # Write video file (may take time depending on duration)
        clip.write_videofile(video_path, codec='libx264', audio_codec='aac', verbose=False, logger=None)

        # 4) Send video back on Telegram
        with open(video_path, 'rb') as vf:
            await context.bot.send_video(chat_id=chat_id, video=vf)

        await context.bot.send_message(chat_id=chat_id, text="✅ Video ready — sent above!")

    except Exception as e:
        # Send an error message to user and log
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error while creating video: {e}")
        except Exception:
            pass
        print("Error in handle_message:", e)

    finally:
        # Cleanup (best-effort)
        for p in (audio_path, bg_path, video_path):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


def run_telegram_bot():
    """Start the telegram polling bot (blocking) — we run in a thread."""
    tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # run_polling blocks, so this function will block unless run in a thread
    tg_app.run_polling()


# --- Web server (so Render detects a bound port) ---
web_app = Flask("auto_video_bot")

@web_app.route('/')
def index():
    return "✅ Auto Video Bot is running. Send me a message on Telegram to create videos."


if __name__ == '__main__':
    # Start Telegram bot in background thread
    thr = threading.Thread(target=run_telegram_bot, daemon=True)
    thr.start()

    # Simple background reporter (optional)
    def reporter():
        while True:
            print("🤖 Background: Telegram bot thread alive?", thr.is_alive())
            time.sleep(30)

    rep = threading.Thread(target=reporter, daemon=True)
    rep.start()

    # Start Flask web server — Render provides PORT via env
    port = int(os.environ.get('PORT', 5000))
    web_app.run(host='0.0.0.0', port=port)

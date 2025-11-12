import os
import uuid
import asyncio
import threading
import requests
from flask import Flask
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- Config ---
TELEGRAM_TOKEN = "8269322609:AAElFFE5YJ-ehl47CXq0JpjYug-zSpiO7NY"
TMP_DIR = "tmp_files"
os.makedirs(TMP_DIR, exist_ok=True)

# --- Flask app ---
web_app = Flask("auto_video_bot")

@web_app.route('/')
def index():
    return "✅ Auto Video Bot is live and connected to Telegram!"

# --- Telegram logic ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="🎬 Received — creating your video...")

    uid = uuid.uuid4().hex
    audio_path = os.path.join(TMP_DIR, f"{uid}.mp3")
    bg_path = os.path.join(TMP_DIR, f"{uid}.jpg")
    video_path = os.path.join(TMP_DIR, f"{uid}.mp4")

    try:
        # Text → Speech
        tts = gTTS(text=text, lang='hi')
        tts.save(audio_path)

        # Random background
        r = requests.get("https://picsum.photos/1280/720", timeout=10)
        with open(bg_path, "wb") as f:
            f.write(r.content)

        # Combine image + audio → video
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        clip = ImageClip(bg_path).set_duration(duration).set_fps(24).set_audio(audio_clip)
        clip.write_videofile(video_path, codec='libx264', audio_codec='aac', verbose=False, logger=None)

        # Send video back
        with open(video_path, 'rb') as vf:
            await context.bot.send_video(chat_id=chat_id, video=vf)
        await context.bot.send_message(chat_id=chat_id, text="✅ Done! Your video is ready.")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error: {e}")
        print("Error:", e)

    finally:
        for p in (audio_path, bg_path, video_path):
            if os.path.exists(p):
                os.remove(p)

async def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Telegram bot started polling...")
    await app.run_polling()

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    web_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Run Flask in background thread
    threading.Thread(target=run_flask, daemon=True).start()

    # Run Telegram bot in main asyncio loop
    asyncio.run(run_bot())

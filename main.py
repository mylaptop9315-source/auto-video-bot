import os
import uuid
import requests
from flask import Flask, request
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip
from telegram import Bot, Update

# Google API imports
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# --- CONFIG ---
TELEGRAM_TOKEN = "8269322609:AAElFFE5YJ-ehl47CXq0JpjYug-zSpiO7NY"
WEBHOOK_URL = "https://auto-video-bot.onrender.com/webhook"
TMP_DIR = "tmp_files"
os.makedirs(TMP_DIR, exist_ok=True)

bot = Bot(token=TELEGRAM_TOKEN)
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

app = Flask(__name__)

# --- Helper: Authenticate YouTube ---
def get_youtube_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

# --- Flask Routes ---
@app.route('/')
def index():
    return "✅ Auto Video Bot (with YouTube Upload) Running!"

@app.route('/setwebhook')
def set_webhook():
    s = bot.set_webhook(WEBHOOK_URL)
    return f"Webhook set: {s}"

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    chat_id = update.effective_chat.id
    text = update.message.text if update.message else ""

    if not text:
        return "no message", 200

    try:
        bot.send_message(chat_id=chat_id, text="🎬 Received! Creating video...")

        # Unique IDs
        uid = uuid.uuid4().hex
        audio_path = os.path.join(TMP_DIR, f"{uid}.mp3")
        image_path = os.path.join(TMP_DIR, f"{uid}.jpg")
        video_path = os.path.join(TMP_DIR, f"{uid}.mp4")

        # Text → Audio
        tts = gTTS(text=text, lang="hi")
        tts.save(audio_path)

        # Background Image
        img = requests.get("https://picsum.photos/1280/720", timeout=10)
        with open(image_path, "wb") as f:
            f.write(img.content)

        # Make Video
        audio = AudioFileClip(audio_path)
        clip = ImageClip(image_path).set_duration(audio.duration).set_fps(24).set_audio(audio)
        clip.write_videofile(video_path, codec="libx264", audio_codec="aac", verbose=False, logger=None)

        # Send to Telegram
        with open(video_path, "rb") as vf:
            bot.send_video(chat_id=chat_id, video=vf)

        bot.send_message(chat_id=chat_id, text="✅ Video ready! Uploading to YouTube...")

        # Upload to YouTube
        youtube = get_youtube_service()
        request_body = {
            "snippet": {
                "categoryId": "22",
                "title": f"Auto Generated Video - {uid[:6]}",
                "description": f"Video created automatically from Telegram text: {text[:80]}...",
                "tags": ["auto", "bot", "gtts", "python"]
            },
            "status": {
                "privacyStatus": "public"
            }
        }

        upload = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=video_path
        )
        upload_response = upload.execute()
        video_id = upload_response.get("id")

        yt_link = f"https://www.youtube.com/watch?v={video_id}"
        bot.send_message(chat_id=chat_id, text=f"🚀 Uploaded to YouTube!\n{yt_link}")

    except Exception as e:
        bot.send_message(chat_id=chat_id, text=f"⚠️ Error: {e}")
        print("Error:", e)
    finally:
        for p in [audio_path, image_path, video_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

import time
import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running on Render!"

def background_task():
    while True:
        print("🤖 Bot is running on Render...")
        time.sleep(10)

if __name__ == '__main__':
    print("✅ Bot is starting...")

    # Background task start karo
    import threading
    threading.Thread(target=background_task, daemon=True).start()

    # Flask web server start karo (Render ko port milega)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

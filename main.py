import time
import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running on Render!"

if __name__ == '__main__':
    print("✅ Bot is starting...")
    while True:
        print("🤖 Bot is running on Render...")
        time.sleep(10)

    # नीचे की 2 lines से Render को port मिलेगा
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

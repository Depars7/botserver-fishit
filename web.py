# web.py
import os
from flask import Flask

app = Flask(__name__)

# Route untuk Health Check Koyeb
@app.route('/')
def home():
    """Mengembalikan 200 OK untuk health check."""
    return "Discord Bot is Running!", 200

def start_web_server():
    """Mulai server Flask di port yang ditentukan oleh Koyeb."""
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting web server on port {port}")
    # Gunakan debug=False dan threaded=False agar lebih stabil di production
    app.run(host='0.0.0.0', port=port, debug=False)

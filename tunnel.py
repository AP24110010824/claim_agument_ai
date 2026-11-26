import os
import sys
import time
import threading
from dotenv import load_dotenv
from pyngrok import ngrok
from waitress import serve
from app import app

load_dotenv()
PORT = int(os.getenv("PORT", 5050))
AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")

def start_waitress():
    """Runs the Waitress server in a background thread."""
    serve(app, host="127.0.0.1", port=PORT, threads=8, _quiet=True)

def deploy():
    print("=" * 65)
    print("🌐 CLAIM-AUGMENT AI: PUBLIC DEPLOYMENT GATEWAY (NGROK)")
    print("=" * 65)

    if not AUTH_TOKEN or AUTH_TOKEN == "your_ngrok_auth_token_here":
        print("❌ ERROR: NGROK_AUTH_TOKEN is missing or unconfigured in .env!")
        print("   1. Get your free token at: https://dashboard.ngrok.com/get-started/your-authtoken")
        print("   2. Add to .env: NGROK_AUTH_TOKEN=your_token_here")
        sys.exit(1)

    # Configure Ngrok
    ngrok.set_auth_token(AUTH_TOKEN)

    # Start local multi-threaded Waitress server
    server_thread = threading.Thread(target=start_waitress, daemon=True)
    server_thread.start()
    print(f"✅ Local Waitress WSGI Server running on http://127.0.0.1:{PORT}")

    # Establish encrypted HTTPS tunnel to port 5050
    tunnel = ngrok.connect(PORT, "http")
    public_url = tunnel.public_url

    if public_url.startswith("http://"):
        public_url = public_url.replace("http://", "https://")

    print("\n" + "🎉" * 25)
    print(f"🌍 LIVE PUBLIC HTTPS URL: {public_url}")
    print("🎉" * 25)
    print("\n📱 You can now open this link on your smartphone or share it with anyone!")
    print("   Press Ctrl + C in this terminal to terminate the deployment.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down deployment gateway...")
        ngrok.disconnect(public_url)
        ngrok.kill()
        print("👋 Tunnel closed.")

if __name__ == "__main__":
    deploy()
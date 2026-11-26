import os
from dotenv import load_dotenv
from waitress import serve
from app import app

load_dotenv()
PORT = int(os.getenv("PORT", 5050))

def start_server():
    print("=" * 65)
    print("🚀 CLAIM-AUGMENT AI: PRODUCTION WSGI SERVER (WAITRESS)")
    print(f"   Binding: http://0.0.0.0:{PORT}")
    print(f"   Workers: 8 Multi-threaded Concurrent Workers")
    print("=" * 65)
    serve(app, host="0.0.0.0", port=PORT, threads=8)

if __name__ == "__main__":
    start_server()
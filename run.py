"""Start the local dashboard: python run.py"""
from __future__ import annotations

import os
import threading
import webbrowser

from dotenv import load_dotenv
from waitress import serve

from app import ROOT, create_app


def main():
    load_dotenv(ROOT / ".env")
    app = create_app()
    app.extensions["bank_service"].customers()  # Fail clearly on a structural backend configuration problem.
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8501"))
    address = f"http://127.0.0.1:{port}"
    print(f"Relationship Intelligence is ready at {address}")
    if os.getenv("OPEN_BROWSER", "true").lower() == "true":
        opener = threading.Timer(1, webbrowser.open, args=[address])
        opener.daemon = True
        opener.start()
    serve(app, host=host, port=port, threads=8, channel_timeout=180, ident="RelationshipIntelligence")


if __name__ == "__main__":
    main()

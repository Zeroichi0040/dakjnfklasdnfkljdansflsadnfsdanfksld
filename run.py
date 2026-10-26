"""Simple local launcher using Waitress, not Flask's development server."""

import argparse
import json
import os
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def open_browser(url):
    for _ in range(60):
        try:
            with urllib.request.urlopen(url + "/health/live", timeout=1) as response:
                if json.load(response).get("app") == "flask-fullstack-framework":
                    webbrowser.open(url)
                    return
        except (OSError, ValueError):
            pass
        time.sleep(0.2)


def main():
    parser = argparse.ArgumentParser(description="Open the Flask application framework.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5000")))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port between 1024 and 65535.")
    try:
        from waitress import create_server  # noqa: PLC0415

        from backend import create_app  # noqa: PLC0415
        from backend.framework.readiness import assert_ready
    except ImportError:
        print("Install dependencies first: run SETUP_WINDOWS.bat or bash setup.sh")
        return 1
    app = create_app()
    try:
        with app.app_context():
            assert_ready()
    except Exception:
        print("Database is not ready. Run SETUP_WINDOWS.bat, bash setup.sh, or python manage.py db upgrade.")
        return 1
    try:
        server = create_server(app, host=args.host, port=args.port, threads=4, max_request_body_size=3 * 1024 * 1024)
    except OSError:
        print("That address or port is unavailable. Try: python run.py --port 5001")
        return 1
    url = f"http://127.0.0.1:{args.port}"
    print(f"\n{app.config['APP_NAME']} is starting: {url}")
    print("Create your account in the browser. No shared demo password is installed.")
    print("Frontend: frontend/ | Python features: backend/modules/ | Models: database/models/")
    print("Keep this terminal open. Stop with Ctrl+C; restart after changing Python files.\n")
    if not args.no_browser:
        threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    try:
        server.run()
    finally:
        server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

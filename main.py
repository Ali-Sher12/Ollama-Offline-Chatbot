#!/usr/bin/env python3
"""
Ollama Desktop Chatbot Launcher
Launches the FastAPI backend and presents a native desktop window (or browser app).
"""

import sys
import os
import time
import socket
import threading
import webbrowser
import uvicorn

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.server import app

def find_available_port(start_port: int = 8080) -> int:
    """Find an available TCP port."""
    port = start_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
        port += 1
    return start_port

def run_server(port: int):
    """Run Uvicorn server."""
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

def main():
    port = find_available_port(8080)
    url = f"http://127.0.0.1:{port}"

    print(f"\n=======================================================")
    print(f"  Starting Ollama Desktop Chatbot on {url}")
    print(f"=======================================================\n")

    # Start FastAPI server in a background thread
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for server to bind
    time.sleep(1.2)

    # Check for headless flag
    if "--headless" in sys.argv or "--server" in sys.argv:
        print(f"Running in server mode. Access the UI at: {url}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down server.")
            sys.exit(0)

    # Attempt to open native desktop window with pywebview
    opened_webview = False
    try:
        import webview
        print("Launching native desktop window via pywebview...")
        window = webview.create_window(
            title="Ollama Desktop Chatbot",
            url=url,
            width=1240,
            height=820,
            min_size=(900, 600),
            background_color="#070a12"
        )
        webview.start()
        opened_webview = True
    except Exception as e:
        print(f"Desktop webview window unavailable ({e}). Falling back to default browser...")

    if not opened_webview:
        webbrowser.open(url)
        print(f"UI opened in browser at {url}. Press Ctrl+C in terminal to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down.")
            sys.exit(0)

if __name__ == "__main__":
    main()

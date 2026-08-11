"""Filebede - Telegram File Downloader Bot

A Telegram bot that downloads files from URLs and sends them to users.
Supports Local Bot API Server for large files.

Features:
- Stream-based downloading (no RAM overload)
- Resume support with HTTP Range
- Automatic filename detection
- SSRF protection
- Retry with exponential backoff

Installation:
    pip install -r requirements.txt

Configuration:
    cp .env.example .env
    # Edit .env with your settings

Running:
    python bot.py

Local Bot API Server:
    1. Download from https://github.com/tdlib/telegram-bot-api
    2. Build and run: telegram-bot-api --api_id=YOUR_ID --api_hash=YOUR_HASH --local -p 8081
    3. Set BOT_API_SERVER=http://127.0.0.1:8081 in .env
"""

"""Entry point — Telegram bot polling + daily scheduler.

Replaces the monolithic scheduler.py by composing clean modules:
  config.py → telegram_utils.py → bot_handler.py → main.py
"""
from __future__ import annotations

import logging
import threading
import time

import requests
import schedule

from app.core.config import OLLAMA_MODEL, SCHEDULE_TIME, TELEGRAM_BOT_TOKEN
from app.services.bot_handler import BotHandler

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Telegram long-polling
# ---------------------------------------------------------------------------

def poll_telegram(handler: BotHandler) -> None:
    """Continuously poll Telegram for new messages."""
    log.info("Starting Telegram long polling …")
    offset = 0

    # Skip messages that arrived before the bot started
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
            params={"offset": -1, "timeout": 1},
            timeout=5,
        )
        data = resp.json()
        if data.get("ok") and data.get("result"):
            offset = data["result"][-1]["update_id"] + 1
    except Exception as exc:
        log.warning("Failed to get initial offset: %s", exc)

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            resp = requests.get(
                url, params={"offset": offset, "timeout": 15}, timeout=20
            )
            if resp.status_code != 200:
                time.sleep(5)
                continue
            data = resp.json()
            if not data.get("ok"):
                time.sleep(5)
                continue
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                try:
                    handler.handle_update(update)
                except Exception as exc:
                    log.error("Error handling update: %s", exc, exc_info=True)
        except Exception as exc:
            log.error("Polling error: %s", exc)
            time.sleep(5)


# ---------------------------------------------------------------------------
# Scheduled tasks
# ---------------------------------------------------------------------------

def run_scheduled_tasks() -> None:
    """Execute daily digest + GitHub trending tasks."""
    log.info("=" * 40)
    log.info("Running scheduled tasks …")

    try:
        from app.tasks.arxiv_fetcher import main as send_papers_main
        send_papers_main()
    except Exception as exc:
        log.error("send_papers failed: %s", exc, exc_info=True)

    try:
        from app.tasks.github_trending import main as trending_github_main
        trending_github_main()
    except Exception as exc:
        log.error("trending_github failed: %s", exc, exc_info=True)

    log.info("Scheduled tasks completed.")
    log.info("=" * 40)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN is empty in .env!")
        return

    log.info("=" * 60)
    log.info("  DAILY PAPER BRIEF BOT")
    log.info("  Schedule : %s", SCHEDULE_TIME)
    log.info("  Model    : %s", OLLAMA_MODEL)
    log.info("=" * 60)

    handler = BotHandler()

    # Start Telegram polling in a daemon thread
    poll_thread = threading.Thread(
        target=poll_telegram, args=(handler,), daemon=True
    )
    poll_thread.start()

    # Schedule daily tasks
    schedule.every().day.at(SCHEDULE_TIME).do(run_scheduled_tasks)
    next_run = schedule.next_run()
    if next_run:
        log.info("Next scheduled run: %s", next_run)

    # Keep main thread alive
    try:
        while True:
            schedule.run_pending()
            time.sleep(2)
    except KeyboardInterrupt:
        log.info("Shutting down …")


if __name__ == "__main__":
    main()

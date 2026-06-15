"""Shared configuration, environment loading, and logging setup.

Single source of truth for all config values — eliminates the duplicated
load_env() that was copy-pasted across scheduler.py, send_papers.py,
and trending_github.py.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def _load_env() -> None:
    """Read .env file and set defaults (won't overwrite existing vars)."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------------------
# Ollama / LLM
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

SCHEDULE_TIME: str = os.getenv("SCHEDULE_TIME", "13:00")

# ---------------------------------------------------------------------------
# Paper search
# ---------------------------------------------------------------------------

TOPICS: list[str] = [
    t.strip()
    for t in os.getenv("TOPICS", "AI agents,RAG,multi-agent systems,LLM reasoning").split(",")
    if t.strip()
]

EXCLUDE_KEYWORDS: list[str] = [
    t.strip().lower()
    for t in os.getenv("EXCLUDE_KEYWORDS", "quantum,bioinformatics,hardware,protein").split(",")
    if t.strip()
]

MAX_RESULTS: int = int(os.getenv("MAX_RESULTS", "30"))
DAYS_BACK: int = int(os.getenv("DAYS_BACK", "7"))
TOP_K: int = int(os.getenv("TOP_K", "5"))

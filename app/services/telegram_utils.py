"""Telegram messaging and Ollama query utilities.

Consolidates the 3 different send_telegram() implementations that existed
across scheduler.py, send_papers.py, and trending_github.py into one
robust version with:
  - Automatic message splitting for Telegram's 4096-char limit
  - HTML fallback when parse_mode fails
  - Retry on transient errors
  - Centralized Ollama LLM query
"""
from __future__ import annotations

import html
import logging
import re
import time
from pathlib import Path

import requests

from app.core.config import TELEGRAM_BOT_TOKEN, OLLAMA_BASE_URL, OLLAMA_MODEL

log = logging.getLogger(__name__)

MAX_TELEGRAM_LEN = 3900


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_message(chat_id: str, text: str, retries: int = 2) -> bool:
    """Send a message to Telegram, auto-splitting if too long.

    Falls back to plain text (no parse_mode) when HTML is invalid.
    """
    if not TELEGRAM_BOT_TOKEN:
        log.warning("TELEGRAM_BOT_TOKEN is empty — skipping send")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = _split_text(text, MAX_TELEGRAM_LEN)

    for chunk in chunks:
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if not _post_with_fallback(url, payload, retries):
            return False
    return True


def _post_with_fallback(url: str, payload: dict, retries: int) -> bool:
    """POST to Telegram API; retry on failure, fallback without HTML."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.ok:
                return True
            # If HTML parsing failed, retry without parse_mode
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if "can't parse entities" in body.get("description", "").lower():
                log.warning("Telegram rejected HTML — retrying as plain text")
                plain = {k: v for k, v in payload.items() if k != "parse_mode"}
                resp2 = requests.post(url, json=plain, timeout=30)
                return resp2.ok
            resp.raise_for_status()
        except requests.RequestException as exc:
            log.error(f"Telegram send failed (attempt {attempt}/{retries}): {exc}")
            if attempt < retries:
                time.sleep(2 * attempt)
    return False


def download_telegram_file(file_id: str, dest_path: Path) -> bool:
    """Download a file from Telegram by file_id."""
    if not TELEGRAM_BOT_TOKEN:
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
    try:
        resp = requests.get(url, params={"file_id": file_id}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            log.error("Failed to getFile: %s", data)
            return False
        
        file_path = data["result"]["file_path"]
        
        dl_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        dl_resp = requests.get(dl_url, stream=True, timeout=60)
        dl_resp.raise_for_status()
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in dl_resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as exc:
        log.error("Error downloading file %s: %s", file_id, exc)
        return False


def _split_text(text: str, max_len: int) -> list[str]:
    """Split *text* into chunks ≤ *max_len* characters, preserving lines."""
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in text.splitlines(keepends=True):
        if current_len + len(line) > max_len:
            if current:
                chunks.append("".join(current))
                current = [line]
                current_len = len(line)
            else:
                # Single line exceeds limit — hard-split
                chunks.append(line[:max_len])
                remainder = line[max_len:]
                current = [remainder] if remainder else []
                current_len = len(remainder)
        else:
            current.append(line)
            current_len += len(line)

    if current:
        chunks.append("".join(current))
    return chunks


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_html(text: str) -> str:
    """Convert lightweight Markdown to Telegram-safe HTML.

    Handles: ## headings, **bold**, *italic*, `code`, ```blocks```.
    """
    escaped = html.escape(text)
    # Headings → bold
    escaped = re.sub(r"(?m)^#{1,4}\s+(.*?)$", r"<b>\1</b>", escaped)
    # **bold**
    escaped = re.sub(
        r"\*\*([^\s*](?:[^*]*[^\s*])?)\*\*", r"<b>\1</b>", escaped
    )
    # *italic*
    escaped = re.sub(
        r"\*([^\s*](?:[^*]*[^\s*])?)\*", r"<i>\1</i>", escaped
    )
    # ```code blocks``` (must come before inline `code`)
    escaped = re.sub(
        r"```(.*?)```", r"<pre>\1</pre>", escaped, flags=re.DOTALL
    )
    # `inline code`
    escaped = re.sub(r"`(.*?)`", r"<code>\1</code>", escaped)
    return escaped


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

def query_ollama(
    prompt: str,
    base_url: str | None = None,
    model: str | None = None,
    timeout: int = 600,
    num_predict: int | None = None,
) -> str:
    """Send a prompt to Ollama and return the response text."""
    base = (base_url or OLLAMA_BASE_URL).rstrip("/")
    mdl = model or OLLAMA_MODEL
    url = f"{base}/api/generate"

    log.info("Calling Ollama (%s), prompt length: %d chars", mdl, len(prompt))
    resp = requests.post(
        url,
        json={
            "model": mdl,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 16384, **({"num_predict": num_predict} if num_predict else {})},
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    raw = resp.json().get("response", "")

    # Model thinks internally (better quality) — strip <think> tags from output
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    if not cleaned and raw.strip():
        # Thinking block may not have closed — extract content after </think>
        parts = raw.split("</think>")
        cleaned = parts[-1].strip() if len(parts) > 1 else raw.strip()

    if not cleaned:
        log.warning("Ollama returned empty response (raw length: %d)", len(raw))

    return cleaned

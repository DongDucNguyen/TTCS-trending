"""Scrape GitHub Trending page, filter AI-related repos, send to Telegram.

Refactored to use shared config.py and telegram_utils.py modules.
"""
from __future__ import annotations

import html
import logging
import re
import sys
from datetime import datetime

import requests

from app.core.config import TELEGRAM_CHAT_ID
from app.services.telegram_utils import send_message

log = logging.getLogger(__name__)

AI_KEYWORDS = [
    "ai", "llm", "gpt", "agent", "machine learning", "deep learning",
    "neural", "transformer", "nlp", "rag", "diffusion", "generative",
    "language model", "embedding", "fine-tun", "reasoning", "vision",
    "multimodal", "chatbot", "inference", "lora", "attention",
    "artificial intelligence", "ml ", "openai", "anthropic", "gemini",
    "stable diffusion", "computer vision", "speech", "whisper", "sam",
    "reinforcement learning", "autonomous", "copilot", "prompt",
    "mcp", "model context protocol", "agentic", "multi-agent",
]


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

def fetch_trending() -> list[dict]:
    """Fetch the GitHub Trending page and parse repo data."""
    url = "https://github.com/trending?since=daily"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/html"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return _parse_html(resp.text)


def _parse_html(html_text: str) -> list[dict]:
    repos: list[dict] = []
    articles = re.split(r'<article\s+class="Box-row"', html_text)

    for art in articles[1:]:
        href = re.search(r'<h2[^>]*>.*?href="(/[^"]+)"', art, re.DOTALL)
        if not href:
            continue
        path = href.group(1).strip().strip("/")

        desc_m = re.search(
            r'<p\s+class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', art, re.DOTALL
        )
        desc = ""
        if desc_m:
            desc = re.sub(r"<[^>]+>", "", desc_m.group(1)).strip()
            desc = html.unescape(desc)

        lang_m = re.search(r'itemprop="programmingLanguage"[^>]*>(.*?)<', art)
        lang = lang_m.group(1).strip() if lang_m else ""

        stars_m = re.search(
            r'href="/' + re.escape(path) + r'/stargazers"[^>]*>\s*([\d,]+)',
            art,
        )
        total = int(stars_m.group(1).replace(",", "").strip()) if stars_m else 0

        today_m = re.search(r"([\d,]+)\s+stars?\s+today", art)
        today = int(today_m.group(1).replace(",", "").strip()) if today_m else 0

        repos.append({
            "repo": path,
            "description": desc,
            "language": lang,
            "total_stars": total,
            "stars_today": today,
            "url": f"https://github.com/{path}",
        })
    return repos


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

def filter_ai(repos: list[dict], k: int = 5) -> list[dict]:
    """Keep only AI-related repos, sorted by today's star count."""
    ai_repos = []
    for repo in repos:
        text = f"{repo['repo']} {repo['description']}".lower()
        if any(kw in text for kw in AI_KEYWORDS):
            ai_repos.append(repo)
    ai_repos.sort(key=lambda x: x["stars_today"], reverse=True)
    return ai_repos[:k]


# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------

def format_msg(repos: list[dict]) -> str:
    today = datetime.now().strftime("%d/%m/%Y")
    lines = [
        f"🔥 <b>GitHub Trending AI — {today}</b>",
        "Top 5 AI repos with fastest star growth today",
        "",
    ]
    for i, r in enumerate(repos, 1):
        desc = html.escape(r["description"][:200]) if r["description"] else "No description"
        name = html.escape(r["repo"])
        lang = html.escape(r["language"]) if r["language"] else "N/A"
        lines.extend([
            f"<b>{i}. <a href=\"{r['url']}\">{name}</a></b>",
            f"   ⭐ +{r['stars_today']} today | Total: {r['total_stars']:,}",
            f"   🔧 {lang}",
            f"   {desc}",
            "",
        ])
    if not repos:
        lines.append("No trending AI repos found today.")
    lines.append("Source: GitHub Trending (daily) 🐙")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    log.info("Fetching GitHub trending page …")
    repos = fetch_trending()
    ai_repos = filter_ai(repos, k=5)

    if ai_repos:
        for i, r in enumerate(ai_repos, 1):
            log.info("  %d. %s (+%d stars)", i, r["repo"], r["stars_today"])

    msg = format_msg(ai_repos)
    chat_id = TELEGRAM_CHAT_ID
    if not chat_id:
        log.warning("TELEGRAM_CHAT_ID is empty — printing to stdout only")
        print(msg)
        return 0

    log.info("Sending to Telegram …")
    send_message(chat_id, msg)
    log.info("Done ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())

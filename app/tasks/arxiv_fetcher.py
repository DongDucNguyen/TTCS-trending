"""Fetch papers from arXiv, filter, rank, and send a digest to Telegram.

Refactored to use shared config.py and telegram_utils.py modules,
eliminating duplicated load_env() and send_telegram().
"""
from __future__ import annotations

import html
import json
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import requests

from app.core.config import (
    EXCLUDE_KEYWORDS,
    DAYS_BACK,
    MAX_RESULTS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TOP_K,
    TOPICS,
)
from app.services.telegram_utils import send_message

log = logging.getLogger(__name__)

NS = {"a": "http://www.w3.org/2005/Atom"}


# ---------------------------------------------------------------------------
# arXiv fetch
# ---------------------------------------------------------------------------

def _get_with_retry(url: str, retries: int = 3) -> requests.Response:
    for attempt in range(1, retries + 1):
        resp = requests.get(
            url, headers={"User-Agent": "paper-bot/1.0"}, timeout=60
        )
        if resp.status_code == 200:
            return resp
        if resp.status_code in {429, 500, 502, 503}:
            wait = int(resp.headers.get("Retry-After", 3 * attempt))
            log.warning("Rate limited (%d), waiting %ds …", resp.status_code, wait)
            time.sleep(wait)
            continue
        resp.raise_for_status()
    raise RuntimeError("arXiv request failed after retries")


def _normalise(text: str) -> str:
    return " ".join(text.replace("\n", " ").split())


def fetch_papers() -> list[dict]:
    """Query arXiv API and return papers published within DAYS_BACK."""
    query = " OR ".join(f'all:"{t}"' for t in TOPICS)
    params = urlencode({
        "search_query": query,
        "start": 0,
        "max_results": MAX_RESULTS,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    url = f"https://export.arxiv.org/api/query?{params}"
    log.info("Fetching from arXiv …")

    resp = _get_with_retry(url)
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    root = ET.fromstring(resp.text)
    papers: list[dict] = []

    for entry in root.findall("a:entry", NS):
        raw_id = entry.findtext("a:id", "", NS)
        arxiv_id = raw_id.rstrip("/").split("/")[-1]
        title = _normalise(entry.findtext("a:title", "", NS))
        abstract = _normalise(entry.findtext("a:summary", "", NS))
        published = entry.findtext("a:published", "", NS)

        pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if pub_dt < cutoff:
            continue

        authors = [
            _normalise(a.findtext("a:name", "", NS))
            for a in entry.findall("a:author", NS)
        ]
        papers.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "abstract": abstract,
            "authors": [a for a in authors if a],
            "published": published[:10],
            "url": raw_id,
        })
    log.info("Found %d papers from arXiv", len(papers))
    return papers


# ---------------------------------------------------------------------------
# Filter & rank
# ---------------------------------------------------------------------------

def filter_and_rank(papers: list[dict]) -> list[dict]:
    """Score papers by keyword relevance and return top-K."""
    terms: set[str] = set()
    for topic in TOPICS:
        lower = topic.lower()
        terms.add(lower)
        for part in lower.replace("-", " ").split():
            if len(part) >= 3:
                terms.add(part)

    scored: list[dict] = []
    for paper in papers:
        text = f"{paper['title']} {paper['abstract']}".lower()
        if any(ex in text for ex in EXCLUDE_KEYWORDS):
            continue

        matches = [t for t in terms if t in text]
        score = 2.0 + len(matches) * 1.5

        if "code" in text or "github" in text:
            score += 1.0
        if "benchmark" in text or "dataset" in text:
            score += 0.7
        if "state-of-the-art" in text or "sota" in text:
            score += 0.5
        if "novel" in text or "first" in text:
            score += 0.3
        if len(paper["authors"]) >= 5:
            score += 0.3

        score = min(10.0, score)
        if score >= 3.5:
            paper["score"] = round(score, 1)
            scored.append(paper)

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:TOP_K]
    log.info("Filtered %d → top %d papers", len(scored), len(top))
    return top


# ---------------------------------------------------------------------------
# Auto-detect chat ID
# ---------------------------------------------------------------------------

def _auto_detect_chat_id() -> str:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    resp = requests.get(url, params={"limit": 10}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("result"):
        return ""
    for update in reversed(data["result"]):
        msg = update.get("message", {})
        chat_id = msg.get("chat", {}).get("id")
        if chat_id:
            return str(chat_id)
    return ""


# ---------------------------------------------------------------------------
# Format digest
# ---------------------------------------------------------------------------

def format_digest(papers: list[dict]) -> str:
    """Build an HTML-formatted digest message."""
    today = datetime.now().strftime("%d/%m/%Y")
    lines = [
        f"📰 <b>Daily Paper Brief — {today}</b>",
        f"Topics: {html.escape(', '.join(TOPICS))}",
        f"Top {len(papers)} papers",
        "========================",
        "",
    ]
    for i, p in enumerate(papers, 1):
        auth_list = p["authors"][:3]
        auth_str = html.escape(", ".join(auth_list))
        if len(p["authors"]) > 3:
            auth_str += f" +{len(p['authors']) - 3} others"

        abstract = p["abstract"]
        if len(abstract) > 280:
            abstract = abstract[:277] + "..."

        badge = (
            "🔥 Must-read"
            if p["score"] >= 8
            else "⭐ Worth reading"
            if p["score"] >= 6
            else "📌 Interesting"
        )
        lines.extend([
            f"<b>{i}. {html.escape(p['title'])}</b>",
            f"   {badge} — Score: {p['score']}/10",
            f"   👤 {auth_str}",
            f"   📅 {p['published']}",
            f"   🔗 <a href=\"{p['url']}\">arXiv:{p['arxiv_id']}</a>",
            f"   💬 /paper{i}",
            "",
            f"   <i>{html.escape(abstract)}</i>",
            "",
            "─" * 30,
            "",
        ])
    if not papers:
        lines.append("No matching papers found.")
    lines.append("Powered by Daily Paper Brief Bot 🤖")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    chat_id = TELEGRAM_CHAT_ID

    if not TELEGRAM_BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN missing!")
        return 1

    if not chat_id:
        log.warning("TELEGRAM_CHAT_ID missing, auto-detecting …")
        chat_id = _auto_detect_chat_id()
        if not chat_id:
            log.error("Could not detect chat_id.")
            return 1
        log.info("Detected chat_id: %s", chat_id)

    papers = fetch_papers()
    if not papers:
        send_message(chat_id, "📰 Daily Paper Brief\n\nNo matching papers found.")
        return 0

    top = filter_and_rank(papers)

    # Cache papers for bot Q&A (/paper1, /paper2, …)
    cache_path = Path("data/last_sent_papers.json")
    cache_data = [
        {
            "index": idx,
            "title": p["title"],
            "abstract": p["abstract"],
            "authors": p["authors"],
            "published": p["published"],
            "url": p["url"],
            "arxiv_id": p["arxiv_id"],
            "score": p["score"],
        }
        for idx, p in enumerate(top, 1)
    ]
    cache_path.write_text(
        json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("Saved cache → %s", cache_path)

    digest = format_digest(top)
    log.info("Sending %d papers to Telegram …", len(top))
    send_message(chat_id, digest)
    log.info("Done ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())

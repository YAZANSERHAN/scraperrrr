"""
Telegram push notifications for newly-found relevant jobs.

Required env vars:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
"""

import os
import requests
from urllib.parse import quote_plus


def _escape_markdown(text: str) -> str:
    # Telegram MarkdownV2 requires escaping these characters
    chars_to_escape = r"_*[]()~`>#+-=|{}.!"
    for ch in chars_to_escape:
        text = text.replace(ch, f"\\{ch}")
    return text


def send_job_alert(job: dict) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[notify] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set, skipping")
        return False

    title = _escape_markdown(job["title"])
    company = _escape_markdown(job["company"])
    location = _escape_markdown(job.get("location", "") or "N/A")
    reason = _escape_markdown(job.get("relevance_reason", ""))
    score = job.get("relevance_score", "?")

    linkedin_search_url = (
        f"https://www.linkedin.com/jobs/search/?keywords="
        f"{quote_plus(job['company'] + ' ' + job['title'])}"
    )

    text = (
        f"*New match \\({score}/10\\)*\n"
        f"*{title}*\n"
        f"{company} — {location}\n"
        f"_{reason}_\n\n"
        f"[Apply]({job['url']})\n"
        f"[Search on LinkedIn]({linkedin_search_url})"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[notify] failed to send alert for {job.get('title')}: {e}")
        return False


def send_summary(new_count: int, total_scanned: int) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    text = f"Job scan complete: {new_count} new relevant match(es) out of {total_scanned} scanned."
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print(f"[notify] failed to send summary: {e}")

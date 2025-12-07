#!/usr/bin/env python3
"""
Export all chats that are NOT part of the main series.

This exports everything except:
- Daily insights
- Daily Summary
- Done Better

Usage:
    python export_remaining_chats.py
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import time
import re

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

API_KEY = os.getenv("LIMITLESS_API_KEY")
API_URL = os.getenv("LIMITLESS_API_URL", "https://api.limitless.ai")
MAX_RETRIES = 3
RETRY_DELAY = 5
REQUEST_DELAY = 0.5

# Series to exclude (already exported)
EXCLUDED_SERIES = [
    "Daily insights",
    "Daily Summary",
    "Done Better"
]


def sanitize_filename(text):
    """Convert text to a safe filename."""
    # Handle None or empty text
    if not text:
        return 'untitled'

    text = str(text)  # Ensure it's a string
    text = re.sub(r'[<>:"/\\|?*]', '-', text)
    text = text[:100]
    text = text.strip('. ')
    return text if text else 'untitled'


def fetch_all_chats(max_pages=200):
    """Fetch all available chats from the API."""
    if not API_KEY:
        print("Error: LIMITLESS_API_KEY not found in environment variables.")
        return []

    endpoint = f"{API_URL}/v1/chats"
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    }

    all_chats = []
    cursor = None
    pages_fetched = 0

    print("Fetching all chats from the API...")

    while pages_fetched < max_pages:
        params = {
            "limit": 10,
            "includeMarkdown": "true"
        }

        if cursor:
            params["cursor"] = cursor

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(endpoint, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                break
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"  Request failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"  Failed after {MAX_RETRIES} attempts: {e}")
                    return all_chats

        chats = data.get("data", {}).get("chats", [])
        all_chats.extend(chats)

        pages_fetched += 1
        if pages_fetched % 10 == 0:
            print(f"  Fetched {len(all_chats)} chats...")

        next_cursor = data.get("meta", {}).get("chats", {}).get("nextCursor")
        if not next_cursor:
            break

        cursor = next_cursor
        time.sleep(REQUEST_DELAY)

    print(f"\n✅ Fetched {len(all_chats)} total chats\n")
    return all_chats


def format_chat_as_markdown(chat):
    """Convert a chat object to markdown format."""
    chat_id = chat.get("id", "unknown")
    summary = chat.get("summary") or "Untitled Chat"
    created_at = chat.get("createdAt", "")
    visibility = chat.get("visibility") or "unknown"

    created_date = "Unknown"
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            created_date = dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            created_date = created_at

    md = f"""# {summary}

**Chat ID:** `{chat_id}`
**Created:** {created_date}
**Visibility:** {visibility}

---

"""

    messages = chat.get("messages", [])

    for i, message in enumerate(messages):
        text = message.get("text", "")
        msg_created = message.get("createdAt", "")
        user = message.get("user", {})
        role = user.get("role", "unknown")
        name = user.get("name", "Unknown")

        msg_time = ""
        if msg_created:
            try:
                dt = datetime.fromisoformat(msg_created.replace('Z', '+00:00'))
                msg_time = dt.strftime("%I:%M %p")
            except:
                msg_time = msg_created

        if role == "user":
            md += f"## 👤 {name}"
        else:
            md += f"## 🤖 {name}"

        if msg_time:
            md += f" • {msg_time}"

        md += "\n\n"
        md += text + "\n\n"

        if i < len(messages) - 1:
            md += "---\n\n"

    return md


def save_chat(chat, output_dir):
    """Save a chat to a markdown file."""
    chat_id = chat.get("id", "unknown")
    summary = chat.get("summary") or "untitled"
    created_at = chat.get("createdAt", "")

    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_str = dt.strftime("%Y-%m-%d")
            year_month = dt.strftime("%Y-%m")

            month_dir = output_dir / year_month
            month_dir.mkdir(parents=True, exist_ok=True)

            safe_summary = sanitize_filename(summary)
            filename = f"{date_str}-{safe_summary}-{chat_id[:8]}.md"
            output_path = month_dir / filename
        except:
            safe_summary = sanitize_filename(summary)
            filename = f"{safe_summary}-{chat_id[:8]}.md"
            output_path = output_dir / filename
    else:
        safe_summary = sanitize_filename(summary)
        filename = f"{safe_summary}-{chat_id[:8]}.md"
        output_path = output_dir / filename

    if output_path.exists():
        return None

    try:
        markdown = format_chat_as_markdown(chat)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        return output_path
    except Exception as e:
        print(f"  ❌ Error saving chat {chat_id}: {e}")
        return None


def main():
    output_dir = Path(__file__).parent.parent / "exports" / "chats"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_dir}\n")
    print(f"Excluding series: {', '.join(EXCLUDED_SERIES)}\n")

    # Fetch all chats
    all_chats = fetch_all_chats()

    if not all_chats:
        print("❌ No chats found")
        sys.exit(1)

    # Filter out the main series
    remaining_chats = [
        c for c in all_chats
        if c.get("summary") not in EXCLUDED_SERIES
    ]

    print(f"Total chats: {len(all_chats)}")
    print(f"Main series (excluded): {len(all_chats) - len(remaining_chats)}")
    print(f"Remaining to export: {len(remaining_chats)}\n")

    # Export remaining chats
    print(f"Exporting {len(remaining_chats)} chats...\n")

    saved_count = 0
    skipped_count = 0

    for i, chat in enumerate(remaining_chats, 1):
        result = save_chat(chat, output_dir)

        if result:
            if i % 10 == 0:
                print(f"  Exported {i}/{len(remaining_chats)} chats...")
            saved_count += 1
        else:
            skipped_count += 1

    # Summary
    print(f"\n{'='*60}")
    print("Export Summary")
    print(f"{'='*60}")
    print(f"  Total chats fetched: {len(all_chats)}")
    print(f"  Main series (skipped): {len(all_chats) - len(remaining_chats)}")
    print(f"  Remaining chats: {len(remaining_chats)}")
    print(f"  Newly saved: {saved_count}")
    print(f"  Already existed: {skipped_count}")
    print(f"{'='*60}")

    if saved_count > 0:
        print(f"\n✅ Successfully exported {saved_count} chats to {output_dir}")

    print("\n📊 Archive Structure:")
    print("  exports/")
    print("    insights/         - Daily Insights (Limitless-generated)")
    print("    daily-summaries/  - Your daily summaries")
    print("    done-better/      - Your daily reflections")
    print("    chats/            - Everything else (just exported)")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Export all chats from the Limitless API to organized markdown files.

This script fetches all available chats and saves them as markdown files,
organized by date and type/summary.

Usage:
    # Export all chats
    python export_all_chats.py

    # Export with custom output directory
    python export_all_chats.py --output-dir exports/all-chats

    # Export only specific types
    python export_all_chats.py --filter "Daily insights"

    # Export date range
    python export_all_chats.py --start 2025-11-01 --end 2025-11-30
"""

import os
import sys
import json
import requests
import argparse
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


def sanitize_filename(text):
    """Convert text to a safe filename."""
    # Remove or replace unsafe characters
    text = re.sub(r'[<>:"/\\|?*]', '-', text)
    # Limit length
    text = text[:100]
    # Remove leading/trailing spaces and dots
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

        # Make API request with retries
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
        print(f"  Page {pages_fetched}: {len(all_chats)} total chats...")

        next_cursor = data.get("meta", {}).get("chats", {}).get("nextCursor")
        if not next_cursor:
            print(f"  Reached end of available chats")
            break

        cursor = next_cursor
        time.sleep(REQUEST_DELAY)

    print(f"\n✅ Fetched {len(all_chats)} total chats\n")
    return all_chats


def format_chat_as_markdown(chat):
    """
    Convert a chat object to markdown format.

    Returns:
        str: Markdown formatted chat
    """
    chat_id = chat.get("id", "unknown")
    summary = chat.get("summary", "Untitled Chat")
    created_at = chat.get("createdAt", "")
    started_at = chat.get("startedAt", "")
    visibility = chat.get("visibility", "unknown")

    # Parse date
    created_date = "Unknown"
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            created_date = dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            created_date = created_at

    # Build markdown
    md = f"""# {summary}

**Chat ID:** `{chat_id}`
**Created:** {created_date}
**Visibility:** {visibility}

---

"""

    # Add messages
    messages = chat.get("messages", [])

    for i, message in enumerate(messages):
        msg_id = message.get("id", "")
        text = message.get("text", "")
        msg_created = message.get("createdAt", "")
        user = message.get("user", {})
        role = user.get("role", "unknown")
        name = user.get("name", "Unknown")

        # Format timestamp
        msg_time = ""
        if msg_created:
            try:
                dt = datetime.fromisoformat(msg_created.replace('Z', '+00:00'))
                msg_time = dt.strftime("%I:%M %p")
            except:
                msg_time = msg_created

        # Add message header
        if role == "user":
            md += f"## 👤 {name}"
        else:
            md += f"## 🤖 {name}"

        if msg_time:
            md += f" • {msg_time}"

        md += "\n\n"

        # Add message content
        md += text + "\n\n"

        # Add separator between messages (except last)
        if i < len(messages) - 1:
            md += "---\n\n"

    return md


def filter_chats(chats, summary_filter=None, start_date=None, end_date=None):
    """Filter chats based on criteria."""
    filtered = chats

    # Filter by summary
    if summary_filter:
        filtered = [c for c in filtered if c.get("summary") and summary_filter.lower() in c.get("summary", "").lower()]

    # Filter by date range
    if start_date or end_date:
        date_filtered = []
        for chat in filtered:
            created_at = chat.get("createdAt", "")
            if created_at:
                try:
                    chat_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()

                    if start_date and chat_date < start_date:
                        continue
                    if end_date and chat_date > end_date:
                        continue

                    date_filtered.append(chat)
                except:
                    pass
        filtered = date_filtered

    return filtered


def save_chat(chat, output_dir, organize_by_date=True):
    """
    Save a chat to a markdown file.

    Returns:
        Path: Path to saved file, or None if failed
    """
    chat_id = chat.get("id", "unknown")
    summary = chat.get("summary", "untitled")
    created_at = chat.get("createdAt", "")

    # Determine output path
    if organize_by_date and created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_str = dt.strftime("%Y-%m-%d")
            year_month = dt.strftime("%Y-%m")

            # Organize: output_dir/YYYY-MM/YYYY-MM-DD-summary-chatid.md
            month_dir = output_dir / year_month
            month_dir.mkdir(parents=True, exist_ok=True)

            safe_summary = sanitize_filename(summary)
            filename = f"{date_str}-{safe_summary}-{chat_id[:8]}.md"
            output_path = month_dir / filename
        except:
            # Fallback to simple organization
            safe_summary = sanitize_filename(summary)
            filename = f"{safe_summary}-{chat_id[:8]}.md"
            output_path = output_dir / filename
    else:
        safe_summary = sanitize_filename(summary)
        filename = f"{safe_summary}-{chat_id[:8]}.md"
        output_path = output_dir / filename

    # Skip if exists
    if output_path.exists():
        return None  # Already exists

    # Format and save
    try:
        markdown = format_chat_as_markdown(chat)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        return output_path
    except Exception as e:
        print(f"  ❌ Error saving chat {chat_id}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Export all chats from Limitless API to markdown files"
    )
    parser.add_argument(
        "--output-dir",
        default="exports/chats",
        help="Output directory for chat files (default: exports/chats)"
    )
    parser.add_argument(
        "--filter",
        help="Filter chats by summary (case-insensitive substring match)"
    )
    parser.add_argument(
        "--start",
        help="Start date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--end",
        help="End date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--no-organize",
        action="store_true",
        help="Don't organize by date (save all to output dir root)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=200,
        help="Maximum API pages to fetch (default: 200)"
    )

    args = parser.parse_args()

    # Parse dates
    start_date = None
    end_date = None

    if args.start:
        try:
            start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid start date '{args.start}'. Use YYYY-MM-DD")
            sys.exit(1)

    if args.end:
        try:
            end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid end date '{args.end}'. Use YYYY-MM-DD")
            sys.exit(1)

    # Create output directory
    output_dir = Path(__file__).parent.parent / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_dir}\n")

    # Fetch all chats
    all_chats = fetch_all_chats(max_pages=args.max_pages)

    if not all_chats:
        print("❌ No chats found")
        sys.exit(1)

    # Filter chats
    filtered_chats = filter_chats(all_chats, args.filter, start_date, end_date)

    if args.filter or start_date or end_date:
        print(f"Filtered to {len(filtered_chats)} chats\n")

    # Export chats
    print(f"Exporting {len(filtered_chats)} chats...\n")

    saved_count = 0
    skipped_count = 0

    for chat in filtered_chats:
        result = save_chat(chat, output_dir, organize_by_date=not args.no_organize)

        if result:
            summary = chat.get("summary", "Untitled")[:50]
            print(f"  ✅ {summary}")
            saved_count += 1
        else:
            skipped_count += 1

    # Summary
    print(f"\n{'='*60}")
    print("Export Summary")
    print(f"{'='*60}")
    print(f"  Total chats fetched: {len(all_chats)}")
    print(f"  After filtering: {len(filtered_chats)}")
    print(f"  Newly saved: {saved_count}")
    print(f"  Already existed: {skipped_count}")
    print(f"{'='*60}")

    if saved_count > 0:
        print(f"\n✅ Successfully exported {saved_count} chats to {output_dir}")


if __name__ == "__main__":
    main()


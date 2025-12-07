#!/usr/bin/env python3
"""
Sync all Limitless chats to local archive.

This script maintains a complete local backup of all your Limitless chats,
organized by series and date. Run it periodically to keep your archive up to date.

Usage:
    python sync_all_chats.py [--dry-run] [--verbose]

Examples:
    # Normal sync
    python sync_all_chats.py

    # See what would be synced without actually doing it
    python sync_all_chats.py --dry-run

    # Show detailed progress
    python sync_all_chats.py --verbose
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
from collections import defaultdict

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

# Series configuration
SERIES_CONFIG = {
    "Daily insights": {
        "dir": "insights",
        "filename_pattern": "{date}-daily-insights.md",
        "description": "Limitless-generated Daily Insights"
    },
    "Daily Summary": {
        "dir": "daily-summaries",
        "filename_pattern": "{date}-{summary}-{id}.md",
        "description": "Your daily summaries"
    },
    "Done Better": {
        "dir": "done-better",
        "filename_pattern": "{date}-{summary}-{id}.md",
        "description": "Your daily reflections"
    }
}

DEFAULT_DIR = "chats"


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


def fetch_all_chats(max_pages=200, verbose=False):
    """Fetch all available chats from the API."""
    if not API_KEY:
        print("❌ Error: LIMITLESS_API_KEY not found in environment variables.")
        return []

    endpoint = f"{API_URL}/v1/chats"
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    }

    all_chats = []
    cursor = None
    pages_fetched = 0

    print("🔄 Fetching chats from Limitless API...")

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
                    if verbose:
                        print(f"  ⚠️  Request failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"  ❌ Failed after {MAX_RETRIES} attempts: {e}")
                    return all_chats

        chats = data.get("data", {}).get("chats", [])
        all_chats.extend(chats)

        pages_fetched += 1
        if verbose or pages_fetched % 10 == 0:
            print(f"  Fetched {len(all_chats)} chats...")

        next_cursor = data.get("meta", {}).get("chats", {}).get("nextCursor")
        if not next_cursor:
            break

        cursor = next_cursor
        time.sleep(REQUEST_DELAY)

    print(f"✅ Fetched {len(all_chats)} total chats from API\n")
    return all_chats


def get_existing_chat_ids(base_dir):
    """
    Scan existing archive and extract all chat IDs.
    Returns a set of chat IDs that are already archived.
    """
    existing_ids = set()

    # Scan all subdirectories
    for series_dir in ["insights", "daily-summaries", "done-better", "chats"]:
        dir_path = base_dir / series_dir
        if not dir_path.exists():
            continue

        # Find all .md files recursively
        for md_file in dir_path.rglob("*.md"):
            # Extract chat ID from filename
            # Patterns:
            # - YYYY-MM-DD-daily-insights.md (no ID, use special handling)
            # - YYYY-MM-DD-Summary-CHATID.md
            filename = md_file.stem

            # Try to extract 8-character ID at the end
            parts = filename.split('-')
            if len(parts) > 0:
                potential_id = parts[-1]
                if len(potential_id) == 8:
                    existing_ids.add(potential_id)

            # For Daily Insights, read the file to get the chat ID
            if "daily-insights" in filename:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Look for Chat ID in the file
                        if "Chat ID:" in content:
                            for line in content.split('\n'):
                                if "Chat ID:" in line:
                                    # Extract ID from markdown: **Chat ID:** `chatid`
                                    import re
                                    match = re.search(r'`([a-zA-Z0-9]+)`', line)
                                    if match:
                                        existing_ids.add(match.group(1)[:8])
                except:
                    pass

    return existing_ids


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
        if text is None:
            text = ""
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


def get_output_path(chat, base_dir):
    """
    Determine the output path for a chat based on its series.
    Returns (output_path, series_name)
    """
    chat_id = chat.get("id", "unknown")
    summary = chat.get("summary", "untitled")
    created_at = chat.get("createdAt", "")

    # Handle None summary
    if not summary:
        summary = "untitled"

    # Determine which series this belongs to
    series_config = SERIES_CONFIG.get(summary)

    if series_config:
        series_dir = series_config["dir"]
        filename_pattern = series_config["filename_pattern"]
    else:
        series_dir = DEFAULT_DIR
        filename_pattern = "{date}-{summary}-{id}.md"

    # Parse date
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_str = dt.strftime("%Y-%m-%d")
            year_month = dt.strftime("%Y-%m")

            # Create month subdirectory
            month_dir = base_dir / series_dir / year_month

            # Format filename
            safe_summary = sanitize_filename(summary)
            filename = filename_pattern.format(
                date=date_str,
                summary=safe_summary,
                id=chat_id[:8]
            )

            output_path = month_dir / filename
        except:
            # Fallback if date parsing fails
            safe_summary = sanitize_filename(summary)
            filename = f"{safe_summary}-{chat_id[:8]}.md"
            output_path = base_dir / series_dir / filename
    else:
        safe_summary = sanitize_filename(summary)
        filename = f"{safe_summary}-{chat_id[:8]}.md"
        output_path = base_dir / series_dir / filename

    return output_path, series_dir


def save_chat(chat, base_dir, dry_run=False):
    """
    Save a chat to the appropriate location.
    Returns (success, output_path, series_name)
    """
    output_path, series_name = get_output_path(chat, base_dir)

    if dry_run:
        return True, output_path, series_name

    # Create directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        markdown = format_chat_as_markdown(chat)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        return True, output_path, series_name
    except Exception as e:
        print(f"  ❌ Error saving chat {chat.get('id', 'unknown')}: {e}")
        return False, output_path, series_name


def main():
    parser = argparse.ArgumentParser(
        description="Sync all Limitless chats to local archive"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without actually saving files"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed progress information"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=200,
        help="Maximum API pages to fetch (default: 200)"
    )

    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent / "exports"

    print("="*60)
    print("📦 Limitless Chat Sync")
    print("="*60)
    print(f"Archive location: {base_dir}")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be saved")
    print()

    # Scan existing archive
    print("📂 Scanning existing archive...")
    existing_ids = get_existing_chat_ids(base_dir)
    print(f"   Found {len(existing_ids)} existing chats\n")

    # Fetch all chats from API
    all_chats = fetch_all_chats(max_pages=args.max_pages, verbose=args.verbose)

    if not all_chats:
        print("❌ No chats found")
        sys.exit(1)

    # Identify new chats
    new_chats = [
        chat for chat in all_chats
        if chat.get("id", "")[:8] not in existing_ids
    ]

    print(f"📊 Sync Analysis:")
    print(f"   Total chats in API: {len(all_chats)}")
    print(f"   Already archived: {len(existing_ids)}")
    print(f"   New chats to sync: {len(new_chats)}")
    print()

    if len(new_chats) == 0:
        print("✅ Archive is up to date! Nothing to sync.")
        return

    if args.dry_run:
        print("🔍 Would sync the following chats:\n")
    else:
        print(f"🔄 Syncing {len(new_chats)} new chats...\n")

    # Group by series for reporting
    by_series = defaultdict(list)
    saved_count = 0
    error_count = 0

    for chat in new_chats:
        success, output_path, series_name = save_chat(chat, base_dir, dry_run=args.dry_run)

        if success:
            by_series[series_name].append(chat)
            saved_count += 1

            if args.verbose:
                summary = chat.get("summary", "Untitled")[:50]
                print(f"  ✅ [{series_name}] {summary}")
        else:
            error_count += 1

    # Summary
    print()
    print("="*60)
    print("📊 Sync Summary")
    print("="*60)

    for series_name, chats in sorted(by_series.items()):
        series_desc = SERIES_CONFIG.get(
            next((k for k, v in SERIES_CONFIG.items() if v["dir"] == series_name), None),
            {}
        ).get("description", "Other chats")

        print(f"  {series_name:20s} {len(chats):3d} chats - {series_desc}")

    print(f"\n  {'Total new chats:':20s} {saved_count}")

    if error_count > 0:
        print(f"  {'Errors:':20s} {error_count}")

    print("="*60)

    if args.dry_run:
        print("\n🔍 Dry run complete. Run without --dry-run to actually sync.")
    else:
        print(f"\n✅ Sync complete! {saved_count} new chats added to archive.")

    print("\n📂 Archive structure:")
    print(f"  {base_dir}/")
    for series_name, config in SERIES_CONFIG.items():
        count = len(by_series.get(config["dir"], []))
        if count > 0 or not args.dry_run:
            print(f"    {config['dir']:20s} - {config['description']}")
    if len(by_series.get(DEFAULT_DIR, [])) > 0 or not args.dry_run:
        print(f"    {DEFAULT_DIR:20s} - Other chats")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Analyze all chats from the Limitless API to identify patterns, series, and types.

This script fetches all available chats and analyzes them to discover:
- Different chat types/categories
- Recurring patterns or series
- Chat summaries and their frequency
- Temporal patterns
- Message characteristics

Usage:
    python analyze_chats.py [--save-raw] [--max-pages N]
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from collections import Counter, defaultdict
import time

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


def fetch_all_chats(max_pages=200):
    """
    Fetch all available chats from the API.

    Returns:
        list: List of all chat objects
    """
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
    print(f"{'='*60}\n")

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
                    print(f"  Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"  Failed after {MAX_RETRIES} attempts: {e}")
                    return all_chats

        # Add all chats from this page
        chats = data.get("data", {}).get("chats", [])
        all_chats.extend(chats)

        pages_fetched += 1
        print(f"  Page {pages_fetched}: {len(all_chats)} total chats fetched...")

        # Check for next page
        next_cursor = data.get("meta", {}).get("chats", {}).get("nextCursor")
        if not next_cursor:
            print(f"\n✅ Reached end of available chats")
            break

        cursor = next_cursor
        time.sleep(REQUEST_DELAY)

    print(f"\n{'='*60}")
    print(f"Total chats fetched: {len(all_chats)}")
    print(f"{'='*60}\n")

    return all_chats


def analyze_chat_metadata(chat):
    """
    Extract metadata from a chat for analysis.

    Returns:
        dict: Metadata about the chat
    """
    messages = chat.get("messages", [])

    # Parse dates
    created_at = chat.get("createdAt", "")
    started_at = chat.get("startedAt", "")

    created_date = None
    if created_at:
        try:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            pass

    # Analyze messages
    user_messages = []
    assistant_messages = []

    for msg in messages:
        user = msg.get("user", {})
        role = user.get("role", "")
        text = msg.get("text", "")

        if role == "user":
            user_messages.append(text)
        elif role == "assistant":
            assistant_messages.append(text)

    # Get first user message (often indicates purpose)
    first_user_msg = user_messages[0] if user_messages else ""

    # Calculate assistant response length safely
    assistant_response_length = 0
    if assistant_messages and assistant_messages[0] is not None:
        assistant_response_length = len(assistant_messages[0])

    return {
        "id": chat.get("id", ""),
        "summary": chat.get("summary", ""),
        "visibility": chat.get("visibility", ""),
        "created_at": created_at,
        "created_date": created_date,
        "started_at": started_at,
        "message_count": len(messages),
        "user_message_count": len(user_messages),
        "assistant_message_count": len(assistant_messages),
        "first_user_message": first_user_msg[:200],  # First 200 chars
        "first_user_message_full": first_user_msg,
        "assistant_response_length": assistant_response_length,
    }


def analyze_patterns(chats_metadata):
    """
    Analyze patterns across all chats.

    Returns:
        dict: Analysis results
    """
    print("\n" + "="*60)
    print("CHAT ANALYSIS RESULTS")
    print("="*60 + "\n")

    # 1. Summary analysis
    print("📊 CHAT SUMMARIES (Types/Categories)")
    print("-" * 60)
    summaries = Counter(m["summary"] for m in chats_metadata if m["summary"])
    for summary, count in summaries.most_common():
        print(f"  {count:3d}x  {summary}")

    # 2. First message patterns
    print("\n\n🔍 FIRST USER MESSAGE PATTERNS")
    print("-" * 60)
    first_messages = Counter(m["first_user_message"] for m in chats_metadata if m["first_user_message"])
    for msg, count in first_messages.most_common(20):
        if count > 1:  # Only show recurring patterns
            print(f"  {count:3d}x  {msg}")

    # 3. Temporal patterns
    print("\n\n📅 TEMPORAL PATTERNS")
    print("-" * 60)

    # Group by date
    chats_by_date = defaultdict(list)
    for m in chats_metadata:
        if m["created_date"]:
            date_str = m["created_date"].date().isoformat()
            chats_by_date[date_str].append(m)

    # Find dates with multiple chats
    multi_chat_dates = {date: chats for date, chats in chats_by_date.items() if len(chats) > 1}

    if multi_chat_dates:
        print(f"\n  Dates with multiple chats: {len(multi_chat_dates)}")
        for date in sorted(multi_chat_dates.keys(), reverse=True)[:10]:
            chats = multi_chat_dates[date]
            print(f"\n  {date} ({len(chats)} chats):")
            for chat in chats:
                print(f"    - {chat['summary'][:50]}")

    # 4. Message characteristics
    print("\n\n💬 MESSAGE CHARACTERISTICS")
    print("-" * 60)

    avg_messages = sum(m["message_count"] for m in chats_metadata) / len(chats_metadata)
    avg_user_msgs = sum(m["user_message_count"] for m in chats_metadata) / len(chats_metadata)
    avg_assistant_msgs = sum(m["assistant_message_count"] for m in chats_metadata) / len(chats_metadata)
    avg_response_length = sum(m["assistant_response_length"] for m in chats_metadata) / len(chats_metadata)

    print(f"  Average messages per chat: {avg_messages:.1f}")
    print(f"  Average user messages: {avg_user_msgs:.1f}")
    print(f"  Average assistant messages: {avg_assistant_msgs:.1f}")
    print(f"  Average assistant response length: {avg_response_length:,.0f} characters")

    # 5. Identify series/recurring patterns
    print("\n\n🔄 POTENTIAL SERIES/RECURRING PATTERNS")
    print("-" * 60)

    # Group by summary
    by_summary = defaultdict(list)
    for m in chats_metadata:
        if m["summary"]:
            by_summary[m["summary"]].append(m)

    # Find series (summaries with multiple instances)
    series = {summary: chats for summary, chats in by_summary.items() if len(chats) > 1}

    if series:
        for summary, chats in sorted(series.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"\n  📌 {summary} ({len(chats)} instances)")

            # Check if it's a daily pattern
            dates = [c["created_date"].date() for c in chats if c["created_date"]]
            if len(dates) > 1:
                dates_sorted = sorted(dates)
                date_range = f"{dates_sorted[0]} to {dates_sorted[-1]}"

                # Check for daily pattern
                date_diffs = [(dates_sorted[i+1] - dates_sorted[i]).days for i in range(len(dates_sorted)-1)]
                if date_diffs:
                    avg_gap = sum(date_diffs) / len(date_diffs)
                    if avg_gap <= 1.5:
                        print(f"     ⭐ DAILY SERIES - appears ~daily")
                    elif avg_gap <= 7.5:
                        print(f"     📅 WEEKLY SERIES - appears ~weekly")
                    else:
                        print(f"     🔹 OCCASIONAL - avg {avg_gap:.1f} days between")

                print(f"     Date range: {date_range}")

                # Show first user message pattern
                first_msgs = set(c["first_user_message"] for c in chats if c["first_user_message"])
                if len(first_msgs) == 1:
                    print(f"     Consistent prompt: \"{list(first_msgs)[0]}\"")
                else:
                    print(f"     Variable prompts ({len(first_msgs)} unique)")

    # 6. Visibility analysis
    print("\n\n🔒 VISIBILITY")
    print("-" * 60)
    visibility = Counter(m["visibility"] for m in chats_metadata if m["visibility"])
    for vis, count in visibility.most_common():
        print(f"  {count:3d}x  {vis}")

    return {
        "total_chats": len(chats_metadata),
        "summaries": dict(summaries),
        "series": {k: len(v) for k, v in series.items()},
        "dates_with_multiple_chats": len(multi_chat_dates),
    }


def save_detailed_report(chats_metadata, analysis, output_dir):
    """
    Save a detailed JSON report of the analysis.
    """
    report = {
        "analysis_date": datetime.now().isoformat(),
        "total_chats": len(chats_metadata),
        "summary": analysis,
        "chats": [
            {
                "id": m["id"],
                "summary": m["summary"],
                "created_at": m["created_at"],
                "message_count": m["message_count"],
                "first_user_message": m["first_user_message"],
            }
            for m in chats_metadata
        ]
    }

    output_path = output_dir / "chats_analysis_report.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(f"\n\n📄 Detailed report saved to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Analyze all chats from Limitless API"
    )
    parser.add_argument(
        "--save-raw",
        action="store_true",
        help="Save raw chat data to JSON file"
    )
    parser.add_argument(
        "--from-file",
        help="Analyze from existing raw JSON file instead of fetching"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=200,
        help="Maximum number of API pages to fetch (default: 200)"
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(__file__).parent.parent / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load or fetch chats
    if args.from_file:
        print(f"Loading chats from {args.from_file}...")
        try:
            with open(args.from_file, 'r', encoding='utf-8') as f:
                all_chats = json.load(f)
            print(f"✅ Loaded {len(all_chats)} chats from file\n")
        except Exception as e:
            print(f"❌ Error loading file: {e}")
            sys.exit(1)
    else:
        # Fetch all chats
        all_chats = fetch_all_chats(max_pages=args.max_pages)

    if not all_chats:
        print("\n❌ No chats found")
        sys.exit(1)

    # Save raw data if requested (and not loading from file)
    if args.save_raw and not args.from_file:
        raw_path = output_dir / "all_chats_raw.json"
        with open(raw_path, 'w', encoding='utf-8') as f:
            json.dump(all_chats, f, indent=2)
        print(f"\n💾 Raw chat data saved to: {raw_path}")

    # Extract metadata
    print("\nAnalyzing chat metadata...")
    chats_metadata = [analyze_chat_metadata(chat) for chat in all_chats]

    # Analyze patterns
    analysis = analyze_patterns(chats_metadata)

    # Save detailed report
    save_detailed_report(chats_metadata, analysis, output_dir)

    print("\n" + "="*60)
    print("✅ Analysis complete!")
    print("="*60)


if __name__ == "__main__":
    main()


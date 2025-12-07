#!/usr/bin/env python3
"""
Batch export Daily Insights from the Limitless API /v1/chats endpoint.

This script fetches Daily Insights for a range of dates or all available insights
and saves them as markdown files.

Usage:
    # Export for a date range
    python batch_export_insights.py START_DATE END_DATE

    # Export all available insights
    python batch_export_insights.py --all

    # Export recent insights (last N days)
    python batch_export_insights.py --recent N

Examples:
    python batch_export_insights.py 2025-11-01 2025-11-20
    python batch_export_insights.py --all
    python batch_export_insights.py --recent 30
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
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
RETRY_DELAY = 5  # seconds
REQUEST_DELAY = 0.5  # seconds between requests to respect rate limits


def fetch_all_daily_insights(max_pages=100):
    """
    Fetch all available Daily Insights from the chats endpoint.

    Args:
        max_pages: Maximum number of pages to fetch (default 100)

    Returns:
        list: List of Daily Insights chat objects
    """
    if not API_KEY:
        print("Error: LIMITLESS_API_KEY not found in environment variables.")
        return []

    endpoint = f"{API_URL}/v1/chats"
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    }

    all_insights = []
    cursor = None
    pages_fetched = 0

    print("Fetching all Daily Insights from the API...")

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
                    return all_insights

        # Filter for Daily Insights chats
        chats = data.get("data", {}).get("chats", [])

        for chat in chats:
            if chat.get("summary") == "Daily insights":
                all_insights.append(chat)

        pages_fetched += 1
        insights_count = len(all_insights)
        print(f"  Page {pages_fetched}: Found {insights_count} Daily Insights so far...")

        # Check for next page
        next_cursor = data.get("meta", {}).get("chats", {}).get("nextCursor")
        if not next_cursor:
            print(f"  Reached end of available chats")
            break

        cursor = next_cursor

        # Brief delay to respect rate limits
        time.sleep(REQUEST_DELAY)

    print(f"\n✅ Found {len(all_insights)} total Daily Insights")
    return all_insights


def extract_insights_data(chat):
    """
    Extract relevant data from a Daily Insights chat.

    Args:
        chat: The chat object

    Returns:
        dict: Extracted data including date, text, and metadata
    """
    created_at = chat.get("createdAt", "")
    chat_date = None

    if created_at:
        chat_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()

    # Extract the assistant's message (the actual insights)
    insights_text = ""
    messages = chat.get("messages", [])

    for message in messages:
        user = message.get("user", {})
        if user.get("role") == "assistant":
            insights_text = message.get("text", "")
            break

    return {
        "date": chat_date,
        "date_str": str(chat_date) if chat_date else "unknown",
        "text": insights_text,
        "chat_id": chat.get("id", ""),
        "created_at": created_at
    }


def save_insight(insight_data, output_dir):
    """
    Save a Daily Insight to a markdown file.

    Args:
        insight_data: Dictionary with insight data
        output_dir: Directory to save the file

    Returns:
        Path: Path to the saved file, or None if failed
    """
    date_str = insight_data["date_str"]

    if date_str == "unknown":
        print(f"  ⚠️  Skipping insight with unknown date")
        return None

    output_path = output_dir / f"{date_str}-daily-insights.md"

    # Skip if file already exists
    if output_path.exists():
        print(f"  ⏭️  Skipping {date_str} (file already exists)")
        return output_path

    # Add a header with metadata
    header = f"""# Daily Insights for {date_str}

*Generated by Limitless AI*
*Chat ID: {insight_data['chat_id']}*
*Created: {insight_data['created_at']}*

---

"""

    full_content = header + insight_data["text"]

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        return output_path
    except Exception as e:
        print(f"  ❌ Error saving {date_str}: {e}")
        return None


def filter_by_date_range(insights, start_date, end_date):
    """
    Filter insights by date range.

    Args:
        insights: List of insight data dictionaries
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        list: Filtered insights
    """
    filtered = []

    for insight in insights:
        insight_date = insight.get("date")
        if insight_date and start_date <= insight_date <= end_date:
            filtered.append(insight)

    return filtered


def main():
    parser = argparse.ArgumentParser(
        description="Batch export Daily Insights from Limitless API"
    )
    parser.add_argument(
        "start_date",
        nargs="?",
        help="Start date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "end_date",
        nargs="?",
        help="End date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Export all available Daily Insights"
    )
    parser.add_argument(
        "--recent",
        type=int,
        metavar="N",
        help="Export insights from the last N days"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=100,
        help="Maximum number of API pages to fetch (default: 100)"
    )

    args = parser.parse_args()

    # Determine date range
    start_date = None
    end_date = None

    if args.all:
        print("Mode: Export all available Daily Insights\n")
    elif args.recent:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=args.recent)
        print(f"Mode: Export recent {args.recent} days ({start_date} to {end_date})\n")
    elif args.start_date and args.end_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
            print(f"Mode: Export date range ({start_date} to {end_date})\n")
        except ValueError:
            print("Error: Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        print("Error: Must specify either:")
        print("  - A date range: START_DATE END_DATE")
        print("  - --all flag to export everything")
        print("  - --recent N to export last N days")
        print("\nUse --help for more information")
        sys.exit(1)

    # Create output directory
    output_dir = Path(__file__).parent.parent / "exports" / "insights"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    # Fetch all Daily Insights
    all_chats = fetch_all_daily_insights(max_pages=args.max_pages)

    if not all_chats:
        print("\n❌ No Daily Insights found")
        sys.exit(1)

    # Extract data from all insights
    print("\nProcessing insights...")
    all_insights = [extract_insights_data(chat) for chat in all_chats]

    # Filter by date range if specified
    if start_date and end_date:
        insights_to_export = filter_by_date_range(all_insights, start_date, end_date)
        print(f"  Filtered to {len(insights_to_export)} insights in date range")
    else:
        insights_to_export = all_insights

    # Sort by date
    insights_to_export.sort(key=lambda x: x["date"] if x["date"] else datetime.min.date())

    # Save each insight
    print(f"\nExporting {len(insights_to_export)} Daily Insights...\n")

    saved_count = 0
    skipped_count = 0
    error_count = 0

    for insight in insights_to_export:
        result = save_insight(insight, output_dir)

        if result:
            if "Skipping" in str(result):
                skipped_count += 1
            else:
                print(f"  ✅ Saved: {insight['date_str']}")
                saved_count += 1
        else:
            error_count += 1

    # Summary
    print(f"\n{'='*60}")
    print("Export Summary")
    print(f"{'='*60}")
    print(f"  Total found: {len(all_insights)}")
    print(f"  In date range: {len(insights_to_export)}")
    print(f"  Newly saved: {saved_count}")
    print(f"  Already existed: {skipped_count}")
    print(f"  Errors: {error_count}")
    print(f"{'='*60}")

    if saved_count > 0:
        print(f"\n✅ Successfully exported {saved_count} Daily Insights to {output_dir}")


if __name__ == "__main__":
    main()


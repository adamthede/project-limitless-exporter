#!/usr/bin/env python3
"""
Verify that your local backup covers all lifelogs on the server.
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from collections import defaultdict

env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

API_KEY = os.getenv("LIMITLESS_API_KEY")
API_URL = os.getenv("LIMITLESS_API_URL", "https://api.limitless.ai")

def fetch_all_lifelogs():
    """Fetch all lifelog metadata (IDs and dates only)."""
    endpoint = f"{API_URL}/v1/lifelogs"
    headers = {"X-API-Key": API_KEY, "Accept": "application/json"}

    all_lifelogs = []
    cursor = None

    print("📥 Fetching lifelog metadata from server...")

    while True:
        params = {"limit": 50, "includeMarkdown": "false"}
        if cursor:
            params["cursor"] = cursor

        response = requests.get(endpoint, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        lifelogs = data.get("data", {}).get("lifelogs", [])
        all_lifelogs.extend(lifelogs)

        print(f"  Fetched {len(all_lifelogs)} lifelogs...")

        next_cursor = data.get("meta", {}).get("lifelogs", {}).get("nextCursor")
        if not next_cursor:
            break
        cursor = next_cursor

    print(f"✅ Total: {len(all_lifelogs)} lifelogs\n")
    return all_lifelogs


def analyze_lifelogs(lifelogs):
    """Analyze date distribution of lifelogs."""
    by_date = defaultdict(int)
    undated = []
    earliest = None
    latest = None

    for lifelog in lifelogs:
        started_at = lifelog.get("startedAt")
        lifelog_id = lifelog.get("id")

        if not started_at:
            undated.append(lifelog_id)
            continue

        try:
            dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            date_str = dt.strftime("%Y-%m-%d")
            by_date[date_str] += 1

            if earliest is None or dt < earliest:
                earliest = dt
            if latest is None or dt > latest:
                latest = dt

        except Exception as e:
            print(f"  Warning: Could not parse date for {lifelog_id}: {started_at}")
            undated.append(lifelog_id)

    return by_date, undated, earliest, latest


def main():
    if not API_KEY:
        print("Error: LIMITLESS_API_KEY not found")
        sys.exit(1)

    # Fetch all lifelogs
    lifelogs = fetch_all_lifelogs()

    # Analyze
    by_date, undated, earliest, latest = analyze_lifelogs(lifelogs)

    # Report
    print(f"{'='*60}")
    print("Lifelog Coverage Analysis")
    print(f"{'='*60}\n")

    print(f"Total lifelogs on server: {len(lifelogs)}")
    print(f"Lifelogs with dates: {len(lifelogs) - len(undated)}")
    print(f"Lifelogs WITHOUT dates: {len(undated)}")

    if earliest and latest:
        print(f"\nDate range on server:")
        print(f"  Earliest: {earliest.strftime('%Y-%m-%d')}")
        print(f"  Latest: {latest.strftime('%Y-%m-%d')}")
        print(f"  Span: {(latest - earliest).days + 1} days")

    print(f"\nYour local backup:")
    print(f"  Date range: 2025-02-27 to 2025-12-05")
    print(f"  Files: 282 daily aggregations")

    # Check coverage
    print(f"\n{'='*60}")
    print("Coverage Assessment")
    print(f"{'='*60}\n")

    local_start = datetime(2025, 2, 27)
    local_end = datetime(2025, 12, 5)

    missing_dates = []
    outside_range = []

    for date_str, count in sorted(by_date.items()):
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if dt < local_start or dt > local_end:
            outside_range.append((date_str, count))

    if outside_range:
        print(f"⚠️  WARNING: {len(outside_range)} dates with lifelogs OUTSIDE your backup range:")
        for date_str, count in outside_range[:10]:
            print(f"  {date_str}: {count} lifelogs")
        if len(outside_range) > 10:
            print(f"  ... and {len(outside_range) - 10} more dates")
        total_outside = sum(count for _, count in outside_range)
        print(f"\n  Total lifelogs outside range: {total_outside}")
    else:
        print("✅ All dated lifelogs fall within your backup range")

    if undated:
        print(f"\n⚠️  WARNING: {len(undated)} lifelogs have NO DATE")
        print("These would NOT be captured by date-based sync!")
        print(f"\nFirst 10 undated lifelog IDs:")
        for lid in undated[:10]:
            print(f"  {lid}")
        if len(undated) > 10:
            print(f"  ... and {len(undated) - 10} more")
    else:
        print("\n✅ All lifelogs have dates")

    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}\n")

    total_missing = len(undated) + sum(count for _, count in outside_range)

    if total_missing > 0:
        print(f"⚠️  Your backup may be INCOMPLETE")
        print(f"   Missing: {total_missing} lifelogs")
        print(f"   - {len(undated)} undated")
        print(f"   - {sum(count for _, count in outside_range)} outside date range")
        print(f"\n   Run download_all_lifelogs_complete.py before deleting!")
    else:
        print("✅ Your backup appears COMPLETE")
        print("   All server lifelogs fall within your backup date range")
        print("   Safe to proceed with deletion")

    print()


if __name__ == "__main__":
    main()

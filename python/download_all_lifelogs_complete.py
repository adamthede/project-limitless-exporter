#!/usr/bin/env python3
"""
Download ALL lifelogs from the server, including those without dates.

This script fetches every single lifelog entry and saves them individually
to ensure nothing is missed before deletion.
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
import time
from datetime import datetime

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

API_KEY = os.getenv("LIMITLESS_API_KEY")
API_URL = os.getenv("LIMITLESS_API_URL", "https://api.limitless.ai")
MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_DELAY = 0.3

def fetch_all_lifelogs():
    """Fetch ALL lifelogs from the API."""
    if not API_KEY:
        print("Error: LIMITLESS_API_KEY not found")
        return []

    endpoint = f"{API_URL}/v1/lifelogs"
    headers = {"X-API-Key": API_KEY, "Accept": "application/json"}

    all_lifelogs = []
    cursor = None
    pages_fetched = 0

    print("📥 Fetching ALL lifelogs from the server...")
    print("This may take a while...\n")

    while True:
        params = {
            "limit": 50,
            "includeMarkdown": "true"  # We need the full content
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
                    return all_lifelogs

        lifelogs = data.get("data", {}).get("lifelogs", [])
        all_lifelogs.extend(lifelogs)

        pages_fetched += 1
        print(f"  Page {pages_fetched}: {len(all_lifelogs)} total lifelogs fetched...")

        next_cursor = data.get("meta", {}).get("lifelogs", {}).get("nextCursor")
        if not next_cursor:
            print(f"\n  Reached end of available lifelogs")
            break

        cursor = next_cursor
        time.sleep(REQUEST_DELAY)

    print(f"\n✅ Fetched {len(all_lifelogs)} total lifelogs\n")
    return all_lifelogs


def save_lifelog(lifelog, output_dir):
    """Save a single lifelog to file."""
    lifelog_id = lifelog.get("id", "unknown")
    started_at = lifelog.get("startedAt")
    ended_at = lifelog.get("endedAt")
    markdown = lifelog.get("markdown", "")

    # Determine filename
    if started_at:
        try:
            dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            date_str = dt.strftime("%Y-%m-%d_%H%M%S")
            filename = f"{date_str}_{lifelog_id}.md"
        except:
            filename = f"undated_{lifelog_id}.md"
    else:
        filename = f"undated_{lifelog_id}.md"

    output_path = output_dir / filename

    # Write file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Lifelog: {lifelog_id}\n\n")
            f.write(f"**Started:** {started_at or 'Unknown'}\n")
            f.write(f"**Ended:** {ended_at or 'Unknown'}\n\n")
            f.write("---\n\n")
            f.write(markdown)
        return True
    except Exception as e:
        print(f"  ❌ Error saving {lifelog_id}: {e}")
        return False


def main():
    # Create output directory
    output_dir = Path(__file__).parent.parent / "exports" / "all_lifelogs_complete"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📂 Output directory: {output_dir}\n")

    # Check existing files
    existing_files = list(output_dir.glob("*.md"))
    print(f"Found {len(existing_files)} existing lifelog files\n")

    # Fetch all lifelogs
    all_lifelogs = fetch_all_lifelogs()

    if not all_lifelogs:
        print("❌ No lifelogs found")
        sys.exit(1)

    # Save lifelogs
    print(f"💾 Saving {len(all_lifelogs)} lifelogs...\n")

    saved_count = 0
    skipped_count = 0

    for i, lifelog in enumerate(all_lifelogs, 1):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(all_lifelogs)} ({(i/len(all_lifelogs)*100):.1f}%)")

        if save_lifelog(lifelog, output_dir):
            saved_count += 1
        else:
            skipped_count += 1

    # Summary
    print(f"\n{'='*60}")
    print("Download Complete")
    print(f"{'='*60}")
    print(f"Total lifelogs: {len(all_lifelogs)}")
    print(f"Successfully saved: {saved_count}")
    print(f"Failed: {skipped_count}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")

    # Calculate size
    import subprocess
    try:
        result = subprocess.run(['du', '-sh', str(output_dir)],
                              capture_output=True, text=True)
        size = result.stdout.split()[0]
        print(f"📊 Total size: {size}\n")
    except:
        pass


if __name__ == "__main__":
    main()

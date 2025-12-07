#!/usr/bin/env python3
"""
Intelligently batch export audio for a full day using lifelog data.

This script reads your lifelog contents JSON to identify actual recording periods,
then downloads audio in optimal chunks that respect the 2-hour API limit while
avoiding silent periods.

Usage:
    python batch_export_audio.py YYYY-MM-DD
    python batch_export_audio.py 2025-11-20
    python batch_export_audio.py --yesterday
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

# API limits
MAX_DURATION_HOURS = 2
MAX_DURATION_MS = MAX_DURATION_HOURS * 60 * 60 * 1000
MIN_GAP_MINUTES = 30  # Minimum gap to consider a break between sessions


def load_lifelog_data(date_str):
    """
    Load lifelog data for a specific date.

    Tries multiple sources in order:
    1. Lifelog markdown file (exports/lifelogs/YYYY-MM-DD-lifelogs.md)
    2. Contents JSON file (exports/contents/YYYY-MM-DD-contents.json)

    Returns:
        str or list: Lifelog markdown text or contents data, or None if not found
    """
    # Try lifelog markdown first (most common)
    lifelog_path = Path(__file__).parent.parent / "exports" / "lifelogs" / f"{date_str}-lifelogs.md"

    if lifelog_path.exists():
        try:
            with open(lifelog_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"⚠️  Error reading lifelog file: {e}")

    # Fallback to contents JSON
    contents_path = Path(__file__).parent.parent / "exports" / "contents" / f"{date_str}-contents.json"

    if contents_path.exists():
        try:
            with open(contents_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Error reading contents file: {e}")

    return None


def extract_recording_periods(data):
    """
    Extract recording periods from lifelog data.

    Handles two input types:
    1. String (markdown text from lifelog file)
    2. List (contents JSON data)

    Returns:
        list: List of (start_time, end_time) tuples in datetime format
    """
    import re

    timestamps = []

    # If data is a string (lifelog markdown)
    if isinstance(data, str):
        # Parse timestamps like: "11/19/25 7:03 AM" or "- Unknown (11/19/25 7:03 AM):"
        pattern = r'(\d{1,2}/\d{1,2}/\d{2}\s+\d{1,2}:\d{2}\s+[AP]M)'
        matches = re.findall(pattern, data)

        for match in matches:
            try:
                dt = datetime.strptime(match, "%m/%d/%y %I:%M %p")
                timestamps.append(dt)
            except:
                pass

    # If data is a list (contents JSON)
    elif isinstance(data, list):
        for lifelog in data:
            contents = lifelog.get('contents', [])

            # Try structured contents array first
            if contents:
                for item in contents:
                    if 'startTime' in item:
                        try:
                            dt = datetime.fromisoformat(item['startTime'].replace('Z', '+00:00'))
                            timestamps.append(dt)
                        except:
                            pass
                    if 'endTime' in item:
                        try:
                            dt = datetime.fromisoformat(item['endTime'].replace('Z', '+00:00'))
                            timestamps.append(dt)
                        except:
                            pass

            # Fallback to parsing markdown
            if not timestamps:
                markdown = lifelog.get('full_markdown', '')
                if markdown:
                    pattern = r'(\d{1,2}/\d{1,2}/\d{2}\s+\d{1,2}:\d{2}\s+[AP]M)'
                    matches = re.findall(pattern, markdown)

                    for match in matches:
                        try:
                            dt = datetime.strptime(match, "%m/%d/%y %I:%M %p")
                            timestamps.append(dt)
                        except:
                            pass

    if not timestamps:
        return []

    # Remove duplicates and sort
    timestamps = sorted(set(timestamps))

    # Group into continuous periods (find gaps)
    periods = []
    if timestamps:
        current_start = timestamps[0]
        current_end = timestamps[0]

        for ts in timestamps[1:]:
            # If gap is less than 5 minutes, extend current period
            if (ts - current_end).total_seconds() < 300:
                current_end = ts
            else:
                # Save current period and start new one
                periods.append((current_start, current_end))
                current_start = ts
                current_end = ts

        # Add the last period
        periods.append((current_start, current_end))

    return periods


def merge_close_periods(periods, min_gap_minutes=MIN_GAP_MINUTES):
    """
    Merge recording periods that are close together.

    Args:
        periods: List of (start, end) datetime tuples
        min_gap_minutes: Minimum gap to keep periods separate

    Returns:
        list: Merged periods
    """
    if not periods:
        return []

    merged = [periods[0]]

    for start, end in periods[1:]:
        last_start, last_end = merged[-1]

        # If gap is less than min_gap_minutes, merge
        gap = (start - last_end).total_seconds() / 60
        if gap < min_gap_minutes:
            merged[-1] = (last_start, max(end, last_end))
        else:
            merged.append((start, end))

    return merged


def chunk_periods_by_duration(periods, max_hours=MAX_DURATION_HOURS):
    """
    Split periods into chunks that don't exceed max_hours.

    Returns:
        list: List of (start, end, label) tuples
    """
    chunks = []
    chunk_index = 1

    for start, end in periods:
        duration_hours = (end - start).total_seconds() / 3600

        if duration_hours <= max_hours:
            # Period fits in one chunk
            label = get_time_label(start, chunk_index)
            chunks.append((start, end, label))
            chunk_index += 1
        else:
            # Split into multiple chunks
            current_start = start
            while current_start < end:
                current_end = min(current_start + timedelta(hours=max_hours), end)
                label = get_time_label(current_start, chunk_index)
                chunks.append((current_start, current_end, label))
                current_start = current_end
                chunk_index += 1

    return chunks


def get_time_label(dt, index):
    """
    Generate a descriptive label for a time period.

    Returns:
        str: Label like "morning", "afternoon", "evening", or "session-N"
    """
    hour = dt.hour

    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    elif 21 <= hour < 24 or 0 <= hour < 5:
        return "night"
    else:
        return f"session-{index}"


def download_audio_chunk(start_dt, end_dt, output_path, verbose=True):
    """
    Download audio for a specific time chunk.

    Returns:
        bool: True if successful
    """
    if not API_KEY:
        print("❌ Error: LIMITLESS_API_KEY not found")
        return False

    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    endpoint = f"{API_URL}/v1/download-audio"

    params = {
        "startMs": start_ms,
        "endMs": end_ms,
        "audioSource": "pendant"
    }

    headers = {
        "X-API-Key": API_KEY
    }

    try:
        if verbose:
            duration_min = (end_dt - start_dt).total_seconds() / 60
            print(f"  Downloading: {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')} ({duration_min:.0f} min)...", end=" ")

        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            timeout=120,
            stream=True
        )

        if response.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = output_path.stat().st_size
            if verbose:
                print(f"✅ {file_size/1024/1024:.1f} MB")

            return True
        elif response.status_code == 404:
            if verbose:
                print(f"⚠️  No audio (404)")
            return False
        else:
            if verbose:
                print(f"❌ Error {response.status_code}")
            return False

    except Exception as e:
        if verbose:
            print(f"❌ {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Intelligently batch export audio for a full day",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script uses your lifelog contents JSON to identify actual recording periods
and downloads audio in optimal chunks.

Examples:
  python batch_export_audio.py 2025-11-20
  python batch_export_audio.py --yesterday
        """
    )

    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument(
        "date",
        nargs="?",
        help="Date in YYYY-MM-DD format"
    )
    date_group.add_argument(
        "--yesterday",
        action="store_true",
        help="Export yesterday's audio"
    )

    parser.add_argument(
        "--output-dir",
        default="exports/audio",
        help="Output directory (default: exports/audio)"
    )
    parser.add_argument(
        "--min-gap",
        type=int,
        default=MIN_GAP_MINUTES,
        help=f"Minimum gap in minutes to split sessions (default: {MIN_GAP_MINUTES})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce verbosity"
    )

    args = parser.parse_args()

    # Determine date
    if args.yesterday:
        date_dt = datetime.now() - timedelta(days=1)
        date_str = date_dt.strftime("%Y-%m-%d")
    else:
        date_str = args.date
        try:
            date_dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print("❌ Error: Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Batch Audio Export for {date_str}")
    print(f"{'='*60}\n")

    # Step 1: Load lifelog data
    if not args.quiet:
        print(f"📂 Loading lifelog data...")

    lifelog_data = load_lifelog_data(date_str)

    if not lifelog_data:
        print(f"❌ No lifelog data found for {date_str}")
        print(f"   Expected: exports/lifelogs/{date_str}-lifelogs.md")
        print(f"   Or: exports/contents/{date_str}-contents.json")
        print(f"\n💡 First export the lifelog:")
        print(f"   python export_day_lifelogs.py {date_str}")
        sys.exit(1)

    if not args.quiet:
        if isinstance(lifelog_data, str):
            print(f"   Loaded lifelog markdown ({len(lifelog_data):,} characters)")
        else:
            print(f"   Loaded {len(lifelog_data)} lifelog entries from JSON")

    # Step 2: Extract recording periods
    if not args.quiet:
        print(f"\n🔍 Analyzing recording periods...")

    periods = extract_recording_periods(lifelog_data)

    if not periods:
        print(f"❌ No recording periods found in contents")
        sys.exit(1)

    if not args.quiet:
        print(f"   Found {len(periods)} recording periods")

    # Step 3: Merge close periods
    merged_periods = merge_close_periods(periods, args.min_gap)

    if not args.quiet:
        print(f"   Merged to {len(merged_periods)} sessions (gaps > {args.min_gap} min)")

    # Step 4: Chunk by duration
    chunks = chunk_periods_by_duration(merged_periods)

    if not args.quiet:
        print(f"   Split into {len(chunks)} downloadable chunks (<{MAX_DURATION_HOURS}h each)")

    # Step 5: Display plan
    print(f"\n📋 Download Plan:")
    print(f"{'='*60}")

    total_duration = timedelta()
    output_dir = Path(__file__).parent.parent / args.output_dir

    for i, (start, end, label) in enumerate(chunks, 1):
        duration = end - start
        total_duration += duration

        filename = f"{date_str}-{label}-{start.strftime('%H%M')}.ogg"
        output_path = output_dir / filename

        duration_min = duration.total_seconds() / 60
        print(f"{i:2d}. {start.strftime('%H:%M')} - {end.strftime('%H:%M')} "
              f"({duration_min:4.0f} min) → {filename}")

    print(f"{'='*60}")
    print(f"Total audio duration: {total_duration.total_seconds()/3600:.1f} hours")
    print(f"Total chunks: {len(chunks)}")

    if args.dry_run:
        print(f"\n🔍 Dry run complete. Use without --dry-run to download.")
        sys.exit(0)

    # Step 6: Download
    print(f"\n⬇️  Downloading audio...")
    print(f"{'='*60}\n")

    success_count = 0
    skip_count = 0
    error_count = 0

    for i, (start, end, label) in enumerate(chunks, 1):
        filename = f"{date_str}-{label}-{start.strftime('%H%M')}.ogg"
        output_path = output_dir / filename

        if output_path.exists():
            if not args.quiet:
                print(f"{i:2d}. {filename}")
                print(f"    ⏭️  Already exists, skipping")
            skip_count += 1
            continue

        if not args.quiet:
            print(f"{i:2d}. {filename}")

        success = download_audio_chunk(start, end, output_path, verbose=not args.quiet)

        if success:
            success_count += 1
        else:
            error_count += 1

        # Brief delay between downloads
        if i < len(chunks):
            time.sleep(1)

    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"  Successfully downloaded: {success_count}")
    print(f"  Already existed: {skip_count}")
    print(f"  Errors/No audio: {error_count}")
    print(f"{'='*60}")

    if success_count > 0:
        print(f"\n✅ Audio files saved to: {output_dir}")
        print(f"\n💡 To play:")
        print(f"   open {output_dir}/{date_str}-*.ogg")


if __name__ == "__main__":
    main()


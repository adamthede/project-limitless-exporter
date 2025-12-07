#!/usr/bin/env python3
"""
Batch export audio for an entire month or date range.

This script downloads audio for multiple days, organizing files by date
in a clean directory structure.

Usage:
    # Export entire month
    python batch_export_audio_month.py 2025-11

    # Export date range
    python batch_export_audio_month.py 2025-11-01 2025-11-30

    # Export specific dates with options
    python batch_export_audio_month.py 2025-11-15 2025-11-20 --dry-run
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
import re
from calendar import monthrange

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
MIN_GAP_MINUTES = 30


def load_lifelog_markdown(date_str):
    """Load lifelog markdown file for a specific date."""
    lifelog_path = Path(__file__).parent.parent / "exports" / "lifelogs" / f"{date_str}-lifelogs.md"

    if not lifelog_path.exists():
        return None

    try:
        with open(lifelog_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return None


def extract_recording_periods(markdown_text):
    """
    Extract recording periods from lifelog markdown.

    Returns:
        list: List of (start_time, end_time) tuples
    """
    if not markdown_text:
        return []

    timestamps = []

    # Parse timestamps like: "11/19/25 7:03 AM"
    pattern = r'(\d{1,2}/\d{1,2}/\d{2}\s+\d{1,2}:\d{2}\s+[AP]M)'
    matches = re.findall(pattern, markdown_text)

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

    # Group into continuous periods
    periods = []
    if timestamps:
        current_start = timestamps[0]
        current_end = timestamps[0]

        for ts in timestamps[1:]:
            if (ts - current_end).total_seconds() < 300:  # 5 min gap
                current_end = ts
            else:
                periods.append((current_start, current_end))
                current_start = ts
                current_end = ts

        periods.append((current_start, current_end))

    return periods


def merge_close_periods(periods, min_gap_minutes=MIN_GAP_MINUTES):
    """Merge recording periods that are close together."""
    if not periods:
        return []

    merged = [periods[0]]

    for start, end in periods[1:]:
        last_start, last_end = merged[-1]
        gap = (start - last_end).total_seconds() / 60

        if gap < min_gap_minutes:
            merged[-1] = (last_start, max(end, last_end))
        else:
            merged.append((start, end))

    return merged


def chunk_periods_by_duration(periods, max_hours=MAX_DURATION_HOURS):
    """Split periods into chunks that don't exceed max_hours."""
    chunks = []
    chunk_index = 1

    for start, end in periods:
        duration_hours = (end - start).total_seconds() / 3600

        if duration_hours <= max_hours:
            label = get_time_label(start, chunk_index)
            chunks.append((start, end, label))
            chunk_index += 1
        else:
            current_start = start
            while current_start < end:
                current_end = min(current_start + timedelta(hours=max_hours), end)
                label = get_time_label(current_start, chunk_index)
                chunks.append((current_start, current_end, label))
                current_start = current_end
                chunk_index += 1

    return chunks


def get_time_label(dt, index):
    """Generate a descriptive label for a time period."""
    hour = dt.hour

    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def download_audio_chunk(start_dt, end_dt, output_path, verbose=True):
    """Download audio for a specific time chunk."""
    if not API_KEY:
        return False

    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    endpoint = f"{API_URL}/v1/download-audio"
    params = {
        "startMs": start_ms,
        "endMs": end_ms,
        "audioSource": "pendant"
    }
    headers = {"X-API-Key": API_KEY}

    try:
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

            return True
        else:
            return False

    except Exception as e:
        return False


def process_single_day(date_str, base_output_dir, dry_run=False, verbose=False):
    """
    Process audio export for a single day.

    Returns:
        dict: Statistics about the export
    """
    # Load lifelog
    markdown = load_lifelog_markdown(date_str)

    if not markdown:
        return {
            "date": date_str,
            "status": "no_lifelog",
            "chunks": 0,
            "downloaded": 0,
            "skipped": 0,
            "errors": 0
        }

    # Extract and process periods
    periods = extract_recording_periods(markdown)
    if not periods:
        return {
            "date": date_str,
            "status": "no_recordings",
            "chunks": 0,
            "downloaded": 0,
            "skipped": 0,
            "errors": 0
        }

    merged = merge_close_periods(periods)
    chunks = chunk_periods_by_duration(merged)

    # Create day-specific output directory
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    year_month = date_obj.strftime("%Y-%m")
    day_dir = base_output_dir / year_month / date_str

    stats = {
        "date": date_str,
        "status": "success",
        "chunks": len(chunks),
        "downloaded": 0,
        "skipped": 0,
        "errors": 0,
        "duration_hours": sum((end - start).total_seconds() for start, end, _ in chunks) / 3600
    }

    if dry_run:
        return stats

    # Download chunks
    for start, end, label in chunks:
        filename = f"{date_str}-{label}-{start.strftime('%H%M')}.ogg"
        output_path = day_dir / filename

        if output_path.exists():
            stats["skipped"] += 1
            if verbose:
                print(f"    ⏭️  {filename}")
            continue

        if verbose:
            duration_min = (end - start).total_seconds() / 60
            print(f"    ⬇️  {start.strftime('%H:%M')}-{end.strftime('%H:%M')} ({duration_min:.0f}m)...", end=" ")

        success = download_audio_chunk(start, end, output_path, verbose=False)

        if success:
            stats["downloaded"] += 1
            if verbose:
                file_size = output_path.stat().st_size
                print(f"✅ {file_size/1024/1024:.1f}MB")
        else:
            stats["errors"] += 1
            if verbose:
                print(f"❌")

        # Brief delay between downloads
        time.sleep(1)

    return stats


def generate_date_range(start_date, end_date):
    """Generate list of dates between start and end (inclusive)."""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


def main():
    parser = argparse.ArgumentParser(
        description="Batch export audio for multiple days",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export entire month
  python batch_export_audio_month.py 2025-11

  # Export date range
  python batch_export_audio_month.py 2025-11-01 2025-11-30

  # Dry run to see plan
  python batch_export_audio_month.py 2025-11 --dry-run

  # Verbose output
  python batch_export_audio_month.py 2025-11-15 2025-11-20 --verbose
        """
    )

    parser.add_argument(
        "start",
        help="Start date (YYYY-MM-DD) or month (YYYY-MM)"
    )
    parser.add_argument(
        "end",
        nargs="?",
        help="End date (YYYY-MM-DD), optional if month specified"
    )
    parser.add_argument(
        "--output-dir",
        default="exports/audio",
        help="Base output directory (default: exports/audio)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without downloading"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed progress for each file"
    )

    args = parser.parse_args()

    # Parse date range
    if len(args.start) == 7:  # YYYY-MM format (month)
        try:
            year, month = map(int, args.start.split('-'))
            start_date = datetime(year, month, 1)
            last_day = monthrange(year, month)[1]
            end_date = datetime(year, month, last_day)
        except ValueError:
            print("❌ Error: Invalid month format. Use YYYY-MM")
            sys.exit(1)
    elif args.end:  # Date range
        try:
            start_date = datetime.strptime(args.start, "%Y-%m-%d")
            end_date = datetime.strptime(args.end, "%Y-%m-%d")
        except ValueError:
            print("❌ Error: Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        print("❌ Error: Specify either a month (YYYY-MM) or date range (START END)")
        sys.exit(1)

    # Generate date list
    dates = generate_date_range(start_date, end_date)

    print(f"\n{'='*60}")
    print(f"Batch Audio Export")
    print(f"{'='*60}")
    print(f"Date range: {dates[0]} to {dates[-1]}")
    print(f"Total days: {len(dates)}")
    if args.dry_run:
        print(f"Mode: DRY RUN")
    print(f"{'='*60}\n")

    # Process each day
    base_output_dir = Path(__file__).parent.parent / args.output_dir

    all_stats = []
    total_chunks = 0
    total_downloaded = 0
    total_skipped = 0
    total_errors = 0
    total_duration = 0
    days_with_audio = 0
    days_no_lifelog = 0
    days_no_recordings = 0

    for i, date_str in enumerate(dates, 1):
        print(f"[{i}/{len(dates)}] {date_str}...", end=" ")

        stats = process_single_day(date_str, base_output_dir, dry_run=args.dry_run, verbose=args.verbose)
        all_stats.append(stats)

        if stats["status"] == "no_lifelog":
            print("⚠️  No lifelog")
            days_no_lifelog += 1
        elif stats["status"] == "no_recordings":
            print("⚠️  No recordings")
            days_no_recordings += 1
        else:
            total_chunks += stats["chunks"]
            total_downloaded += stats["downloaded"]
            total_skipped += stats["skipped"]
            total_errors += stats["errors"]
            total_duration += stats["duration_hours"]
            days_with_audio += 1

            if not args.verbose:
                print(f"✅ {stats['chunks']} chunks ({stats['duration_hours']:.1f}h) - "
                      f"Downloaded: {stats['downloaded']}, Skipped: {stats['skipped']}")

    # Summary
    print(f"\n{'='*60}")
    print("Export Summary")
    print(f"{'='*60}")
    print(f"  Total days processed: {len(dates)}")
    print(f"  Days with audio: {days_with_audio}")
    print(f"  Days without lifelog: {days_no_lifelog}")
    print(f"  Days without recordings: {days_no_recordings}")
    print(f"\n  Total audio chunks: {total_chunks}")
    print(f"  Total duration: {total_duration:.1f} hours")

    if not args.dry_run:
        print(f"\n  Downloaded: {total_downloaded}")
        print(f"  Skipped (existed): {total_skipped}")
        print(f"  Errors: {total_errors}")

    print(f"{'='*60}")

    if args.dry_run:
        print(f"\n🔍 Dry run complete. Use without --dry-run to download.")
        print(f"\n💡 Estimated download:")
        print(f"   {total_chunks} files")
        print(f"   ~{total_duration * 1.5:.0f} MB (approximate)")
    else:
        print(f"\n✅ Export complete!")
        print(f"\n📂 Archive structure:")
        print(f"   {base_output_dir}/")

        # Show directory structure
        year_months = set()
        for stat in all_stats:
            if stat["status"] == "success":
                date_obj = datetime.strptime(stat["date"], "%Y-%m-%d")
                year_months.add(date_obj.strftime("%Y-%m"))

        for ym in sorted(year_months):
            print(f"     {ym}/")
            # Show sample dates
            dates_in_month = [s["date"] for s in all_stats if s["status"] == "success" and s["date"].startswith(ym)]
            for date in sorted(dates_in_month)[:3]:
                print(f"       {date}/")
                print(f"         {date}-morning-HHMM.ogg")
                print(f"         {date}-afternoon-HHMM.ogg")
                print(f"         ...")
                break  # Just show one example
            if len(dates_in_month) > 1:
                print(f"       ... ({len(dates_in_month)} days)")


if __name__ == "__main__":
    main()


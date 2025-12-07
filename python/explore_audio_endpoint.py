#!/usr/bin/env python3
"""
Explore and download audio from the Limitless API.

Based on official Limitless API documentation:
https://limitless.ai/developers/docs/api

The GET /v1/download-audio endpoint downloads audio recordings from your Pendant
in Ogg Opus format for a specified time range (max 2 hours per request).

Usage:
    # Download audio for a specific date (full day)
    python explore_audio_endpoint.py --date 2025-11-20

    # Download audio for a specific time range
    python explore_audio_endpoint.py --start "2025-11-20 09:00" --end "2025-11-20 11:00"

    # Test endpoint without downloading
    python explore_audio_endpoint.py --date 2025-11-20 --test-only
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

# API limits from documentation
MAX_DURATION_HOURS = 2
MAX_DURATION_MS = MAX_DURATION_HOURS * 60 * 60 * 1000


def download_audio(start_ms, end_ms, output_path, test_only=False, verbose=True):
    """
    Download audio from Limitless API for a specific time range.

    Args:
        start_ms: Start time in milliseconds (Unix timestamp)
        end_ms: End time in milliseconds (Unix timestamp)
        output_path: Path to save the audio file
        test_only: If True, only test the endpoint without downloading
        verbose: Print detailed information

    Returns:
        bool: True if successful, False otherwise
    """
    if not API_KEY:
        print("❌ Error: LIMITLESS_API_KEY not found in environment variables.")
        return False

    # Validate duration
    duration_ms = end_ms - start_ms
    if duration_ms > MAX_DURATION_MS:
        print(f"⚠️  Warning: Duration ({duration_ms/1000/60:.1f} minutes) exceeds max ({MAX_DURATION_HOURS} hours)")
        print(f"   The API will reject this request. Consider splitting into smaller chunks.")
        if not test_only:
            return False

    endpoint = f"{API_URL}/v1/download-audio"

    params = {
        "startMs": start_ms,
        "endMs": end_ms,
        "audioSource": "pendant"  # Currently only pendant is supported
    }

    headers = {
        "X-API-Key": API_KEY
    }

    if verbose:
        start_dt = datetime.fromtimestamp(start_ms / 1000)
        end_dt = datetime.fromtimestamp(end_ms / 1000)
        duration_min = duration_ms / 1000 / 60

        print(f"\n{'='*60}")
        print(f"Limitless Audio Download")
        print(f"{'='*60}")
        print(f"Endpoint: {endpoint}")
        print(f"Time Range:")
        print(f"  Start: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  End:   {end_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Duration: {duration_min:.1f} minutes")
        if test_only:
            print(f"Mode: TEST ONLY (not downloading)")
        print(f"{'='*60}\n")

    try:
        if verbose:
            print("Making API request...")

        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            timeout=60,  # Longer timeout for audio download
            stream=True  # Stream for large files
        )

        status_code = response.status_code

        if verbose:
            print(f"Status Code: {status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"Content-Length: {response.headers.get('Content-Length', 'N/A')} bytes")

        if status_code == 200:
            if test_only:
                print("\n✅ SUCCESS! Audio endpoint is working.")
                print(f"   Audio is available for this time range.")
                print(f"   File size: {response.headers.get('Content-Length', 'unknown')} bytes")
                return True

            # Download the audio file
            if verbose:
                print(f"\nDownloading audio to: {output_path}")

            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = output_path.stat().st_size

            if verbose:
                print(f"✅ Audio downloaded successfully!")
                print(f"   File: {output_path}")
                print(f"   Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
                print(f"   Format: Ogg Opus")

            return True

        elif status_code == 400:
            print(f"\n❌ Bad Request (400)")
            print(f"   The time range may be invalid or exceed the 2-hour limit.")
            try:
                error_data = response.json()
                print(f"   Error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Response: {response.text[:200]}")
            return False

        elif status_code == 404:
            print(f"\n⚠️  Not Found (404)")
            print(f"   No audio available for this time range.")
            print(f"   This could mean:")
            print(f"   - No recordings during this time")
            print(f"   - Time range is outside your recording history")
            return False

        elif status_code == 403:
            print(f"\n❌ Forbidden (403)")
            print(f"   Your API key may not have access to audio downloads.")
            return False

        else:
            print(f"\n❌ Unexpected status code: {status_code}")
            print(f"   Response: {response.text[:200]}")
            return False

    except requests.exceptions.Timeout:
        print(f"\n❌ Request timeout")
        print(f"   Audio download took too long. Try a shorter time range.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


def parse_datetime(date_str, time_str=None):
    """Parse date and optional time string to datetime."""
    if time_str:
        dt_str = f"{date_str} {time_str}"
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    else:
        return datetime.strptime(date_str, "%Y-%m-%d")


def main():
    parser = argparse.ArgumentParser(
        description="Download audio from Limitless API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download audio for a full day
  python explore_audio_endpoint.py --date 2025-11-20

  # Download audio for specific time range
  python explore_audio_endpoint.py --start "2025-11-20 09:00" --end "2025-11-20 11:00"

  # Test without downloading
  python explore_audio_endpoint.py --date 2025-11-20 --test-only

  # Yesterday's audio
  python explore_audio_endpoint.py --yesterday
        """
    )

    # Time range options
    time_group = parser.add_mutually_exclusive_group(required=True)
    time_group.add_argument(
        "--date",
        help="Date in YYYY-MM-DD format (downloads full day)"
    )
    time_group.add_argument(
        "--yesterday",
        action="store_true",
        help="Download yesterday's audio"
    )
    time_group.add_argument(
        "--start",
        help="Start time in 'YYYY-MM-DD HH:MM' format (requires --end)"
    )

    parser.add_argument(
        "--end",
        help="End time in 'YYYY-MM-DD HH:MM' format (requires --start)"
    )
    parser.add_argument(
        "--output-dir",
        default="exports/audio",
        help="Output directory for audio files (default: exports/audio)"
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Test endpoint without downloading audio"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce verbosity"
    )

    args = parser.parse_args()

    # Determine time range
    if args.start and args.end:
        try:
            start_dt = datetime.strptime(args.start, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(args.end, "%Y-%m-%d %H:%M")
        except ValueError:
            print("❌ Error: Invalid date/time format. Use 'YYYY-MM-DD HH:MM'")
            sys.exit(1)
    elif args.start or args.end:
        print("❌ Error: --start and --end must be used together")
        sys.exit(1)
    elif args.yesterday:
        yesterday = datetime.now() - timedelta(days=1)
        start_dt = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:  # args.date
        try:
            date_dt = datetime.strptime(args.date, "%Y-%m-%d")
            start_dt = date_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = date_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError:
            print("❌ Error: Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)

    # Convert to milliseconds
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    # Check if duration exceeds limit
    duration_hours = (end_ms - start_ms) / 1000 / 60 / 60
    if duration_hours > MAX_DURATION_HOURS:
        print(f"\n⚠️  Warning: Time range ({duration_hours:.1f} hours) exceeds API limit ({MAX_DURATION_HOURS} hours)")
        print(f"   The API will reject this request.")
        print(f"\n💡 Suggestion: Use a shorter time range, such as:")
        print(f"   python explore_audio_endpoint.py --start \"{start_dt.strftime('%Y-%m-%d %H:%M')}\" --end \"{(start_dt + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')}\"")
        sys.exit(1)

    # Determine output filename
    output_dir = Path(__file__).parent.parent / args.output_dir
    date_str = start_dt.strftime("%Y-%m-%d")
    time_str = start_dt.strftime("%H%M") if start_dt.hour != 0 or start_dt.minute != 0 else "full-day"
    output_filename = f"{date_str}-{time_str}.ogg"
    output_path = output_dir / output_filename

    # Download audio
    success = download_audio(
        start_ms,
        end_ms,
        output_path,
        test_only=args.test_only,
        verbose=not args.quiet
    )

    if not success:
        sys.exit(1)

    if not args.test_only and not args.quiet:
        print(f"\n{'='*60}")
        print("Next Steps:")
        print(f"{'='*60}")
        print(f"1. Play the audio file:")
        print(f"   open {output_path}")
        print(f"\n2. Convert to MP3 (requires ffmpeg):")
        print(f"   ffmpeg -i {output_path} {output_path.with_suffix('.mp3')}")
        print(f"\n3. Download more audio:")
        print(f"   python explore_audio_endpoint.py --date YYYY-MM-DD")


if __name__ == "__main__":
    main()

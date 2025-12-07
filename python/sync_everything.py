#!/usr/bin/env python3
"""
Master orchestrator script for syncing all Limitless data.

This script runs a complete sync workflow in the correct order:
1. Export lifelogs (raw transcripts)
2. Export contents JSON (structured data)
3. Sync all chats (conversations)
4. Export audio (recordings)
5. Run daily analytics
6. Run monthly analytics

Usage:
    # Sync everything for missing days up to yesterday
    python sync_everything.py

    # Sync specific date range
    python sync_everything.py --start 2025-11-01 --end 2025-11-20

    # Sync specific month
    python sync_everything.py --month 2025-11

    # Dry run to see what would be synced
    python sync_everything.py --dry-run

    # Skip certain steps
    python sync_everything.py --skip-audio --skip-analytics
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from calendar import monthrange
import json

# Color codes for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{Colors.END}\n")


def print_step(step_num, total_steps, description):
    """Print a step header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}[Step {step_num}/{total_steps}] {description}{Colors.END}")
    print(f"{'-'*60}")


def print_success(message):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_warning(message):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


def print_error(message):
    """Print error message."""
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def run_script(script_name, args=None, description=None, dry_run=False):
    """
    Run a Python script and capture its output.

    Returns:
        tuple: (success, output)
    """
    if description:
        print(f"   {description}...")

    cmd = [sys.executable, script_name]
    if args:
        cmd.extend(args)

    if dry_run and '--dry-run' not in cmd:
        cmd.append('--dry-run')

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout per script
        )

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Script timeout (10 minutes)"
    except Exception as e:
        return False, str(e)


def find_missing_dates(start_date, end_date, export_type="lifelogs"):
    """
    Find dates that are missing from exports.

    Args:
        start_date: Start date
        end_date: End date
        export_type: Type of export to check ("lifelogs", "contents", "analytics")

    Returns:
        list: List of missing date strings
    """
    exports_dir = Path(__file__).parent.parent / "exports"

    if export_type == "lifelogs":
        check_dir = exports_dir / "lifelogs"
        pattern = "{date}-lifelogs.md"
    elif export_type == "contents":
        check_dir = exports_dir / "contents"
        pattern = "{date}-contents.json"
    elif export_type == "analytics":
        check_dir = exports_dir / "analytics"
        pattern = "{date}-analytics.md"
    else:
        return []

    missing = []
    current = start_date

    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        filename = pattern.format(date=date_str)
        file_path = check_dir / filename

        if not file_path.exists():
            missing.append(date_str)

        current += timedelta(days=1)

    return missing


def determine_date_range(args):
    """
    Determine the date range to process based on arguments.

    Returns:
        tuple: (start_date, end_date, description)
    """
    if args.month:
        # Parse month (YYYY-MM)
        try:
            year, month = map(int, args.month.split('-'))
            start_date = datetime(year, month, 1)
            last_day = monthrange(year, month)[1]
            end_date = datetime(year, month, last_day)
            description = f"month {args.month}"
        except ValueError:
            print_error("Invalid month format. Use YYYY-MM")
            sys.exit(1)
    elif args.start and args.end:
        # Parse date range
        try:
            start_date = datetime.strptime(args.start, "%Y-%m-%d")
            end_date = datetime.strptime(args.end, "%Y-%m-%d")
            description = f"range {args.start} to {args.end}"
        except ValueError:
            print_error("Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        # Default: Find missing dates up to yesterday
        yesterday = datetime.now() - timedelta(days=1)

        # Find earliest lifelog
        lifelogs_dir = Path(__file__).parent.parent / "exports" / "lifelogs"
        if lifelogs_dir.exists():
            lifelog_files = sorted(lifelogs_dir.glob("*-lifelogs.md"))
            if lifelog_files:
                first_file = lifelog_files[0].stem.replace("-lifelogs", "")
                try:
                    start_date = datetime.strptime(first_file, "%Y-%m-%d")
                except:
                    start_date = yesterday - timedelta(days=30)
            else:
                start_date = yesterday - timedelta(days=30)
        else:
            start_date = yesterday - timedelta(days=30)

        end_date = yesterday
        description = f"missing days from {start_date.strftime('%Y-%m-%d')} to yesterday"

    return start_date, end_date, description


def main():
    parser = argparse.ArgumentParser(
        description="Master sync script for all Limitless data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync everything (auto-detect missing)
  python sync_everything.py

  # Sync specific month
  python sync_everything.py --month 2025-11

  # Sync date range
  python sync_everything.py --start 2025-11-01 --end 2025-11-20

  # Dry run
  python sync_everything.py --month 2025-11 --dry-run

  # Skip certain steps
  python sync_everything.py --skip-audio --skip-analytics
        """
    )

    # Date range options
    parser.add_argument(
        "--month",
        help="Month to sync in YYYY-MM format"
    )
    parser.add_argument(
        "--start",
        help="Start date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--end",
        help="End date in YYYY-MM-DD format"
    )

    # Options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without actually syncing"
    )
    parser.add_argument(
        "--skip-lifelogs",
        action="store_true",
        help="Skip lifelog export"
    )
    parser.add_argument(
        "--skip-contents",
        action="store_true",
        help="Skip contents JSON export"
    )
    parser.add_argument(
        "--skip-chats",
        action="store_true",
        help="Skip chat sync"
    )
    parser.add_argument(
        "--skip-audio",
        action="store_true",
        help="Skip audio export"
    )
    parser.add_argument(
        "--skip-analytics",
        action="store_true",
        help="Skip analytics generation"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output from each script"
    )

    args = parser.parse_args()

    # Determine date range
    start_date, end_date, description = determine_date_range(args)

    # Print header
    print_header("🔄 Limitless Complete Sync")
    print(f"Date range: {description}")
    print(f"Start: {start_date.strftime('%Y-%m-%d')}")
    print(f"End: {end_date.strftime('%Y-%m-%d')}")
    print(f"Total days: {(end_date - start_date).days + 1}")
    if args.dry_run:
        print(f"\n{Colors.YELLOW}🔍 DRY RUN MODE - No data will be downloaded{Colors.END}")
    print()

    # Calculate steps
    total_steps = 7  # Added index generation
    current_step = 0

    # Track statistics
    stats = {
        "lifelogs": {"success": False, "count": 0},
        "contents": {"success": False, "count": 0},
        "chats": {"success": False, "count": 0},
        "audio": {"success": False, "count": 0},
        "daily_analytics": {"success": False, "count": 0},
        "monthly_analytics": {"success": False, "count": 0}
    }

    # Step 1: Export Lifelogs
    current_step += 1
    if not args.skip_lifelogs:
        print_step(current_step, total_steps, "Export Lifelogs (Raw Transcripts)")

        # Find missing lifelogs
        missing_lifelogs = find_missing_dates(start_date, end_date, "lifelogs")

        if missing_lifelogs:
            print(f"   Found {len(missing_lifelogs)} days without lifelogs")

            if not args.dry_run:
                # Run batch_process_days for lifelogs only
                success, output = run_script(
                    "batch_process_days.py",
                    [missing_lifelogs[0], missing_lifelogs[-1], "--skip-summary"],
                    "Exporting lifelogs",
                    dry_run=False
                )

                if success:
                    print_success(f"Exported {len(missing_lifelogs)} lifelogs")
                    stats["lifelogs"]["success"] = True
                    stats["lifelogs"]["count"] = len(missing_lifelogs)
                else:
                    print_error("Lifelog export failed")
                    if args.verbose:
                        print(output)
            else:
                print_success(f"Would export {len(missing_lifelogs)} lifelogs")
        else:
            print_success("All lifelogs already exported")
            stats["lifelogs"]["success"] = True
    else:
        print_step(current_step, total_steps, "Export Lifelogs - SKIPPED")

    # Step 2: Export Contents JSON
    current_step += 1
    if not args.skip_contents:
        print_step(current_step, total_steps, "Export Contents JSON (Structured Data)")

        missing_contents = find_missing_dates(start_date, end_date, "contents")

        if missing_contents:
            print(f"   Found {len(missing_contents)} days without contents JSON")

            if not args.dry_run:
                success, output = run_script(
                    "batch_export_contents_json.py",
                    [missing_contents[0], missing_contents[-1]],
                    "Exporting contents JSON",
                    dry_run=False
                )

                if success:
                    print_success(f"Exported {len(missing_contents)} contents files")
                    stats["contents"]["success"] = True
                    stats["contents"]["count"] = len(missing_contents)
                else:
                    print_error("Contents export failed")
                    if args.verbose:
                        print(output)
            else:
                print_success(f"Would export {len(missing_contents)} contents files")
        else:
            print_success("All contents JSON already exported")
            stats["contents"]["success"] = True
    else:
        print_step(current_step, total_steps, "Export Contents JSON - SKIPPED")

    # Step 3: Sync All Chats
    current_step += 1
    if not args.skip_chats:
        print_step(current_step, total_steps, "Sync All Chats")

        if not args.dry_run:
            success, output = run_script(
                "sync_all_chats.py",
                [],
                "Syncing chats",
                dry_run=False
            )

            if success:
                # Parse output to get count
                if "new chats:" in output:
                    import re
                    match = re.search(r'Total new chats:\s+(\d+)', output)
                    if match:
                        count = int(match.group(1))
                        stats["chats"]["count"] = count
                        if count > 0:
                            print_success(f"Synced {count} new chats")
                        else:
                            print_success("All chats already synced")
                else:
                    print_success("Chat sync completed")
                stats["chats"]["success"] = True
            else:
                print_error("Chat sync failed")
                if args.verbose:
                    print(output)
        else:
            print_success("Would sync new chats")
    else:
        print_step(current_step, total_steps, "Sync All Chats - SKIPPED")

    # Step 4: Export Audio
    current_step += 1
    if not args.skip_audio:
        print_step(current_step, total_steps, "Export Audio Recordings")

        # Determine which days need audio
        date_list = []
        current = start_date
        while current <= end_date:
            date_list.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        print(f"   Processing {len(date_list)} days for audio export")

        if not args.dry_run:
            # Use batch_export_audio_month for efficiency
            if args.month:
                success, output = run_script(
                    "batch_export_audio_month.py",
                    [args.month],
                    "Exporting audio by month",
                    dry_run=False
                )
            else:
                success, output = run_script(
                    "batch_export_audio_month.py",
                    [date_list[0], date_list[-1]],
                    "Exporting audio by date range",
                    dry_run=False
                )

            if success:
                # Parse output for statistics
                if "Successfully downloaded:" in output:
                    import re
                    match = re.search(r'Successfully downloaded:\s+(\d+)', output)
                    if match:
                        count = int(match.group(1))
                        stats["audio"]["count"] = count
                        if count > 0:
                            print_success(f"Downloaded {count} audio files")
                        else:
                            print_success("All audio already downloaded")
                else:
                    print_success("Audio export completed")
                stats["audio"]["success"] = True
            else:
                print_error("Audio export failed")
                if args.verbose:
                    print(output)
        else:
            print_success(f"Would export audio for {len(date_list)} days")
    else:
        print_step(current_step, total_steps, "Export Audio - SKIPPED")

    # Step 5: Run Daily Analytics
    current_step += 1
    if not args.skip_analytics:
        print_step(current_step, total_steps, "Generate Daily Analytics")

        missing_analytics = find_missing_dates(start_date, end_date, "analytics")

        if missing_analytics:
            print(f"   Found {len(missing_analytics)} days without analytics")

            if not args.dry_run:
                success, output = run_script(
                    "analyze_daily_usage.py",
                    [missing_analytics[0], missing_analytics[-1]],
                    "Generating daily analytics",
                    dry_run=False
                )

                if success:
                    print_success(f"Generated analytics for {len(missing_analytics)} days")
                    stats["daily_analytics"]["success"] = True
                    stats["daily_analytics"]["count"] = len(missing_analytics)
                else:
                    print_warning("Daily analytics failed (may need contents JSON)")
                    if args.verbose:
                        print(output)
            else:
                print_success(f"Would generate analytics for {len(missing_analytics)} days")
        else:
            print_success("All daily analytics already generated")
            stats["daily_analytics"]["success"] = True
    else:
        print_step(current_step, total_steps, "Generate Daily Analytics - SKIPPED")

    # Step 6: Run Monthly Analytics
    current_step += 1
    if not args.skip_analytics:
        print_step(current_step, total_steps, "Generate Monthly Analytics")

        # Determine which months to process
        months = set()
        current = start_date
        while current <= end_date:
            months.add(current.strftime("%Y-%m"))
            current = current.replace(day=1) + timedelta(days=32)
            current = current.replace(day=1)

        print(f"   Processing {len(months)} month(s)")

        if not args.dry_run:
            success, output = run_script(
                "analyze_monthly_usage.py",
                [],
                "Generating monthly analytics",
                dry_run=False
            )

            if success:
                print_success(f"Generated monthly analytics")
                stats["monthly_analytics"]["success"] = True
            else:
                print_warning("Monthly analytics failed")
                if args.verbose:
                    print(output)
        else:
            print_success(f"Would generate analytics for {len(months)} month(s)")
    else:
        print_step(current_step, total_steps, "Generate Monthly Analytics - SKIPPED")

    # Step 7: Generate Obsidian Indexes
    current_step += 1
    print_step(current_step, total_steps, "Generate Obsidian Indexes")

    if not args.dry_run:
        success, output = run_script(
            "generate_index.py",
            ["--rebuild-all"],
            "Generating navigation indexes",
            dry_run=False
        )

        if success:
            print_success("Generated Obsidian index files")
        else:
            print_warning("Index generation failed")
            if args.verbose:
                print(output)
    else:
        print_success("Would generate Obsidian index files")

    # Final Summary
    print_header("📊 Sync Complete!")

    print("Results:")
    print(f"  {'Lifelogs:':20s} {'✅' if stats['lifelogs']['success'] else '❌'} "
          f"({stats['lifelogs']['count']} new)" if stats['lifelogs']['count'] else
          f"  {'Lifelogs:':20s} {'✅' if stats['lifelogs']['success'] else '⏭️ '}")

    print(f"  {'Contents JSON:':20s} {'✅' if stats['contents']['success'] else '❌'} "
          f"({stats['contents']['count']} new)" if stats['contents']['count'] else
          f"  {'Contents JSON:':20s} {'✅' if stats['contents']['success'] else '⏭️ '}")

    print(f"  {'Chats:':20s} {'✅' if stats['chats']['success'] else '❌'} "
          f"({stats['chats']['count']} new)" if stats['chats']['count'] else
          f"  {'Chats:':20s} {'✅' if stats['chats']['success'] else '⏭️ '}")

    print(f"  {'Audio:':20s} {'✅' if stats['audio']['success'] else '❌'} "
          f"({stats['audio']['count']} new)" if stats['audio']['count'] else
          f"  {'Audio:':20s} {'✅' if stats['audio']['success'] else '⏭️ '}")

    print(f"  {'Daily Analytics:':20s} {'✅' if stats['daily_analytics']['success'] else '❌'} "
          f"({stats['daily_analytics']['count']} new)" if stats['daily_analytics']['count'] else
          f"  {'Daily Analytics:':20s} {'✅' if stats['daily_analytics']['success'] else '⏭️ '}")

    print(f"  {'Monthly Analytics:':20s} {'✅' if stats['monthly_analytics']['success'] else '❌'}")

    print(f"\n{'='*60}")

    if args.dry_run:
        print(f"\n🔍 Dry run complete. Run without --dry-run to actually sync.")
    else:
        print(f"\n✅ All sync operations complete!")
        print(f"\n📂 Your complete Limitless archive is in: exports/")


if __name__ == "__main__":
    main()


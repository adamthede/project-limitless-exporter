import os
import subprocess
import time
import random
import argparse
from datetime import date, timedelta, datetime
import re

def get_last_exported_contents_date(contents_dir: str) -> date | None:
    """
    Scans the contents directory to find the latest date from filenames
    matching YYYY-MM-DD-contents.json.
    Returns the latest date object or None if no such files are found.
    """
    latest_date = None
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})-contents\.json")
    try:
        if not os.path.exists(contents_dir):
            return None
        for filename in os.listdir(contents_dir):
            match = date_pattern.fullmatch(filename)
            if match:
                date_str = match.group(1)
                try:
                    current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    if latest_date is None or current_date > latest_date:
                        latest_date = current_date
                except ValueError:
                    continue
    except Exception as e:
        print(f"Error scanning contents directory {contents_dir} for last exported date: {e}")
        return None
    return latest_date

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def process_single_day_contents(
    date_str: str,
    export_contents_script_path: str,
    script_dir: str,
    export_page_limit: int
) -> bool:
    """
    Processes a single day: exports lifelog contents using export_day_contents_json.py.
    Returns True if successful, False otherwise.
    """
    print(f"--- Starting contents export for date: {date_str} ---")

    export_command = [
        "python", export_contents_script_path, date_str,
        "--page_limit", str(export_page_limit)
    ]

    try:
        process = subprocess.run(
            export_command,
            cwd=script_dir, # Run from the python/ directory
            capture_output=True,
            text=True,
            check=False # We check returncode manually
        )
        print(f"export_day_contents_json.py stdout for {date_str}:\n{process.stdout}")
        if process.returncode != 0:
            print(f"export_day_contents_json.py failed for {date_str} with exit code {process.returncode}.")
            print(f"export_day_contents_json.py stderr for {date_str}:\n{process.stderr}")
            return False
        print(f"export_day_contents_json.py completed successfully for {date_str}.")
        return True

    except FileNotFoundError:
        print(f"Error: export_day_contents_json.py not found at {export_contents_script_path}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while running export_day_contents_json.py for {date_str}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Batch process lifelog contents exports for a date range with retries.")

    # Date range arguments
    parser.add_argument("start_date", type=str, nargs='?', default=None, help="Start date in YYYY-MM-DD format. Defaults to yesterday if not provided.")
    parser.add_argument("end_date", type=str, nargs='?', default=None, help="End date in YYYY-MM-DD format. Defaults to yesterday if start_date is not provided, otherwise defaults to start_date.")

    # Batch retry arguments
    parser.add_argument("--batch_max_retries", type=int, default=3, help="Maximum number of retry attempts for each day in the batch (default: 3).")
    parser.add_argument("--batch_initial_backoff", type=float, default=10.0, help="Initial backoff time in seconds for batch retries (default: 10.0).")
    parser.add_argument("--batch_max_backoff", type=float, default=120.0, help="Maximum backoff time in seconds for batch retries (default: 120.0).")

    # Arguments to pass to export_day_contents_json.py
    parser.add_argument("--export_page_limit", type=int, default=50, help="Page limit for export_day_contents_json.py (default: 50).")

    args = parser.parse_args()

    today = date.today()
    yesterday = today - timedelta(days=1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    contents_output_dir = os.path.join(project_root, "exports", "contents")
    os.makedirs(contents_output_dir, exist_ok=True)

    start_dt = None
    end_dt = None

    if args.start_date is None and args.end_date is None:
        print("No start or end date provided. Attempting to determine date range based on last exported contents day...")
        last_exported_dt = get_last_exported_contents_date(contents_output_dir)
        if last_exported_dt:
            print(f"Last successfully exported contents date found in '{contents_output_dir}': {last_exported_dt.strftime('%Y-%m-%d')}")
            start_dt = last_exported_dt + timedelta(days=1)
            end_dt = yesterday
            if start_dt > end_dt:
                print(f"Contents data is already up to date through {last_exported_dt.strftime('%Y-%m-%d')}. Yesterday was {yesterday.strftime('%Y-%m-%d')}. Nothing new to export.")
                return
        else:
            print(f"No previously exported contents found in '{contents_output_dir}'. Defaulting to process yesterday's data only ({yesterday.strftime('%Y-%m-%d')}).")
            start_dt = yesterday
            end_dt = yesterday
    elif args.start_date is None:
        print(f"Start date not provided. Defaulting start date to yesterday: {yesterday.strftime('%Y-%m-%d')}")
        start_dt = yesterday
        try:
            end_dt = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid end_date format ('{args.end_date}'). Please use YYYY-MM-DD.")
            return
    elif args.end_date is None:
        try:
            start_dt = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid start_date format ('{args.start_date}'). Please use YYYY-MM-DD.")
            return
        end_dt = start_dt
        print(f"End date not provided. Defaulting end date to start date: {end_dt.strftime('%Y-%m-%d')}")
    else:
        try:
            start_dt = datetime.strptime(args.start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format for start_date ('{args.start_date}') or end_date ('{args.end_date}'). Please use YYYY-MM-DD.")
            return

    effective_start_date_str = start_dt.strftime("%Y-%m-%d")
    effective_end_date_str = end_dt.strftime("%Y-%m-%d")

    if end_dt < start_dt:
        print(f"Error: Calculated end date ({effective_end_date_str}) is before start date ({effective_start_date_str}). Cannot process.")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__)) # Moved up
    export_contents_script_path = os.path.join(script_dir, "export_day_contents_json.py")

    # The export_day_contents_json.py script handles its own output directory creation (exports/contents/)
    # So no need to explicitly create it here, but good to be aware.

    print(f"Starting batch contents export from {effective_start_date_str} to {effective_end_date_str}...")
    print(f"Batch retries per day: {args.batch_max_retries}, initial backoff: {args.batch_initial_backoff}s")
    print(f"Contents export script params: page_limit={args.export_page_limit}")

    failed_dates = []

    for single_date_dt in daterange(start_dt, end_dt):
        date_str = single_date_dt.strftime("%Y-%m-%d")
        day_processed_successfully = False

        for attempt in range(args.batch_max_retries):
            print(f"\nBatch attempt {attempt + 1} of {args.batch_max_retries} for date: {date_str}")

            if process_single_day_contents(
                date_str,
                export_contents_script_path,
                script_dir,
                args.export_page_limit
            ):
                day_processed_successfully = True
                break  # Success for this day, move to next date

            # If processing failed for the day
            if attempt < args.batch_max_retries - 1:
                backoff_time = min(
                    args.batch_initial_backoff * (2 ** attempt) + random.uniform(0, 1),
                    args.batch_max_backoff
                )
                print(f"Contents export for {date_str} failed on batch attempt {attempt + 1}.")
                print(f"Retrying batch contents export for {date_str} in {backoff_time:.2f} seconds...")
                time.sleep(backoff_time)
            else:
                print(f"All {args.batch_max_retries} batch attempts for {date_str} have failed.")

        if not day_processed_successfully:
            print(f"Failed to export contents for {date_str} after all batch retries. Adding to failed dates list.")
            failed_dates.append(date_str)

    print("\n--- Batch contents export finished ---")
    if failed_dates:
        print("\nThe following dates could not be processed successfully for contents export after all batch retries:")
        for fd in failed_dates:
            print(fd)
    else:
        print("All dates in the range processed successfully for contents export.")

if __name__ == "__main__":
    main()
import os
import subprocess
import time
import random
import argparse
from datetime import date, timedelta, datetime

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def process_single_day(
    date_str: str,
    export_script_path: str,
    summarize_script_path: str,
    lifelogs_output_dir: str,
    script_dir: str,
    export_page_limit: int,
    export_max_retries: int,
    export_initial_backoff: float,
    export_max_backoff: float
) -> bool:
    """
    Processes a single day: exports lifelogs and then generates a summary.
    Returns True if both steps are successful, False otherwise.
    """
    print(f"--- Starting processing for date: {date_str} ---")

    # Step 1: Export lifelogs for the current date
    print(f"Running export_day_lifelogs.py for {date_str}...")
    export_command = [
        "python", export_script_path, date_str,
        "--page_limit", str(export_page_limit),
        "--max_retries", str(export_max_retries),
        "--initial_backoff", str(export_initial_backoff),
        "--max_backoff", str(export_max_backoff)
    ]

    try:
        export_process = subprocess.run(
            export_command,
            cwd=script_dir,
            capture_output=True,
            text=True,
            check=False # We check returncode manually
        )
        print(f"Export script stdout for {date_str}:\n{export_process.stdout}")
        if export_process.returncode != 0:
            print(f"Export script failed for {date_str} with exit code {export_process.returncode}.")
            print(f"Export script stderr for {date_str}:\n{export_process.stderr}")
            return False
        print(f"Export script completed successfully for {date_str}.")

    except FileNotFoundError:
        print(f"Error: export_day_lifelogs.py not found at {export_script_path}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while running export script for {date_str}: {e}")
        return False

    lifelog_file_path = os.path.join(lifelogs_output_dir, f"{date_str}-lifelogs.md")

    if not os.path.exists(lifelog_file_path):
        print(f"Export for {date_str} reported success, but output file does not exist: {lifelog_file_path}")
        print("This might happen if no lifelogs were found for the day, and the export script handles this by not creating a file.")
        print("Assuming no data to summarize. Skipping summary step.")
        # If no data was found (and thus no file created), we can consider the day "processed"
        # in terms of export, and there's nothing to summarize.
        return True # No export file, so nothing to summarize, effectively "done" for this day.

    if os.path.getsize(lifelog_file_path) == 0:
        print(f"Export file for {date_str} is empty: {lifelog_file_path}. Skipping summary.")
        # Similar to above, if the file is empty, nothing to summarize.
        return True

    # Step 2: Generate summary for the current date
    print(f"Running summarize_day.py for {lifelog_file_path}...")
    summarize_command = ["python", summarize_script_path, lifelog_file_path, "--stream"]

    try:
        summarize_process = subprocess.run(
            summarize_command,
            cwd=script_dir,
            capture_output=True,
            text=True,
            check=False # We check returncode manually
        )
        print(f"Summarize script stdout for {date_str}:\n{summarize_process.stdout}")
        if summarize_process.returncode != 0:
            print(f"Summarize script failed for {date_str} with exit code {summarize_process.returncode}.")
            print(f"Summarize script stderr for {date_str}:\n{summarize_process.stderr}")
            return False
        print(f"Summarize script completed successfully for {date_str}.")

    except FileNotFoundError:
        print(f"Error: summarize_day.py not found at {summarize_script_path}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while running summary script for {date_str}: {e}")
        return False

    print(f"Successfully exported and summarized {date_str}.")
    return True

def main():
    parser = argparse.ArgumentParser(description="Batch process lifelog exports and summaries for a date range with retries.")

    # Date range arguments
    parser.add_argument("start_date", type=str, nargs='?', default=None, help="Start date in YYYY-MM-DD format. Defaults to yesterday if not provided.")
    parser.add_argument("end_date", type=str, nargs='?', default=None, help="End date in YYYY-MM-DD format. Defaults to yesterday if start_date is not provided, otherwise defaults to start_date.")

    # Batch retry arguments
    parser.add_argument("--batch_max_retries", type=int, default=3, help="Maximum number of retry attempts for each day in the batch (default: 3).")
    parser.add_argument("--batch_initial_backoff", type=float, default=10.0, help="Initial backoff time in seconds for batch retries (default: 10.0).")
    parser.add_argument("--batch_max_backoff", type=float, default=120.0, help="Maximum backoff time in seconds for batch retries (default: 120.0).")

    # Arguments to pass to export_day_lifelogs.py
    parser.add_argument("--export_page_limit", type=int, default=50, help="Page limit for export_day_lifelogs.py (default: 50).")
    parser.add_argument("--export_max_retries", type=int, default=5, help="Max retries for export_day_lifelogs.py (default: 5).")
    parser.add_argument("--export_initial_backoff", type=float, default=2.0, help="Initial backoff for export_day_lifelogs.py (default: 2.0).")
    parser.add_argument("--export_max_backoff", type=float, default=60.0, help="Max backoff for export_day_lifelogs.py (default: 60.0).")

    args = parser.parse_args()

    today = date.today()
    yesterday = today - timedelta(days=1)

    start_dt = None
    end_dt = None

    if args.start_date is None:
        start_dt = yesterday
        # If start_date wasn't given, end_date also defaults to yesterday unless explicitly provided
        if args.end_date is None:
            end_dt = yesterday
        else:
            try:
                end_dt = datetime.strptime(args.end_date, "%Y-%m-%d").date()
            except ValueError:
                print(f"Error: Invalid end_date format ({args.end_date}). Please use YYYY-MM-DD.")
                return
    else: # start_date was provided
        try:
            start_dt = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid start_date format ({args.start_date}). Please use YYYY-MM-DD.")
            return

        if args.end_date is None:
            end_dt = start_dt # If only start_date is given, end_date is the same
        else:
            try:
                end_dt = datetime.strptime(args.end_date, "%Y-%m-%d").date()
            except ValueError:
                print(f"Error: Invalid end_date format ({args.end_date}). Please use YYYY-MM-DD.")
                return

    # For logging purposes, ensure args.start_date and args.end_date have the actual dates being used.
    effective_start_date_str = start_dt.strftime("%Y-%m-%d")
    effective_end_date_str = end_dt.strftime("%Y-%m-%d")

    if end_dt < start_dt:
        print("Error: End date cannot be before start date.")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__)) # Should be the python/ directory
    export_script_path = os.path.join(script_dir, "export_day_lifelogs.py")
    summarize_script_path = os.path.join(script_dir, "summarize_day.py")

    project_root = os.path.dirname(script_dir)
    lifelogs_output_dir = os.path.join(project_root, "exports", "lifelogs")

    # Ensure exports/lifelogs directory exists
    os.makedirs(lifelogs_output_dir, exist_ok=True)


    print(f"Starting batch processing from {effective_start_date_str} to {effective_end_date_str}...")
    print(f"Batch retries per day: {args.batch_max_retries}, initial backoff: {args.batch_initial_backoff}s")
    print(f"Export script params: page_limit={args.export_page_limit}, max_retries={args.export_max_retries}, initial_backoff={args.export_initial_backoff}s")

    failed_dates = []

    for single_date_dt in daterange(start_dt, end_dt):
        date_str = single_date_dt.strftime("%Y-%m-%d")
        day_processed_successfully = False

        for attempt in range(args.batch_max_retries):
            print(f"\nBatch attempt {attempt + 1} of {args.batch_max_retries} for date: {date_str}")

            if process_single_day(
                date_str,
                export_script_path,
                summarize_script_path,
                lifelogs_output_dir,
                script_dir,
                args.export_page_limit,
                args.export_max_retries,
                args.export_initial_backoff,
                args.export_max_backoff
            ):
                day_processed_successfully = True
                break  # Success for this day, move to next date

            # If processing failed for the day
            if attempt < args.batch_max_retries - 1:
                backoff_time = min(
                    args.batch_initial_backoff * (2 ** attempt) + random.uniform(0, 1),
                    args.batch_max_backoff
                )
                print(f"Processing for {date_str} failed on batch attempt {attempt + 1}.")
                print(f"Retrying batch processing for {date_str} in {backoff_time:.2f} seconds...")
                time.sleep(backoff_time)
            else:
                print(f"All {args.batch_max_retries} batch attempts for {date_str} have failed.")

        if not day_processed_successfully:
            print(f"Failed to process {date_str} after all batch retries. Adding to failed dates list.")
            failed_dates.append(date_str)

    print("\n--- Batch processing finished ---")
    if failed_dates:
        print("\nThe following dates could not be processed successfully after all batch retries:")
        for fd in failed_dates:
            print(fd)
    else:
        print("All dates in the range processed successfully.")

if __name__ == "__main__":
    main()
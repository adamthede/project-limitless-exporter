import os
import argparse
from datetime import datetime
from dotenv import load_dotenv
import time # Added for backoff
import random # Added for jitter in backoff
import sys # Added to control exit code
load_dotenv()

# Assuming _client.py is in the same directory or accessible via PYTHONPATH
# and get_lifelogs can handle pagination parameters and returns a full API response object.
try:
    from _client import get_lifelogs
except ImportError:
    print("Error: Could not import get_lifelogs from _client.py.")
    print("Please ensure _client.py is in the same directory or in your PYTHONPATH.")
    print("Also ensure get_lifelogs in _client.py supports 'date', 'cursor', 'limit', 'includeMarkdown', 'direction' parameters and returns the full API response object.")
    exit(1)

def fetch_one_page_of_lifelogs_for_date(api_key: str, target_date: str, limit: int = 50):
    """
    Fetches a single page of lifelog entries for a specific date.
    NOTE: This function does NOT handle pagination. If there are more entries
    for the date than the 'limit', only the first page will be returned.
    To get all entries, '_client.py' and this script would need full pagination support.
    Returns a single string of all markdown content from the fetched page,
    or an empty string if none found or on error.
    """
    all_markdowns = []
    # Flag to track if "No lifelog entries found for date" was printed by this function
    fetch_one_page_of_lifelogs_for_date.printed_no_initial_entries = False

    print(f"Fetching lifelogs for date: {target_date} (single page, limit: {limit})...")
    print("Note: Full pagination is not currently active due to _client.py compatibility.")

    try:
        response = get_lifelogs(
            api_key=api_key,
            date=target_date,
            limit=limit,
            # cursor is removed as it caused the TypeError
            includeMarkdown=True,
            direction="asc"
        )
    except Exception as e:
        print(f"Error calling get_lifelogs: {e}")
        # If the error was about 'date', 'includeMarkdown', or 'direction', it would also show here.
        # For now, we assume these are either supported or ignored gracefully by _client.py.
        return ""

    if not response:
        print("Failed to fetch lifelogs: No response from API client.")
        print(f"No lifelogs found or unable to fetch for date: {target_date}")
        fetch_one_page_of_lifelogs_for_date.printed_no_initial_entries = True
        return ""

    lifelogs_data = response.get("data", {}).get("lifelogs", [])

    if not lifelogs_data:
        print(f"No lifelog entries found for date: {target_date} in the fetched page.")
        fetch_one_page_of_lifelogs_for_date.printed_no_initial_entries = True
        # No need to check meta.nextCursor as we are not paginating
    else:
        for lifelog in lifelogs_data:
            if lifelog and isinstance(lifelog, dict) and lifelog.get("markdown"):
                all_markdowns.append(lifelog["markdown"])

        if not all_markdowns:
            print(f"Entries were found for {target_date}, but they contained no markdown text.")

    # next_cursor and multi-page logic is removed.

    return "\n\n---\n\n".join(all_markdowns)

def fetch_all_lifelogs_for_date(api_key: str, target_date: str, page_limit: int = 50):
    """
    Fetches ALL lifelog entries for a specific date, handling pagination.
    Returns a tuple: (string_of_all_markdown_content, boolean_success_flag).
    The success_flag is True if all pages were fetched without error, False otherwise.
    """
    all_markdowns = []
    current_cursor = None
    first_fetch = True
    fetch_fully_successful = True # Assume success until an error occurs

    # Flag to track if "No lifelog entries found for date" was printed by this function
    fetch_all_lifelogs_for_date.printed_no_initial_entries = False

    print(f"Fetching all lifelogs for date: {target_date} (page limit: {page_limit})...")
    print("Attempting full pagination. This requires _client.py's get_lifelogs to support 'cursor'.")

    while True:
        try:
            response = get_lifelogs(
                api_key=api_key,
                date=target_date,
                limit=page_limit,
                cursor=current_cursor,
                includeMarkdown=True,
                direction="asc"
            )
        except TypeError as te:
            if 'cursor' in str(te).lower():
                print(f"CRITICAL ERROR: get_lifelogs in _client.py does not support the 'cursor' argument, which is essential for pagination.")
                print("Please update _client.py. Halting export for this date.")
            else:
                print(f"Error calling get_lifelogs (TypeError): {te}")
            fetch_fully_successful = False
            break # Exit loop on critical error
        except Exception as e:
            print(f"Error calling get_lifelogs: {e}")
            fetch_fully_successful = False
            break # Exit loop on general error

        if not response:
            print("Failed to fetch lifelogs: No response from API client (or _client.py did not return one).")
            if first_fetch:
                print(f"No lifelogs found or unable to fetch for date: {target_date} on the first attempt.")
                fetch_all_lifelogs_for_date.printed_no_initial_entries = True
            fetch_fully_successful = False # Mark as not fully successful if response is missing
            break # Exit loop if response is missing

        lifelogs_data = response.get("data", {}).get("lifelogs", [])

        if first_fetch and not lifelogs_data:
            print(f"No lifelog entries found for date: {target_date} in the first page of results.")
            fetch_all_lifelogs_for_date.printed_no_initial_entries = True
            # This is not an error, just no data. Loop will break if no next_cursor.

        for lifelog in lifelogs_data:
            if lifelog and isinstance(lifelog, dict) and lifelog.get("markdown"):
                all_markdowns.append(lifelog["markdown"])

        meta = response.get("meta", {})
        if not isinstance(meta, dict):
            print("Warning: 'meta' object not found or not a dictionary in API response. Pagination cannot continue reliably.")
            fetch_fully_successful = False
            break

        meta_lifelogs = meta.get("lifelogs", {})
        if not isinstance(meta_lifelogs, dict):
            print("Warning: 'meta.lifelogs' object not found or not a dictionary in API response. Pagination cannot continue reliably.")
            fetch_fully_successful = False
            break

        next_cursor = meta_lifelogs.get("nextCursor")

        if not next_cursor:
            if first_fetch and lifelogs_data:
                 print(f"Fetched {len(lifelogs_data)} entries. No more pages for {target_date}.")
            elif not first_fetch:
                 print(f"Fetched an additional {len(lifelogs_data)} entries. No more pages for {target_date}.")
            # This is a successful end of pagination
            break

        page_info_msg = f"Fetched first page with {len(lifelogs_data)} entries." if first_fetch else f"Fetched {len(lifelogs_data)} more entries."
        print(f"{page_info_msg} Next cursor: {next_cursor[:10]}...")

        current_cursor = next_cursor
        first_fetch = False

    final_markdown_string = "\n\n---\n\n".join(all_markdowns) if all_markdowns else ""

    if not final_markdown_string and not fetch_all_lifelogs_for_date.printed_no_initial_entries and fetch_fully_successful:
        # This case means API calls were successful but no actual markdown content was found in any lifelog
        print(f"API calls were successful, but no markdown content was found in any lifelogs for {target_date}.")
    elif all_markdowns and fetch_fully_successful:
        print(f"Finished fetching all pages successfully for {target_date}. Total markdown entries collated: {len(all_markdowns)}.")
    elif not fetch_fully_successful and all_markdowns:
        print(f"Warning: Fetching for {target_date} was incomplete due to errors, but some data ({len(all_markdowns)} entries) was retrieved.")
    elif not fetch_fully_successful and not all_markdowns:
        print(f"Fetching for {target_date} failed and no data was retrieved.")


    return (final_markdown_string, fetch_fully_successful)

def main():
    parser = argparse.ArgumentParser(description="Export ALL lifelogs for a specific date to a markdown file, handling pagination.")
    parser.add_argument("date", type=str, help="The date to export lifelogs for, in YYYY-MM-DD format.")
    parser.add_argument("--page_limit", type=int, default=50, help="Number of entries to fetch per API call during pagination (default: 50).")
    parser.add_argument("--max_retries", type=int, default=5, help="Maximum number of retry attempts for fetching a day's data (default: 5).")
    parser.add_argument("--initial_backoff", type=float, default=2.0, help="Initial backoff time in seconds for retries (default: 2.0).")
    parser.add_argument("--max_backoff", type=float, default=60.0, help="Maximum backoff time in seconds for retries (default: 60.0).")

    args = parser.parse_args()
    target_date_str = args.date
    page_fetch_limit = args.page_limit
    max_retries = args.max_retries
    initial_backoff_seconds = args.initial_backoff
    max_backoff_seconds = args.max_backoff

    # Validate date format
    try:
        datetime.strptime(target_date_str, "%Y-%m-%d")
    except ValueError:
        print("Error: Date format must be YYYY-MM-DD and be a valid date (e.g., 2024-07-15).")
        return

    api_key = os.getenv("LIMITLESS_API_KEY")
    if not api_key:
        print("Error: LIMITLESS_API_KEY environment variable not set.")
        return

    # Define the output directory relative to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    # Specific subdirectory for lifelogs
    output_base_dir = os.path.join(project_root, "exports", "lifelogs")

    try:
        os.makedirs(output_base_dir, exist_ok=True)
    except OSError as e:
        print(f"Error creating output directory {output_base_dir}: {e}")
        return

    final_combined_markdown = ""
    final_fetch_successful = False

    for attempt in range(max_retries):
        print(f"Attempt {attempt + 1} of {max_retries} to fetch lifelogs for {target_date_str}...")

        # Reset this flag for each full attempt to ensure clean logging for that attempt
        fetch_all_lifelogs_for_date.printed_no_initial_entries = False

        current_combined_markdown, current_fetch_successful = fetch_all_lifelogs_for_date(
            api_key, target_date_str, page_limit=page_fetch_limit
        )

        if current_fetch_successful:
            final_combined_markdown = current_combined_markdown
            final_fetch_successful = True
            print(f"Successfully fetched all lifelogs for {target_date_str} on attempt {attempt + 1}.")
            break  # Exit retry loop on success
        else:
            # Store potentially partial data from this failed attempt.
            # This ensures that if all retries fail, 'final_combined_markdown' holds the data from the last attempt.
            final_combined_markdown = current_combined_markdown
            final_fetch_successful = False # Explicitly mark as failed for this attempt

            print(f"Attempt {attempt + 1} for {target_date_str} failed to complete successfully.")
            if attempt < max_retries - 1:
                backoff_time = min(initial_backoff_seconds * (2 ** attempt) + random.uniform(0, 1), max_backoff_seconds)
                print(f"Retrying in {backoff_time:.2f} seconds...")
                time.sleep(backoff_time)
            else:
                print(f"All {max_retries} attempts to fetch lifelogs for {target_date_str} have failed.")
                # final_combined_markdown already holds data from the last attempt.
                # final_fetch_successful is already False.

    output_filename = os.path.join(output_base_dir, f"{target_date_str}-lifelogs.md")

    if final_combined_markdown and final_fetch_successful:
        try:
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(final_combined_markdown)
            print(f"Successfully fetched all lifelogs for {target_date_str} and saved to {output_filename}")
        except IOError as e:
            print(f"Error writing to file {output_filename}: {e}")
    elif final_combined_markdown and not final_fetch_successful:
        print(f"Warning: Fetching for {target_date_str} was incomplete after all retries.")
        print(f"The file {output_filename} was NOT updated to preserve potentially more complete existing data.")
        # Optionally, save partial data to a different file, e.g.:
        # partial_filename = os.path.join(output_base_dir, f"{target_date_str}-lifelogs.PARTIAL_FAILED.md")
        # try:
        #     with open(partial_filename, "w", encoding="utf-8") as f:
        #         f.write(final_combined_markdown)
        #     print(f"Partial data from the last failed attempt saved to {partial_filename}")
        # except IOError as e:
        #     print(f"Error writing partial data to file {partial_filename}: {e}")
    elif not final_combined_markdown and final_fetch_successful:
        # This case implies API calls were fine, but no actual markdown content was returned.
        # fetch_all_lifelogs_for_date.printed_no_initial_entries would have been true.
        print(f"No markdown content found for {target_date_str}, though API calls were successful. {output_filename} not created/updated.")
    else: # not final_combined_markdown and not final_fetch_successful
        print(f"Fetching failed for {target_date_str} after all retries and no data was retrieved. {output_filename} not created/updated.")

    if not final_fetch_successful:
        print(f"Exiting with status 1 due to incomplete fetch for {target_date_str}.")
        sys.exit(1)

if __name__ == "__main__":
    main()
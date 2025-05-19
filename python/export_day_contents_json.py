import os
import argparse
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
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

def fetch_all_lifelog_contents_for_date(api_key: str, target_date: str, page_limit: int = 50):
    """
    Fetches ALL lifelogs for a specific date, handling pagination, and extracts their IDs and 'contents' arrays.
    Returns a list of dictionaries, each containing 'lifelog_id' and 'contents_array'.
    """
    all_lifelog_details = []
    current_cursor = None
    first_fetch = True
    # Flag to track if "No lifelog entries found for date" was printed by this function
    fetch_all_lifelog_contents_for_date.printed_no_initial_entries = False

    print(f"Fetching all lifelog contents for date: {target_date} (page limit: {page_limit})...")
    print("Attempting full pagination. This requires _client.py's get_lifelogs to support 'cursor'.")

    while True:
        try:
            response = get_lifelogs(
                api_key=api_key,
                date=target_date,
                limit=page_limit,
                cursor=current_cursor,
                includeMarkdown=True, # Keep True to ensure 'contents' is populated as per API behavior
                includeHeadings=True, # Keep True to get headings in 'contents'
                direction="asc"       # Chronological order for the day's entries
            )
        except TypeError as te:
            if 'cursor' in str(te).lower(): # Check if the error message mentions 'cursor'
                print(f"CRITICAL ERROR: get_lifelogs in _client.py does not support the 'cursor' argument, which is essential for pagination.")
                print("Please update _client.py. Halting export for this date.")
            else:
                print(f"Error calling get_lifelogs (TypeError): {te}")
            return [] # Stop processing for this date
        except Exception as e:
            print(f"Error calling get_lifelogs: {e}")
            return [] # Stop processing for this date

        if not response:
            print("Failed to fetch lifelogs: No response from API client (or _client.py did not return one).")
            if first_fetch:
                print(f"No lifelogs found or unable to fetch for date: {target_date} on the first attempt.")
                fetch_all_lifelog_contents_for_date.printed_no_initial_entries = True
            return all_lifelog_details # Return what we have so far

        lifelogs_data = response.get("data", {}).get("lifelogs", [])

        if first_fetch and not lifelogs_data:
            print(f"No lifelog entries found for date: {target_date} in the first page of results.")
            fetch_all_lifelog_contents_for_date.printed_no_initial_entries = True
            # The loop will terminate if next_cursor is also None.

        for lifelog in lifelogs_data:
            if lifelog and isinstance(lifelog, dict):
                lifelog_id = lifelog.get("id")
                contents_array = lifelog.get("contents")
                full_markdown_content = lifelog.get("markdown") # Get the top-level markdown

                if lifelog_id:
                    entry_details = {
                        "lifelog_id": lifelog_id,
                        "full_markdown": full_markdown_content if full_markdown_content is not None else "", # Store markdown, default to empty string if null
                        "contents": contents_array if contents_array is not None else [] # Store contents, default to empty list if null
                    }
                    all_lifelog_details.append(entry_details)

                    if contents_array is None:
                        print(f"Warning: Lifelog ID {lifelog_id} for date {target_date} did not have a 'contents' field or it was null. Stored as empty list.")
                    if full_markdown_content is None:
                        print(f"Warning: Lifelog ID {lifelog_id} for date {target_date} did not have a 'markdown' field or it was null. Stored as empty string.")
                else:
                    print(f"Warning: Encountered a lifelog entry without an ID for date {target_date}. Skipping this entry.")


        meta = response.get("meta", {})
        if not isinstance(meta, dict):
            print("Warning: 'meta' object not found or not a dictionary in API response. Pagination may not work.")
            break

        meta_lifelogs = meta.get("lifelogs", {})
        if not isinstance(meta_lifelogs, dict):
            print("Warning: 'meta.lifelogs' object not found or not a dictionary in API response. Pagination may not work.")
            break

        next_cursor = meta_lifelogs.get("nextCursor")

        if not next_cursor:
            if first_fetch and lifelogs_data:
                 print(f"Fetched {len(lifelogs_data)} entries' contents. No more pages for {target_date}.")
            elif not first_fetch:
                 print(f"Fetched an additional {len(lifelogs_data)} entries' contents. No more pages for {target_date}.")
            break

        page_info = f"Fetched first page with {len(lifelogs_data)} entries' contents." if first_fetch else f"Fetched {len(lifelogs_data)} more entries' contents."
        print(f"{page_info} Next cursor: {next_cursor[:10]}...")

        current_cursor = next_cursor
        first_fetch = False

    if not all_lifelog_details and not fetch_all_lifelog_contents_for_date.printed_no_initial_entries:
        print(f"No lifelog contents were extracted for {target_date}. This could be due to no entries, or entries lacking 'contents' field.")
    elif all_lifelog_details:
        print(f"Finished fetching all pages for {target_date}. Total lifelogs with contents processed: {len(all_lifelog_details)}.")

    return all_lifelog_details

def main():
    parser = argparse.ArgumentParser(description="Export structured 'contents' of all lifelogs for a specific date to a JSON file.")
    parser.add_argument("date", type=str, help="The date to export lifelogs for, in YYYY-MM-DD format.")
    parser.add_argument("--page_limit", type=int, default=50, help="Number of entries to fetch per API call during pagination (default: 50).")

    args = parser.parse_args()
    target_date_str = args.date
    page_fetch_limit = args.page_limit

    # Initialize the flag
    fetch_all_lifelog_contents_for_date.printed_no_initial_entries = False

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
    project_root = os.path.dirname(script_dir) # Assumes script is in a subdir like 'python/'
    # Corrected output directory to include the 'contents' subdirectory
    output_dir = os.path.join(project_root, "exports", "contents")

    # Create the output directory if it doesn't exist
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        print(f"Error creating output directory {output_dir}: {e}")
        return

    extracted_data = fetch_all_lifelog_contents_for_date(api_key, target_date_str, page_limit=page_fetch_limit)

    if extracted_data:
        output_filename = os.path.join(output_dir, f"{target_date_str}-contents.json")
        try:
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False) # indent for readability
            print(f"Successfully exported lifelog contents for {target_date_str} to {output_filename}")
        except IOError as e:
            print(f"Error writing to file {output_filename}: {e}")
        except TypeError as te:
            print(f"Error serializing data to JSON for {output_filename}: {te}. This might indicate non-serializable data in 'contents'.")

    elif not fetch_all_lifelog_contents_for_date.printed_no_initial_entries:
        print(f"No data was extracted for {target_date_str}. No JSON file created. Review logs from fetching process.")

if __name__ == "__main__":
    main()
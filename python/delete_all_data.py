#!/usr/bin/env python3
"""
Delete all data from Limitless API (lifelogs and chats).

⚠️  WARNING: This script PERMANENTLY deletes ALL your Limitless data.
This action is IRREVERSIBLE. Deleted data cannot be recovered.

Before running this script:
1. Ensure you have a complete local backup
2. Run with --dry-run first to see what will be deleted
3. Understand that this action is permanent

Usage:
    # Dry run - see what would be deleted (RECOMMENDED FIRST)
    python delete_all_data.py --dry-run

    # Delete everything (requires confirmation)
    python delete_all_data.py

    # Delete only lifelogs
    python delete_all_data.py --lifelogs-only

    # Delete only chats
    python delete_all_data.py --chats-only

    # Skip confirmation prompts (USE WITH EXTREME CAUTION)
    python delete_all_data.py --yes
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime
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
MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_DELAY = 0.3  # Delay between requests to avoid rate limiting


def fetch_all_lifelogs(max_pages=1000):
    """
    Fetch all lifelogs from the API.

    Returns:
        list: List of all lifelog dictionaries
    """
    if not API_KEY:
        print("Error: LIMITLESS_API_KEY not found in environment variables.")
        return []

    endpoint = f"{API_URL}/v1/lifelogs"
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    }

    all_lifelogs = []
    cursor = None
    pages_fetched = 0

    print("📥 Fetching all lifelogs from the API...")

    while pages_fetched < max_pages:
        params = {
            "limit": 50,
            "includeMarkdown": "false"  # We don't need the content, just IDs
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
        print(f"  Page {pages_fetched}: {len(all_lifelogs)} total lifelogs...")

        next_cursor = data.get("meta", {}).get("lifelogs", {}).get("nextCursor")
        if not next_cursor:
            print(f"  Reached end of available lifelogs")
            break

        cursor = next_cursor
        time.sleep(REQUEST_DELAY)

    print(f"✅ Fetched {len(all_lifelogs)} total lifelogs\n")
    return all_lifelogs


def fetch_all_chats(max_pages=200):
    """
    Fetch all chats from the API.

    Returns:
        list: List of all chat dictionaries
    """
    if not API_KEY:
        print("Error: LIMITLESS_API_KEY not found in environment variables.")
        return []

    endpoint = f"{API_URL}/v1/chats"
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    }

    all_chats = []
    cursor = None
    pages_fetched = 0

    print("📥 Fetching all chats from the API...")

    while pages_fetched < max_pages:
        params = {
            "limit": 10,
            "includeMarkdown": "false"  # We don't need the content, just IDs
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
                    return all_chats

        chats = data.get("data", {}).get("chats", [])
        all_chats.extend(chats)

        pages_fetched += 1
        print(f"  Page {pages_fetched}: {len(all_chats)} total chats...")

        next_cursor = data.get("meta", {}).get("chats", {}).get("nextCursor")
        if not next_cursor:
            print(f"  Reached end of available chats")
            break

        cursor = next_cursor
        time.sleep(REQUEST_DELAY)

    print(f"✅ Fetched {len(all_chats)} total chats\n")
    return all_chats


def delete_lifelog(lifelog_id):
    """
    Delete a single lifelog by ID.

    Args:
        lifelog_id: The ID of the lifelog to delete

    Returns:
        bool: True if successful, False otherwise
    """
    if not API_KEY:
        print("Error: LIMITLESS_API_KEY not found.")
        return False

    endpoint = f"{API_URL}/v1/lifelogs/{lifelog_id}"
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.delete(endpoint, headers=headers, timeout=30)
            response.raise_for_status()

            # Check for success response
            result = response.json()
            if result.get("success"):
                return True
            else:
                print(f"  Unexpected response: {result}")
                return False

        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Delete failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                time.sleep(RETRY_DELAY)
            else:
                print(f"  Failed to delete lifelog {lifelog_id} after {MAX_RETRIES} attempts: {e}")
                return False

    return False


def delete_chat(chat_id):
    """
    Delete a single chat by ID.

    Args:
        chat_id: The ID of the chat to delete

    Returns:
        bool: True if successful, False otherwise
    """
    if not API_KEY:
        print("Error: LIMITLESS_API_KEY not found.")
        return False

    endpoint = f"{API_URL}/v1/chats/{chat_id}"
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.delete(endpoint, headers=headers, timeout=30)
            response.raise_for_status()

            # Check for success response
            result = response.json()
            if result.get("data", {}).get("success"):
                return True
            else:
                print(f"  Unexpected response: {result}")
                return False

        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Delete failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                time.sleep(RETRY_DELAY)
            else:
                print(f"  Failed to delete chat {chat_id} after {MAX_RETRIES} attempts: {e}")
                return False

    return False


def delete_all_lifelogs(lifelogs, dry_run=False):
    """
    Delete all lifelogs.

    Args:
        lifelogs: List of lifelog dictionaries
        dry_run: If True, only simulate deletion

    Returns:
        tuple: (success_count, failure_count)
    """
    print(f"\n{'='*60}")
    print("Deleting Lifelogs")
    print(f"{'='*60}\n")

    success_count = 0
    failure_count = 0

    for i, lifelog in enumerate(lifelogs, 1):
        lifelog_id = lifelog.get("id")
        started_at = lifelog.get("startTime", "Unknown date")

        print(f"[{i}/{len(lifelogs)}] Lifelog {lifelog_id} ({started_at})", end="")

        if dry_run:
            print(" [DRY RUN - would delete]")
            success_count += 1
        else:
            if delete_lifelog(lifelog_id):
                print(" ✅")
                success_count += 1
            else:
                print(" ❌")
                failure_count += 1

            time.sleep(REQUEST_DELAY)

    return success_count, failure_count


def delete_all_chats(chats, dry_run=False):
    """
    Delete all chats.

    Args:
        chats: List of chat dictionaries
        dry_run: If True, only simulate deletion

    Returns:
        tuple: (success_count, failure_count)
    """
    print(f"\n{'='*60}")
    print("Deleting Chats")
    print(f"{'='*60}\n")

    success_count = 0
    failure_count = 0

    for i, chat in enumerate(chats, 1):
        chat_id = chat.get("id")
        summary = (chat.get("summary") or "Untitled")[:50]

        print(f"[{i}/{len(chats)}] {summary} ({chat_id})", end="")

        if dry_run:
            print(" [DRY RUN - would delete]")
            success_count += 1
        else:
            if delete_chat(chat_id):
                print(" ✅")
                success_count += 1
            else:
                print(" ❌")
                failure_count += 1

            time.sleep(REQUEST_DELAY)

    return success_count, failure_count


def confirm_deletion(lifelogs_count, chats_count, skip_lifelogs=False, skip_chats=False):
    """
    Ask user for confirmation before deleting data.

    Returns:
        bool: True if user confirms, False otherwise
    """
    print(f"\n{'='*60}")
    print("⚠️  WARNING: PERMANENT DATA DELETION")
    print(f"{'='*60}\n")

    print("You are about to PERMANENTLY delete:")
    if not skip_lifelogs:
        print(f"  • {lifelogs_count} lifelogs (transcripts, audio, metadata)")
    if not skip_chats:
        print(f"  • {chats_count} chats (conversations)")

    print("\n⚠️  This action is IRREVERSIBLE!")
    print("⚠️  Deleted data CANNOT be recovered!")
    print("\nBefore proceeding:")
    print("  ✓ Ensure you have a complete local backup")
    print("  ✓ Verify your backup is intact")
    print("  ✓ Understand this is permanent")

    print("\n" + "="*60)
    response = input("\nType 'DELETE ALL MY DATA' to confirm: ")

    return response == "DELETE ALL MY DATA"


def main():
    parser = argparse.ArgumentParser(
        description="Delete all data from Limitless API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to preview what would be deleted
  python delete_all_data.py --dry-run

  # Delete everything (with confirmation)
  python delete_all_data.py

  # Delete only lifelogs
  python delete_all_data.py --lifelogs-only

  # Delete only chats
  python delete_all_data.py --chats-only

⚠️  WARNING: This permanently deletes ALL your Limitless data.
Make sure you have a complete backup before proceeding!
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (USE WITH EXTREME CAUTION)"
    )
    parser.add_argument(
        "--lifelogs-only",
        action="store_true",
        help="Delete only lifelogs, skip chats"
    )
    parser.add_argument(
        "--chats-only",
        action="store_true",
        help="Delete only chats, skip lifelogs"
    )
    parser.add_argument(
        "--max-lifelog-pages",
        type=int,
        default=1000,
        help="Maximum API pages to fetch for lifelogs (default: 1000)"
    )
    parser.add_argument(
        "--max-chat-pages",
        type=int,
        default=200,
        help="Maximum API pages to fetch for chats (default: 200)"
    )

    args = parser.parse_args()

    # Check for API key
    if not API_KEY:
        print("Error: LIMITLESS_API_KEY not found in environment variables.")
        print("Please set it in your .env file or environment.")
        sys.exit(1)

    # Determine what to delete
    skip_lifelogs = args.chats_only
    skip_chats = args.lifelogs_only

    # Fetch data
    lifelogs = [] if skip_lifelogs else fetch_all_lifelogs(max_pages=args.max_lifelog_pages)
    chats = [] if skip_chats else fetch_all_chats(max_pages=args.max_chat_pages)

    if not lifelogs and not chats:
        print("No data found to delete.")
        sys.exit(0)

    # Show summary
    print(f"\n{'='*60}")
    print("Data Summary")
    print(f"{'='*60}")
    if not skip_lifelogs:
        print(f"  Lifelogs found: {len(lifelogs)}")
    if not skip_chats:
        print(f"  Chats found: {len(chats)}")
    print(f"{'='*60}")

    # Dry run mode
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No data will be deleted\n")

        if lifelogs:
            delete_all_lifelogs(lifelogs, dry_run=True)

        if chats:
            delete_all_chats(chats, dry_run=True)

        print(f"\n{'='*60}")
        print("Dry Run Summary")
        print(f"{'='*60}")
        print("This was a DRY RUN. No data was deleted.")
        print("\nTo actually delete data, run without --dry-run")
        print(f"{'='*60}\n")

        return

    # Confirmation
    if not args.yes:
        if not confirm_deletion(len(lifelogs), len(chats), skip_lifelogs, skip_chats):
            print("\n❌ Deletion cancelled by user.")
            sys.exit(0)

    # Perform deletion
    print("\n🗑️  Starting deletion process...\n")

    lifelog_success = 0
    lifelog_failure = 0
    chat_success = 0
    chat_failure = 0

    if lifelogs:
        lifelog_success, lifelog_failure = delete_all_lifelogs(lifelogs, dry_run=False)

    if chats:
        chat_success, chat_failure = delete_all_chats(chats, dry_run=False)

    # Final summary
    print(f"\n{'='*60}")
    print("Deletion Complete")
    print(f"{'='*60}")

    if lifelogs:
        print(f"\nLifelogs:")
        print(f"  ✅ Successfully deleted: {lifelog_success}")
        print(f"  ❌ Failed to delete: {lifelog_failure}")

    if chats:
        print(f"\nChats:")
        print(f"  ✅ Successfully deleted: {chat_success}")
        print(f"  ❌ Failed to delete: {chat_failure}")

    total_success = lifelog_success + chat_success
    total_failure = lifelog_failure + chat_failure

    print(f"\nTotal:")
    print(f"  ✅ Successfully deleted: {total_success}")
    print(f"  ❌ Failed to delete: {total_failure}")

    print(f"{'='*60}\n")

    if total_failure > 0:
        print("⚠️  Some items failed to delete. You may want to:")
        print("   1. Check your internet connection")
        print("   2. Verify your API key is still valid")
        print("   3. Run the script again to retry failed deletions")
    else:
        print("✅ All data successfully deleted from Limitless servers.")


if __name__ == "__main__":
    main()

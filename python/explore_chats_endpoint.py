#!/usr/bin/env python3
"""
Experimental script to explore the Limitless API /v1/chats endpoint.
This script will help us understand what data is available, including
potentially the Daily Digest/Daily Insights.

Usage:
    python explore_chats_endpoint.py [--date YYYY-MM-DD] [--limit N]
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import tzlocal

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("LIMITLESS_API_KEY")
API_URL = os.getenv("LIMITLESS_API_URL", "https://api.limitless.ai")
TIMEZONE = str(tzlocal.get_localzone())


def explore_chats_endpoint(
    date=None,
    limit=10,
    cursor=None,
    include_markdown=True,
    verbose=True
):
    """
    Explore the /v1/chats endpoint to see what data is available.

    Args:
        date: Optional date string in YYYY-MM-DD format
        limit: Number of results to return
        cursor: Pagination cursor
        include_markdown: Whether to include markdown in response
        verbose: Print detailed information

    Returns:
        dict: The full API response, or None on error
    """
    if not API_KEY:
        print("Error: LIMITLESS_API_KEY not found in environment variables.")
        print("Please create a .env file with your API key.")
        return None

    endpoint = f"{API_URL}/v1/chats"

    params = {
        "limit": limit,
        "includeMarkdown": "true" if include_markdown else "false",
        "timezone": TIMEZONE
    }

    if date:
        params["date"] = date
    if cursor:
        params["cursor"] = cursor

    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    }

    if verbose:
        print(f"\n{'='*60}")
        print(f"Exploring Limitless API Chats Endpoint")
        print(f"{'='*60}")
        print(f"Endpoint: {endpoint}")
        print(f"Parameters: {json.dumps(params, indent=2)}")
        print(f"{'='*60}\n")

    try:
        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            timeout=30
        )

        if verbose:
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers:")
            for key, value in response.headers.items():
                if key.lower() not in ['set-cookie', 'authorization']:
                    print(f"  {key}: {value}")
            print()

        # Try to parse JSON even if status code isn't 200
        try:
            data = response.json()

            if verbose:
                print(f"Response Structure:")
                print(f"  Top-level keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                print()

            if response.status_code == 200:
                if verbose:
                    print("✅ Success! Response received.")
                    print(f"\nFull Response (formatted):")
                    print(json.dumps(data, indent=2))
                return data
            else:
                print(f"⚠️  Non-200 status code: {response.status_code}")
                print(f"Response: {json.dumps(data, indent=2)}")
                return data

        except json.JSONDecodeError:
            print(f"❌ Failed to parse JSON response")
            print(f"Raw response text: {response.text[:500]}")
            return None

    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        return None
    except requests.exceptions.Timeout as e:
        print(f"❌ Request timeout: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def search_for_daily_insights(response_data):
    """
    Analyze the response to look for Daily Digest/Insights patterns.
    """
    if not response_data:
        return

    print(f"\n{'='*60}")
    print("Searching for Daily Digest/Insights patterns...")
    print(f"{'='*60}\n")

    # Look for common patterns that might indicate Daily Insights
    insights_keywords = [
        "daily", "digest", "insight", "summary", "recap",
        "overview", "highlights", "key moments"
    ]

    def search_dict(obj, path=""):
        """Recursively search through nested dictionaries and lists."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key

                # Check if key name suggests Daily Insights
                if any(keyword in key.lower() for keyword in insights_keywords):
                    print(f"🔍 Found potential insight field: {current_path}")
                    print(f"   Value preview: {str(value)[:200]}")
                    print()

                search_dict(value, current_path)

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                search_dict(item, f"{path}[{i}]")

        elif isinstance(obj, str):
            # Check if string content suggests Daily Insights
            if any(keyword in obj.lower() for keyword in insights_keywords):
                if len(obj) > 50:  # Only flag longer text that might be insights
                    print(f"🔍 Found potential insight content at: {path}")
                    print(f"   Preview: {obj[:200]}")
                    print()

    search_dict(response_data)


def main():
    parser = argparse.ArgumentParser(
        description="Explore the Limitless API /v1/chats endpoint"
    )
    parser.add_argument(
        "--date",
        help="Date to query in YYYY-MM-DD format (e.g., 2025-11-20)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of results to return (default: 10)"
    )
    parser.add_argument(
        "--yesterday",
        action="store_true",
        help="Query yesterday's date"
    )
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Don't include markdown in response"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce verbosity"
    )
    parser.add_argument(
        "--save",
        help="Save response to specified JSON file"
    )

    args = parser.parse_args()

    # Determine date to query
    query_date = args.date
    if args.yesterday:
        yesterday = datetime.now() - timedelta(days=1)
        query_date = yesterday.strftime("%Y-%m-%d")

    # Make the API call
    response = explore_chats_endpoint(
        date=query_date,
        limit=args.limit,
        include_markdown=not args.no_markdown,
        verbose=not args.quiet
    )

    if response:
        # Search for Daily Insights patterns
        if not args.quiet:
            search_for_daily_insights(response)

        # Save to file if requested
        if args.save:
            try:
                with open(args.save, 'w') as f:
                    json.dump(response, f, indent=2)
                print(f"\n✅ Response saved to: {args.save}")
            except Exception as e:
                print(f"\n❌ Failed to save response: {e}")
    else:
        print("\n❌ No response received from API")
        sys.exit(1)


if __name__ == "__main__":
    main()


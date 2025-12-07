#!/usr/bin/env python3
"""
Simple test script to explore the /v1/chats endpoint.
Run this manually to see what the chats endpoint returns.
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in parent directory
# This handles both running from python/ and from root
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try loading from current directory
    load_dotenv()

# Get API key from environment
API_KEY = os.getenv("LIMITLESS_API_KEY", "YOUR_API_KEY_HERE")
API_URL = "https://api.limitless.ai"

def test_chats_endpoint():
    """Test the /v1/chats endpoint with yesterday's date."""

    # Get yesterday's date
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    endpoint = f"{API_URL}/v1/chats"
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    }
    params = {
        "date": yesterday,
        "limit": 10,
        "includeMarkdown": "true"
    }

    print(f"Testing endpoint: {endpoint}")
    print(f"Date: {yesterday}")
    print(f"Parameters: {json.dumps(params, indent=2)}")
    print("\nMaking request...\n")

    try:
        response = requests.get(endpoint, headers=headers, params=params, timeout=30)

        print(f"Status Code: {response.status_code}")
        print(f"\nResponse Headers:")
        for key, value in response.headers.items():
            if key.lower() not in ['set-cookie', 'authorization']:
                print(f"  {key}: {value}")

        print(f"\nResponse Body:")
        try:
            data = response.json()
            print(json.dumps(data, indent=2))

            # Save to file - create directory if it doesn't exist
            output_dir = Path(__file__).parent.parent / "exports"
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / "chats_test_response.json"

            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n✅ Response saved to: {output_file}")

        except json.JSONDecodeError:
            print(f"Raw text response:\n{response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if API_KEY == "YOUR_API_KEY_HERE":
        print("⚠️  Please set your LIMITLESS_API_KEY environment variable or edit this script.")
    else:
        test_chats_endpoint()


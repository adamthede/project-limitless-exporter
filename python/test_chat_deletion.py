#!/usr/bin/env python3
"""
Test chat deletion to see what error we get.
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

API_KEY = os.getenv("LIMITLESS_API_KEY")
API_URL = os.getenv("LIMITLESS_API_URL", "https://api.limitless.ai")

def test_chat_deletion():
    """Try to delete a single chat and see the full error."""

    # First, get one chat ID
    endpoint = f"{API_URL}/v1/chats"
    headers = {"X-API-Key": API_KEY, "Accept": "application/json"}
    params = {"limit": 1, "includeMarkdown": "false"}

    print("Fetching one chat to test deletion...\n")
    response = requests.get(endpoint, headers=headers, params=params, timeout=30)
    data = response.json()

    chats = data.get("data", {}).get("chats", [])
    if not chats:
        print("No chats found!")
        return

    chat = chats[0]
    chat_id = chat.get("id")
    summary = chat.get("summary", "Untitled")

    print(f"Chat to delete:")
    print(f"  ID: {chat_id}")
    print(f"  Summary: {summary}")
    print()

    # Try to delete it
    delete_endpoint = f"{API_URL}/v1/chats/{chat_id}"
    print(f"Attempting DELETE request to: {delete_endpoint}")
    print(f"Headers: X-API-Key: {API_KEY[:10]}...")
    print()

    try:
        response = requests.delete(delete_endpoint, headers=headers, timeout=30)

        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print()
        print("Response Body:")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_chat_deletion()

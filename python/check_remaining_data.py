#!/usr/bin/env python3
"""
Quick script to see what data remains on Limitless servers.
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

API_KEY = os.getenv("LIMITLESS_API_KEY")
API_URL = os.getenv("LIMITLESS_API_URL", "https://api.limitless.ai")

def check_lifelogs():
    """Check what lifelogs are on the server."""
    endpoint = f"{API_URL}/v1/lifelogs"
    headers = {"X-API-Key": API_KEY, "Accept": "application/json"}
    params = {"limit": 10, "includeMarkdown": "false"}

    response = requests.get(endpoint, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    lifelogs = data.get("data", {}).get("lifelogs", [])

    print(f"\n{'='*60}")
    print("Lifelogs on Server")
    print(f"{'='*60}")
    print(f"Count: {len(lifelogs)}\n")

    for lifelog in lifelogs:
        log_id = lifelog.get("id", "unknown")
        started = lifelog.get("startedAt", "unknown")
        ended = lifelog.get("endedAt", "unknown")
        print(f"  ID: {log_id}")
        print(f"  Started: {started}")
        print(f"  Ended: {ended}")
        print()

def check_chats():
    """Check summary of chats on the server."""
    endpoint = f"{API_URL}/v1/chats"
    headers = {"X-API-Key": API_KEY, "Accept": "application/json"}
    params = {"limit": 10, "includeMarkdown": "false"}

    response = requests.get(endpoint, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    chats = data.get("data", {}).get("chats", [])

    print(f"\n{'='*60}")
    print("Chats on Server (first 10)")
    print(f"{'='*60}\n")

    for chat in chats:
        chat_id = chat.get("id", "unknown")
        summary = chat.get("summary", "Untitled")[:50]
        created = chat.get("createdAt", "unknown")[:10]
        print(f"  [{created}] {summary} (ID: {chat_id[:8]}...)")

if __name__ == "__main__":
    if not API_KEY:
        print("Error: LIMITLESS_API_KEY not found")
        sys.exit(1)

    check_lifelogs()
    check_chats()
    print()

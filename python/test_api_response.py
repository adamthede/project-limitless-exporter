#!/usr/bin/env python3
"""
Test what the API actually returns to understand the response structure.
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

def test_api_response():
    """Fetch a few lifelogs and see what fields we get."""
    endpoint = f"{API_URL}/v1/lifelogs"
    headers = {"X-API-Key": API_KEY, "Accept": "application/json"}

    print("Testing API response structure...\n")

    # Test 1: Without markdown
    print("="*60)
    print("Test 1: includeMarkdown=false")
    print("="*60)
    params = {"limit": 2, "includeMarkdown": "false"}
    response = requests.get(endpoint, headers=headers, params=params, timeout=30)
    data = response.json()

    lifelogs = data.get("data", {}).get("lifelogs", [])
    if lifelogs:
        print(f"\nFound {len(lifelogs)} lifelogs")
        print("\nFirst lifelog structure:")
        print(json.dumps(lifelogs[0], indent=2))

    # Test 2: With markdown
    print("\n" + "="*60)
    print("Test 2: includeMarkdown=true")
    print("="*60)
    params = {"limit": 2, "includeMarkdown": "true"}
    response = requests.get(endpoint, headers=headers, params=params, timeout=30)
    data = response.json()

    lifelogs = data.get("data", {}).get("lifelogs", [])
    if lifelogs:
        print(f"\nFound {len(lifelogs)} lifelogs")
        print("\nFirst lifelog structure (markdown truncated):")
        lifelog = lifelogs[0].copy()
        if 'markdown' in lifelog:
            lifelog['markdown'] = lifelog['markdown'][:100] + "..." if len(lifelog['markdown']) > 100 else lifelog['markdown']
        print(json.dumps(lifelog, indent=2))

    # Test 3: With date filter
    print("\n" + "="*60)
    print("Test 3: With date=2025-12-05")
    print("="*60)
    params = {"limit": 5, "includeMarkdown": "false", "date": "2025-12-05"}
    response = requests.get(endpoint, headers=headers, params=params, timeout=30)
    data = response.json()

    lifelogs = data.get("data", {}).get("lifelogs", [])
    print(f"\nFound {len(lifelogs)} lifelogs for 2025-12-05")
    if lifelogs:
        print("\nFirst lifelog:")
        print(json.dumps(lifelogs[0], indent=2))

if __name__ == "__main__":
    test_api_response()

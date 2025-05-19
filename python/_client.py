import os
import requests
import tzlocal
import json # Added for better error handling if JSON parsing fails

def get_lifelogs(api_key,
                 api_url=os.getenv("LIMITLESS_API_URL") or "https://api.limitless.ai",
                 endpoint="v1/lifelogs",
                 limit=50,  # This is now the per-API-call limit
                 cursor=None, # This is the cursor for the API call
                 includeMarkdown=True,
                 includeHeadings=False, # Note: export_day_lifelogs.py doesn't use this param currently
                 date=None,
                 timezone=None,
                 direction="asc"):
    """
    Makes a single API call to the /lifelogs endpoint.
    Returns the full parsed JSON response from the API, or None on error.
    The calling function is responsible for handling pagination by using the 'cursor'
    from the 'meta' part of the returned response.
    """
    if not api_key:
        # Consider raising a ValueError or logging an error
        print("API key is required for get_lifelogs.")
        return None

    params = {
        "limit": limit,
        "includeMarkdown": "true" if includeMarkdown else "false",
        "includeHeadings": "true" if includeHeadings else "false",
        "direction": direction,
        "timezone": timezone if timezone else str(tzlocal.get_localzone())
    }

    if date:
        params["date"] = date
    if cursor:
        params["cursor"] = cursor

    # For debugging: Log the request being made
    # Mask the API key if it were part of the log, but it's in headers here.
    print(f"[DEBUG] Making API call to {api_url}/{endpoint} with params: {params}")

    try:
        response = requests.get(
            f"{api_url}/{endpoint}",
            headers={"X-API-Key": api_key},
            params=params,
            timeout=30 # Adding a timeout for the request
        )

        response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)

        return response.json() # Return the full parsed JSON response

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - Status: {response.status_code} - Response: {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        # This will catch the timeout we added above, and also connect timeouts
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred during the request: {req_err}")
    except json.JSONDecodeError as json_err:
        print(f"Failed to decode JSON response: {json_err}. Response text: {response.text if 'response' in locals() else 'Response object not available'}")
    except Exception as e:
        print(f"An unexpected error occurred in get_lifelogs: {e} (params: {params})") # Log params on unexpected error

    return None # Return None in case of any exception

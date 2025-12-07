# Lifelog Archiving & Analysis Workflow

This document outlines the workflow for exporting, summarizing, analyzing, and archiving your daily lifelogs using the provided Python scripts. The goal is to create a reliable local archive of your daily data, its AI-generated summaries, and usage analytics.

## 1. Directory Structure

All scripts are located in the `python/` directory. All exported data and reports will be stored within the `exports/` directory in your project root. This directory will have the following subdirectories:

- `exports/lifelogs/`: Contains the raw, concatenated markdown lifelogs for each day (e.g., `YYYY-MM-DD-lifelogs.md`).
- `exports/summaries/`: Contains the AI-generated summaries for each day (e.g., `YYYY-MM-DD-summary.md`).
- `exports/contents/`: Contains the structured JSON exports of lifelogs for each day (e.g., `YYYY-MM-DD-contents.json`). This includes full markdown per entry plus the `contents` array with detailed segments (text, timestamps, speaker info).
- `exports/analytics/`: Contains daily usage analytics reports as markdown files (e.g., `YYYY-MM-DD-analytics.md`) which include textual statistics and an embedded PNG timeline chart (e.g., `YYYY-MM-DD-usage-timeline.png`).

## 2. Environment Setup

1.  **Navigate to the `python/` directory.** All script commands should be run from here.
2.  **Create and activate a Python virtual environment** (see `README.md` for instructions).
3.  **Install dependencies:** Ensure you have a `requirements.txt` file in the `python/` directory. A comprehensive one would include:
    ```txt
    # For Limitless API interaction & basic scripting
    requests
    python-dotenv
    tzlocal

    # For summarization
    openai

    # For usage analytics
    pandas
    matplotlib
    ```
    Install with: `pip install -r requirements.txt`
4.  **API Keys:** Create a `.env` file in your `python/` directory (you can copy `python/.env.example` to `python/.env`). Add your API keys:
    ```env
    LIMITLESS_API_KEY="your_limitless_api_key_here"
    OPENAI_API_KEY="your_openai_api_key_here"
    ```

## 3. Scripts Overview

*   **`export_day_lifelogs.py`**:
    *   Fetches *all* lifelogs for a specific date (raw markdown), handling API pagination and retries.
    *   Saves to `exports/lifelogs/YYYY-MM-DD-lifelogs.md`.
    *   Idempotent and exits with a non-zero status on failure.
*   **`summarize_day.py`**:
    *   Takes an existing `exports/lifelogs/YYYY-MM-DD-lifelogs.md` file as input.
    *   Sends its content to OpenAI for summarization.
    *   Saves summary to `exports/summaries/YYYY-MM-DD-summary.md`.
*   **`export_day_contents_json.py`**:
    *   Fetches *all* lifelogs for a specific date, extracting full markdown and the structured `contents` array for each entry.
    *   Saves to `exports/contents/YYYY-MM-DD-contents.json`.
    *   Handles API pagination and retries.
*   **`batch_process_days.py`**:
    *   Orchestrates `export_day_lifelogs.py` and then `summarize_day.py` for a range of dates.
    *   Includes its own batch-level retry logic.
    *   If run without date arguments, it will automatically process days from the day after the last processed lifelog up to yesterday.
*   **`batch_export_contents_json.py`**:
    *   Orchestrates `export_day_contents_json.py` for a range of dates.
    *   Useful for backfilling the JSON data needed for analytics.
    *   Includes its own batch-level retry logic.
    *   If run without date arguments, it will automatically process days from the day after the last exported JSON content up to yesterday.
*   **`analyze_daily_usage.py`**:
    *   Processes `exports/contents/YYYY-MM-DD-contents.json` files for a single date or a date range.
    *   For each day, generates:
        *   Detailed usage statistics printed to the console.
        *   A timeline chart image: `exports/analytics/YYYY-MM-DD-usage-timeline.png`.
        *   A markdown report: `exports/analytics/YYYY-MM-DD-analytics.md` (includes stats and chart).
    *   If run without date arguments, it automatically determines the range: starts after the last analytics report (or earliest content if no reports) and processes up to yesterday or the latest available content data, whichever is earlier.

## 4. Recommended Workflow for Archiving & Analysis

This workflow aims to first secure your raw data and summaries, then optionally generate structured data for deeper analysis.

**Step 1: Daily Sync (Lifelogs & Summaries)**
Run `batch_process_days.py` daily. When run without date arguments, it will automatically fetch lifelogs and generate summaries for any days that were missed since the last run, up to and including the previous day. This is the recommended method for daily catch-up.

*   **Command (run from `python/` directory):**
    ```bash
    python batch_process_days.py
    ```

**Step 2 (Optional but Recommended for Analytics): Daily Sync (Structured JSON Contents)**
After successfully completing Step 1, run `batch_export_contents_json.py` without arguments. It will automatically export structured JSON data for any days processed in Step 1 that don't yet have corresponding JSON files, up to and including the previous day.

*   **Command (run from `python/` directory):**
    ```bash
    python batch_export_contents_json.py
    ```

**Step 3 (Optional): Daily Usage Analysis**
After successfully completing Step 2, run `analyze_daily_usage.py` without arguments. It will automatically generate analytics reports for any days that have content data but are missing an analytics report, up to the latest available content or yesterday.

*   **Command (run from `python/` directory):**
    ```bash
    python analyze_daily_usage.py
    ```

## 5. Backfilling Past Data

To backfill data for a specific range of past dates (e.g., if you're just starting or missed a large period), you can still provide explicit `START_DATE` and `END_DATE` arguments to the batch scripts:

**A. Lifelogs & Summaries:**
Use `batch_process_days.py`.
```bash
# Example: Backfill January 2025 (run from python/)
python batch_process_days.py 2025-01-01 2025-01-31
```

**B. Structured JSON Contents (after A is complete for the range):**
Use `batch_export_contents_json.py`.
```bash
# Example: Backfill January 2025 contents (run from python/)
python batch_export_contents_json.py 2025-01-01 2025-01-31
```

**C. Usage Analytics (after B is complete for the range):**
Use `analyze_daily_usage.py`.
```bash
# Example: Backfill January 2025 analytics (run from python/)
python analyze_daily_usage.py 2025-01-01 2025-01-31
```

**Customization & Troubleshooting:**
*   All batch scripts (`batch_process_days.py`, `batch_export_contents_json.py`) accept options like `--batch_max_retries`, `--export_page_limit`, etc. Use `--help` for details.
*   For individual date failures, you can run the single-day scripts (`export_day_lifelogs.py`, `summarize_day.py`, `export_day_contents_json.py`, `analyze_daily_usage.py YYYY-MM-DD`) for troubleshooting.

## 6. Important Considerations

*   **Order of Operations:** For analytics, ensure `contents.json` files are generated *before* running `analyze_daily_usage.py`.
*   **API Rate Limits & Errors:** Retry logic is built-in, but for very large backfills, monitor for persistent errors. Consider smaller date chunks if issues arise.
*   **Disk Space:** Ensure adequate disk space for exported files.

This workflow provides a robust way to archive your Limitless data and gain insights from it.
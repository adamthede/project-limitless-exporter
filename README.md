# Project - Limitless Exporter

This project initially began as a clone of the official limitless-api-examples repository.

## 🛳️ Python Script Examples

All commands below assume you are in the `python/` directory with your virtual environment activated and `.env` file configured.

### 1. Exporting Daily Lifelogs (Raw Markdown)

The `export_day_lifelogs.py` script fetches all lifelog entries for a specific date, handles API pagination and retries, and saves the concatenated raw markdown to `exports/lifelogs/YYYY-MM-DD-lifelogs.md`.

**Usage:**
```bash
python export_day_lifelogs.py YYYY-MM-DD
```
**Example:**
```bash
python export_day_lifelogs.py 2025-02-28
```

### 2. Generating Daily Summaries

The `summarize_day.py` script takes a previously exported daily lifelog markdown file and uses OpenAI (GPT-4.1-Nano by default) to generate a factual, journal-style summary. The summary is saved to `exports/summaries/YYYY-MM-DD-summary.md`.

**Usage:**
```bash
python summarize_day.py path/to/your/YYYY-MM-DD-lifelogs.md
```
**Example (after running export_day_lifelogs.py):**
```bash
python summarize_day.py ../exports/lifelogs/2025-02-28-lifelogs.md
```

### 3. Exporting Daily Lifelogs (Structured JSON)

The `export_day_contents_json.py` script fetches all lifelog entries for a specific date, including their full markdown and the structured `contents` array (which contains individual text segments, timestamps, speaker info, etc.). This is saved to `exports/contents/YYYY-MM-DD-contents.json`. This JSON format is ideal for detailed programmatic analysis.

**Usage:**
```bash
python export_day_contents_json.py YYYY-MM-DD
```
**Example:**
```bash
python export_day_contents_json.py 2025-02-28
```

### 4. Batch Processing: Daily Exports & Summaries

The `batch_process_days.py` script automates the process of exporting daily lifelogs (using `export_day_lifelogs.py`) and then generating summaries (using `summarize_day.py`) for a specified range of dates. It includes robust retry mechanisms for each step and for each day.

**Usage:**
```bash
python batch_process_days.py START_DATE END_DATE [OPTIONS]
```
**Example (process January 2025):**
```bash
python batch_process_days.py 2025-01-01 2025-01-31
```
Use `--help` to see available options for retry behavior and export parameters.

### 5. Batch Processing: Daily Structured JSON Exports

The `batch_export_contents_json.py` script automates the export of structured JSON data (using `export_day_contents_json.py`) for a specified range of dates. This is useful for backfilling the `exports/contents/` directory needed for usage analytics.

**Usage:**
```bash
python batch_export_contents_json.py START_DATE END_DATE [OPTIONS]
```
**Example (export contents for February 2025):**
```bash
python batch_export_contents_json.py 2025-02-01 2025-02-28
```
Use `--help` to see available options.

### 6. Analyzing Daily Usage & Generating Reports

The `analyze_daily_usage.py` script processes the structured JSON data from `exports/contents/` for a given date or date range. For each day, it:
-   Prints detailed usage statistics to the console.
-   Generates and saves a visual timeline chart of recording sessions to `exports/analytics/YYYY-MM-DD-usage-timeline.png`.
-   Creates a comprehensive markdown report (`exports/analytics/YYYY-MM-DD-analytics.md`) containing all statistics and embedding the timeline chart.

**Prerequisite:** Ensure the corresponding `YYYY-MM-DD-contents.json` files exist in `exports/contents/` for the dates you want to analyze.

**Usage (single day):**
```bash
python analyze_daily_usage.py YYYY-MM-DD
```
**Usage (date range):**
```bash
python analyze_daily_usage.py START_DATE END_DATE
```
**Example:**
```bash
python analyze_daily_usage.py 2025-02-28
# or for a range
python analyze_daily_usage.py 2025-03-01 2025-03-10
```

### Legacy Examples

-   **`export_markdown.py` (Legacy):** This was an initial simple script to print the most recent lifelog's markdown. It has been superseded by `export_day_lifelogs.py` for more robust daily archiving.
-   **Jupyter Notebooks (`notebooks/`):** The `notebooks/chart_usage.ipynb` provides an example of how to visualize usage from the API. The `analyze_daily_usage.py` script offers a more automated and report-oriented approach using local JSON data.

## Workflow for Archiving & Analysis

For a detailed guide on setting up your environment, daily syncing, backfilling data, and using these scripts in a cohesive workflow, please see the **[LIFELOG_ARCHIVING_WORKFLOW.md](LIFELOG_ARCHIVING_WORKFLOW.md)** document.

## ℹ️ More information

For more information on the API, see the [documentation](https://limitless.ai/developers/docs/api).

## 🛟 Support

If you need help, join our [Slack community](https://www.limitless.ai/community), follow us on [X/Twitter](https://twitter.com/limitlessai), or [email us](mailto:support@limitless.ai).

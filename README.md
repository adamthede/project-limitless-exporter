# Limitless Data Exporter

A comprehensive toolkit for exporting, archiving, and analyzing your Limitless AI data before account deletion.

> **Important Context:** This project was created to help Limitless users export their complete data before the Meta (Facebook) acquisition. On December 6, 2025, Limitless AI announced its acquisition by Meta, raising privacy concerns about the transfer of personal voice recordings and transcripts. This toolkit enables you to maintain complete local control of your data.

## What This Tool Does

- **Export lifelogs** - Download all conversation transcripts by day or date range
- **Archive chats** - Backup Daily Insights, summaries, and all conversations
- **Download audio** - Export raw audio recordings from your Pendant
- **Generate analytics** - Create usage reports and visualizations
- **Incremental sync** - Keep your archive up to date with new data
- **Obsidian-ready** - Organized exports compatible with Obsidian note-taking

## Why You Might Need This

1. **Privacy concerns** - Keep control of your personal data before it transfers to Meta
2. **Data preservation** - Maintain access to your lifelogs regardless of service changes
3. **Account deletion** - Required if you plan to delete your Limitless account
4. **Backup strategy** - Good practice to maintain local copies of important data

## Quick Start

### 1. Setup

```bash
cd python
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Access

Copy the example environment file and add your API key:

```bash
cp .env.example .env
# Edit .env and add your Limitless API key
# Get it from: https://www.limitless.ai/developers
```

### 3. Sync Everything

Run the master sync script to download all your data:

```bash
# Sync all missing data up to yesterday
python sync_everything.py

# Or sync a specific month
python sync_everything.py --month 2025-11

# Dry run to see what would be synced
python sync_everything.py --dry-run
```

This single command will:
1. ✅ Export missing lifelogs (transcripts)
2. ✅ Export structured JSON data
3. ✅ Sync all chats and conversations
4. ✅ Download audio recordings
5. ✅ Generate daily analytics
6. ✅ Generate monthly analytics

**All in the correct order with dependency handling.**

## Archive Structure

After syncing, your data will be organized in the `exports/` directory:

```
exports/
  lifelogs/              # Daily transcripts (markdown)
    2025-03-01-lifelogs.md
    2025-03-02-lifelogs.md
    ...

  contents/              # Structured JSON data
    2025-03-01-contents.json
    ...

  insights/              # Limitless-generated Daily Insights
    2025-03/
      2025-03-01-daily-insights.md
      ...

  daily-summaries/       # Your custom daily summaries
    2025-03/
      ...

  chats/                 # All other conversations
    2025-03/
      ...

  audio/                 # Raw audio recordings (.ogg)
    2025-03/
      2025-03-01/
        2025-03-01-morning-0700.ogg
        ...

  analytics/             # Usage reports and charts
    2025-03-01-analytics.md
    2025-03-01-usage-timeline.png
    ...
```

## Documentation

- **[docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - Quick command reference
- **[docs/COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md)** - Comprehensive guide covering everything
- **[docs/SYNC_GUIDE.md](docs/SYNC_GUIDE.md)** - Complete sync workflow and automation
- **[docs/OBSIDIAN_GUIDE.md](docs/OBSIDIAN_GUIDE.md)** - Using exports with Obsidian
- **[docs/DATA_DELETION_PROCESS.md](docs/DATA_DELETION_PROCESS.md)** - How to delete data from Limitless servers

### Specific Topics

- **[docs/CHAT_ANALYSIS_GUIDE.md](docs/CHAT_ANALYSIS_GUIDE.md)** - Analyzing chat patterns
- **[docs/DAILY_INSIGHTS_GUIDE.md](docs/DAILY_INSIGHTS_GUIDE.md)** - Daily Insights export
- **[docs/EXPLORING_CHATS_ENDPOINT.md](docs/EXPLORING_CHATS_ENDPOINT.md)** - API details
- **[docs/LIFELOG_ARCHIVING_WORKFLOW.md](docs/LIFELOG_ARCHIVING_WORKFLOW.md)** - Complete workflow

## Key Features

### Smart Incremental Sync
Only downloads new data, making regular backups fast and efficient.

### Complete Data Coverage
- Lifelogs (transcripts)
- Audio recordings (Ogg Opus format)
- All chat conversations
- Daily Insights
- User-created prompts and responses

### Export Formats
- **Markdown** - Human-readable, Obsidian-compatible
- **JSON** - Structured data for analysis
- **Audio** - Raw Ogg Opus recordings
- **PNG** - Usage timeline visualizations

### Data Organization
Files are automatically organized by:
- Date (YYYY-MM-DD format)
- Type (insights, summaries, chats)
- Month subdirectories for better navigation

## Common Commands

```bash
# Sync everything (recommended)
python sync_everything.py

# Sync specific month
python sync_everything.py --month 2025-11

# Export lifelogs for a single day
python export_day_lifelogs.py 2025-03-01

# Download audio for a day
python batch_export_audio.py 2025-03-01

# Sync all chats
python sync_all_chats.py

# Generate analytics
python analyze_daily_usage.py 2025-03-01
```

## Data Deletion

If you want to delete your data from Limitless servers after exporting:

1. **Backup first** - Run `sync_everything.py` to ensure you have everything
2. **Verify backup** - Check that all data exported successfully
3. **Read the guide** - See [docs/DATA_DELETION_PROCESS.md](docs/DATA_DELETION_PROCESS.md)
4. **Run deletion script** - Use `python delete_all_data.py` (with caution)
5. **Send formal request** - Email support@limitless.ai for complete deletion

**Warning:** API-based deletion has limitations. A formal GDPR/CCPA deletion request is recommended for complete removal.

## Privacy & Security

- **Your API key** - Never commit `.env` file to version control
- **Personal data** - The `exports/` directory contains all your personal data and is excluded from git
- **Audio files** - Raw recordings are excluded from git by default
- **Local-only** - All exports stay on your machine unless you explicitly share them

## Requirements

- Python 3.8+
- Limitless API key ([get one here](https://www.limitless.ai/developers))
- Optional: OpenAI API key (for summarization features)

## About This Project

This began as a fork of the official [limitless-api-examples](https://github.com/limitless-ai-inc/limitless-api-examples) repository and was significantly expanded to:

1. Provide comprehensive data export capabilities
2. Enable users to maintain data sovereignty
3. Facilitate account deletion while preserving personal records
4. Support privacy-conscious users concerned about the Meta acquisition

## License

MIT License - See [LICENSE](LICENSE) for details

## Support

- **Limitless API Documentation:** https://limitless.ai/developers/docs/api
- **Limitless Community:** https://www.limitless.ai/community
- **Issues:** Please report issues on GitHub

## Disclaimer

This is a community-maintained tool and is not officially affiliated with or endorsed by Limitless AI or Meta. Use at your own discretion. The authors are not responsible for any data loss or issues arising from the use of this software.

Always verify your backups before deleting data from any service.

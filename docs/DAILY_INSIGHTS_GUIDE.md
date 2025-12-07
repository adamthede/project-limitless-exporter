# Daily Insights Export Guide

## 🎉 Success! We Found Your Daily Insights!

The `/v1/chats` endpoint provides access to your **Daily Insights** - the rich daily summaries that Limitless generates automatically. These insights include:

- ✨ Daily Narrative & Highlights
- 📌 Key Follow-Ups and Action Items
- ✅ Decision Log
- 🌱 Opportunities for Growth
- 🚩 Red Flags & Recurring Patterns
- 💡 Knowledge Nuggets
- 📇 Personal CRM Digest
- 💬 Memorable Exchanges

## 📊 What We Discovered

### API Response Structure

The `/v1/chats` endpoint returns:

```json
{
  "data": {
    "chats": [
      {
        "id": "unique_chat_id",
        "summary": "Daily insights",
        "createdAt": "2025-11-21T10:07:52.672Z",
        "messages": [
          {
            "text": "Create today's Daily insights page...",
            "user": {"role": "user", "name": "Adam Thede"}
          },
          {
            "text": "# Overview & Action\n\n## ✨ Daily Narrative...",
            "user": {"role": "assistant", "name": "Assistant"}
          }
        ],
        "visibility": "private",
        "startedAt": "2025-11-21T10:07:52.672Z"
      }
    ]
  },
  "meta": {
    "chats": {
      "count": 10,
      "nextCursor": "cursor_for_pagination"
    }
  }
}
```

### Key Features

✅ **Pagination Supported** - Use `nextCursor` to fetch historical insights
✅ **Rich Markdown Content** - Full formatted insights with sections and emojis
✅ **Date Information** - `createdAt` and `startedAt` timestamps
✅ **Searchable** - Filter by `summary: "Daily insights"`

## 🚀 How to Use

### 1. Export a Single Day's Insights

```bash
cd python
source venv/bin/activate
python export_daily_insights.py 2025-11-20
```

This will save to: `exports/insights/2025-11-20-daily-insights.md`

### 2. Batch Export Multiple Days

**Export a date range:**
```bash
python batch_export_insights.py 2025-11-01 2025-11-30
```

**Export all available insights:**
```bash
python batch_export_insights.py --all
```

**Export recent insights (last 30 days):**
```bash
python batch_export_insights.py --recent 30
```

### 3. Test the Endpoint

Use the simple test script to explore:
```bash
python test_chats_simple.py
```

This saves the raw API response to `exports/chats_test_response.json`

## 📁 Output Structure

After running the export scripts, your directory will look like:

```
exports/
  insights/
    2025-11-01-daily-insights.md
    2025-11-02-daily-insights.md
    2025-11-03-daily-insights.md
    ...
    2025-11-20-daily-insights.md
```

Each file contains:
- Header with metadata (date, chat ID, creation timestamp)
- Full Daily Insights content in markdown format
- All sections: Overview, Highlights, Follow-ups, Reflections, etc.

## 💡 Use Cases

### Personal Knowledge Management
- Build a searchable archive of daily insights
- Track patterns in your behavior and decisions over time
- Review key follow-ups and action items

### Journaling & Reflection
- Use Daily Insights as a starting point for deeper reflection
- Track personal growth opportunities identified by the AI
- Review memorable exchanges and conversations

### Productivity & Task Management
- Extract action items from the "Key Follow-Ups" section
- Track decisions made over time
- Monitor unresolved questions

### Relationship Management
- Use the "Personal CRM Digest" to remember important details about people
- Track memorable conversations
- Note relationship-building opportunities

## 🔄 Integration Ideas

### Combine with Other Exports

You now have three complementary data sources:

1. **Lifelogs** (`exports/lifelogs/`) - Raw conversation transcripts
2. **Contents** (`exports/contents/`) - Structured JSON with timestamps
3. **Daily Insights** (`exports/insights/`) - AI-generated summaries and analysis

### Potential Workflows

**Daily Review Workflow:**
```bash
# 1. Export yesterday's insights
python export_daily_insights.py $(date -v-1d +%Y-%m-%d)

# 2. Review the markdown file
cat exports/insights/$(date -v-1d +%Y-%m-%d)-daily-insights.md

# 3. Extract action items (manual or automated)
```

**Weekly Backfill:**
```bash
# Export the last 7 days
python batch_export_insights.py --recent 7
```

**Full Archive:**
```bash
# One-time export of all available insights
python batch_export_insights.py --all
```

## 📝 Important Notes

### Timing
- Daily Insights are typically generated **the day after** the activity
- Insights for November 20th might be created on November 21st
- The scripts search with a 1-day tolerance to handle this

### Rate Limits
- The API has rate limits (180 requests/minute by default)
- Batch scripts include delays between requests
- Large exports may take several minutes

### Data Availability
- Daily Insights depend on having lifelog data for that day
- Not every day may have insights (e.g., if no pendant usage)
- The scripts will skip days without insights

## 🛠️ Troubleshooting

### "No Daily Insights found"
- Check if you had pendant activity on that date
- Remember insights are created the day after
- Try searching for the next day's date

### API Key Errors
- Ensure `LIMITLESS_API_KEY` is set in your `.env` file
- The `.env` file should be in the `limitless-api-examples` root directory

### Rate Limit Errors
- The scripts include automatic retries
- If you hit limits, wait a minute and try again
- Consider using smaller date ranges

## 🎯 Next Steps

Now that you have access to Daily Insights, you can:

1. **Export your historical insights** - Run the batch export for all available data
2. **Set up a daily routine** - Add the export to your morning routine
3. **Build custom analysis** - Parse the markdown to extract specific sections
4. **Integrate with other tools** - Feed insights into your note-taking system
5. **Create visualizations** - Track patterns in your growth opportunities or decisions

## 📚 Related Documentation

- Main README: `README.md`
- Chats Endpoint Exploration: `EXPLORING_CHATS_ENDPOINT.md`
- Lifelog Archiving Workflow: `LIFELOG_ARCHIVING_WORKFLOW.md`

---

**Congratulations!** You now have programmatic access to your Daily Insights. This is a powerful tool for self-reflection, productivity, and personal growth. 🚀


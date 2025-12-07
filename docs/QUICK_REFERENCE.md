# Quick Reference Card

## 🚀 Most Common Commands

### ⭐ Complete Sync (Everything at Once)
```bash
cd python && source venv/bin/activate
python sync_everything.py
```

**This one command syncs:**
- Lifelogs
- Contents JSON
- All chats
- Audio recordings
- Daily analytics
- Monthly analytics

### Sync Specific Month
```bash
python sync_everything.py --month 2025-11
```

### Preview What Would Sync
```bash
python sync_everything.py --dry-run
```

### Check Archive Status
```bash
python count_archive.py
```

### Sync Only Chats (Quick)
```bash
python sync_all_chats.py
```

---

## 📊 Your Data Summary

| Type | Count | Location |
|------|-------|----------|
| Daily Insights | 79 | `exports/insights/` |
| Daily Summaries | 83 | `exports/daily-summaries/` |
| Done Better | 83 | `exports/done-better/` |
| Other Chats | 232+ | `exports/chats/` |
| **TOTAL** | **477** | |

---

## 🔑 Key Facts

### Built-in vs User Chats
- ❌ No API field distinguishes them
- ✅ Check first user message text
- Built-in prompt: "Create today's Daily insights page based on my lifelog entries."

### Sync Behavior
- **First run:** Downloads all (~477 chats, 5-10 min)
- **Updates:** Only new chats (< 1 minute)
- **Smart:** Skips existing files automatically

### Archive Organization
- By series (insights, summaries, etc.)
- By date (YYYY-MM subdirectories)
- Markdown format (searchable, readable)

---

## 📁 File Locations

```
limitless-api-examples/
├── python/              # All scripts here
│   ├── venv/           # Virtual environment
│   ├── sync_all_chats.py      ⭐ Main sync script
│   ├── analyze_chats.py       # Discover patterns
│   ├── count_archive.py       # Check status
│   └── ...
├── exports/            # Your archive
│   ├── insights/
│   ├── daily-summaries/
│   ├── done-better/
│   └── chats/
├── .env                # API key here
└── README.md           # Full documentation
```

---

## 🛠️ Common Tasks

### Weekly Backup
```bash
python sync_all_chats.py
```

### Analyze Your Chats
```bash
python analyze_chats.py --save-raw
```

### Export Specific Type
```bash
python export_all_chats.py --filter "Daily Summary"
```

### Export Date Range
```bash
python export_all_chats.py --start 2025-11-01 --end 2025-11-30
```

### Single Day Lifelog
```bash
python export_day_lifelogs.py 2025-11-20
```

### Usage Analytics
```bash
python analyze_daily_usage.py 2025-11-20
```

---

## 🔧 Troubleshooting

### API Key Issues
```bash
# Check if .env exists
cat ../.env

# Should show:
LIMITLESS_API_KEY=your_key_here
```

### Count Doesn't Match
```bash
# Fill any gaps
python sync_all_chats.py
```

### See What's New
```bash
# Dry run first
python sync_all_chats.py --dry-run
```

### Detailed Progress
```bash
# Verbose mode
python sync_all_chats.py --verbose
```

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| `README.md` | Complete script reference |
| `COMPLETE_GUIDE.md` | Everything you need to know |
| `SYNC_GUIDE.md` | Sync script details |
| `CHAT_ANALYSIS_GUIDE.md` | Pattern analysis |
| `DAILY_INSIGHTS_GUIDE.md` | Daily Insights specifics |

---

## ⏰ Recommended Schedule

### Weekly (Best)
```bash
# Every Sunday evening
python sync_all_chats.py
```

### Monthly (Minimum)
```bash
# First of each month
python sync_all_chats.py
```

### Automated
```bash
# Add to crontab
0 20 * * 0 cd /path/to/python && ./venv/bin/python sync_all_chats.py
```

---

## ✅ Quick Checklist

- [ ] `.env` file configured with API key
- [ ] Virtual environment activated
- [ ] Initial sync completed
- [ ] Archive verified with `count_archive.py`
- [ ] Weekly sync scheduled
- [ ] `exports/` backed up to cloud/external drive

---

## 🎯 One-Liner Summary

**Keep your archive updated:**
```bash
cd python && source venv/bin/activate && python sync_all_chats.py
```

That's it! 🎉


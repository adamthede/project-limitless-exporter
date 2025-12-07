#!/usr/bin/env python3
"""
Generate Obsidian-friendly index files for your Limitless archive.

Creates navigable index pages with wiki-links that work perfectly in Obsidian:
- Master index (overview of everything)
- Monthly indexes (all content for each month)
- Daily indexes (all content for each day)
- Type indexes (by content type: insights, summaries, etc.)

Usage:
    python generate_index.py
    python generate_index.py --month 2025-11
    python generate_index.py --rebuild-all
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from calendar import monthrange

def scan_archive():
    """
    Scan the entire archive and catalog all files.

    Returns:
        dict: Organized catalog of all files
    """
    base_dir = Path(__file__).parent.parent / "exports"

    catalog = {
        "insights": [],
        "daily_summaries": [],
        "done_better": [],
        "chats": [],
        "lifelogs": [],
        "contents": [],
        "summaries": [],
        "analytics": [],
        "audio": []
    }

    # Scan each directory
    for category, subdir in [
        ("insights", "insights"),
        ("daily_summaries", "daily-summaries"),
        ("done_better", "done-better"),
        ("chats", "chats"),
        ("lifelogs", "lifelogs"),
        ("contents", "contents"),
        ("summaries", "summaries"),
        ("analytics", "analytics"),
        ("audio", "audio")
    ]:
        dir_path = base_dir / subdir
        if not dir_path.exists():
            continue

        # Find all files
        if category in ["lifelogs", "contents", "summaries"]:
            # These are flat directories
            for file in dir_path.glob("*"):
                if file.is_file():
                    catalog[category].append({
                        "path": file,
                        "relative_path": file.relative_to(base_dir),
                        "name": file.stem,
                        "date": extract_date_from_filename(file.name)
                    })
        else:
            # These have YYYY-MM subdirectories
            for file in dir_path.rglob("*"):
                if file.is_file() and not file.name.startswith('.'):
                    catalog[category].append({
                        "path": file,
                        "relative_path": file.relative_to(base_dir),
                        "name": file.stem,
                        "date": extract_date_from_filename(file.name)
                    })

    # Sort by date
    for category in catalog:
        catalog[category].sort(key=lambda x: x["date"] if x["date"] else "")

    return catalog


def extract_date_from_filename(filename):
    """Extract date from filename (YYYY-MM-DD format)."""
    import re
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    return match.group(1) if match else None


def generate_master_index(catalog, output_path):
    """Generate the master index page."""

    # Count items
    total_files = sum(len(files) for files in catalog.values())

    # Get date range
    all_dates = []
    for category in catalog.values():
        all_dates.extend([item["date"] for item in category if item["date"]])

    if all_dates:
        earliest = min(all_dates)
        latest = max(all_dates)
    else:
        earliest = latest = "Unknown"

    # Count by month
    months = defaultdict(int)
    for category in catalog.values():
        for item in category:
            if item["date"]:
                month = item["date"][:7]  # YYYY-MM
                months[month] += 1

    md = f"""# 📚 Limitless Archive Index

*Last updated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}*

---

## 📊 Archive Overview

- **Total Files:** {total_files:,}
- **Date Range:** {earliest} to {latest}
- **Months Covered:** {len(months)}

### By Category

| Category | Files | Description |
|----------|-------|-------------|
| Daily Insights | {len(catalog['insights']):,} | Limitless-generated daily summaries |
| Daily Summaries | {len(catalog['daily_summaries']):,} | Your daily summary prompts |
| Done Better | {len(catalog['done_better']):,} | Your daily reflections |
| Other Chats | {len(catalog['chats']):,} | All other conversations |
| Lifelogs | {len(catalog['lifelogs']):,} | Raw conversation transcripts |
| Contents JSON | {len(catalog['contents']):,} | Structured data files |
| Summaries | {len(catalog['summaries']):,} | AI-generated summaries |
| Analytics | {len(catalog['analytics']):,} | Usage reports and charts |
| Audio | {len(catalog['audio']):,} | Audio recordings |

---

## 📅 Browse by Month

"""

    # Add monthly links
    for month in sorted(months.keys(), reverse=True):
        month_date = datetime.strptime(month, "%Y-%m")
        month_name = month_date.strftime("%B %Y")
        count = months[month]

        md += f"- [[Index - {month}|{month_name}]] ({count} files)\n"

    md += f"""

---

## 📂 Browse by Type

### Daily Content
- [[Index - Daily Insights]] ({len(catalog['insights'])} files)
- [[Index - Daily Summaries]] ({len(catalog['daily_summaries'])} files)
- [[Index - Done Better]] ({len(catalog['done_better'])} files)

### Conversations
- [[Index - Chats]] ({len(catalog['chats'])} files)

### Raw Data
- [[Index - Lifelogs]] ({len(catalog['lifelogs'])} files)
- [[Index - Audio]] ({len(catalog['audio'])} files)

### Analysis
- [[Index - Analytics]] ({len(catalog['analytics'])} files)

---

## 🔍 Quick Access

### Recent Content (Last 7 Days)

"""

    # Add recent files
    recent_cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    for category_name, category_key in [
        ("Daily Insights", "insights"),
        ("Daily Summaries", "daily_summaries"),
        ("Done Better", "done_better")
    ]:
        recent = [item for item in catalog[category_key] if item["date"] and item["date"] >= recent_cutoff]
        if recent:
            md += f"\n**{category_name}:**\n"
            for item in sorted(recent, key=lambda x: x["date"], reverse=True)[:7]:
                date_obj = datetime.strptime(item["date"], "%Y-%m-%d")
                date_display = date_obj.strftime("%a, %b %d")
                # Use relative path for wiki-link
                link_path = str(item["relative_path"]).replace(".md", "")
                md += f"- [[{link_path}|{date_display}]]\n"

    md += f"""

---

## 📖 How to Use This Archive

### In Obsidian
- Click any link to open that file
- Use Cmd/Ctrl + O to quick-open files
- Use search to find specific content
- Create your own notes and link to archive files

### Updating the Index
Run the index generator script:
```bash
python generate_index.py
```

---

*This index was automatically generated. Re-run `generate_index.py` to update.*
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)


def generate_monthly_index(catalog, year_month, output_path):
    """Generate index for a specific month."""

    month_date = datetime.strptime(year_month, "%Y-%m")
    month_name = month_date.strftime("%B %Y")

    # Filter items for this month
    month_items = defaultdict(list)
    for category, items in catalog.items():
        for item in items:
            if item["date"] and item["date"].startswith(year_month):
                month_items[category].append(item)

    if not any(month_items.values()):
        return  # No data for this month

    # Count by day
    days = defaultdict(lambda: defaultdict(int))
    for category, items in month_items.items():
        for item in items:
            date = item["date"]
            days[date][category] += 1

    md = f"""# 📅 {month_name}

[[Index - Master|← Back to Master Index]]

---

## 📊 Month Overview

- **Total Files:** {sum(len(items) for items in month_items.values())}
- **Days with Data:** {len(days)}

### By Category

| Category | Files |
|----------|-------|
"""

    for category, items in month_items.items():
        if items:
            category_display = category.replace("_", " ").title()
            md += f"| {category_display} | {len(items)} |\n"

    md += f"""

---

## 📆 Daily Content

"""

    # List all days
    for date in sorted(days.keys(), reverse=True):
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        day_display = date_obj.strftime("%A, %B %d, %Y")

        md += f"\n### {day_display}\n\n"

        # Add links for each category
        for category, items in month_items.items():
            day_items = [item for item in items if item["date"] == date]
            if day_items:
                category_display = category.replace("_", " ").title()
                md += f"**{category_display}:**\n"
                for item in day_items:
                    link_path = str(item["relative_path"]).replace(".md", "").replace(".ogg", "")
                    file_name = item["path"].name
                    md += f"- [[{link_path}|{file_name}]]\n"
                md += "\n"

    md += f"""

---

*[[Index - Master|← Back to Master Index]]*
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)


def generate_type_index(catalog, category_key, category_display, output_path):
    """Generate index for a specific content type."""

    items = catalog[category_key]

    if not items:
        return

    # Group by month
    by_month = defaultdict(list)
    for item in items:
        if item["date"]:
            month = item["date"][:7]
            by_month[month].append(item)

    md = f"""# 📂 {category_display}

[[Index - Master|← Back to Master Index]]

---

## 📊 Overview

- **Total Files:** {len(items)}
- **Months:** {len(by_month)}

---

## 📅 By Month

"""

    for month in sorted(by_month.keys(), reverse=True):
        month_date = datetime.strptime(month, "%Y-%m")
        month_name = month_date.strftime("%B %Y")
        month_items = by_month[month]

        md += f"\n### {month_name} ({len(month_items)} files)\n\n"

        for item in sorted(month_items, key=lambda x: x["date"], reverse=True):
            date_obj = datetime.strptime(item["date"], "%Y-%m-%d")
            date_display = date_obj.strftime("%a, %b %d")
            link_path = str(item["relative_path"]).replace(".md", "").replace(".ogg", "")
            md += f"- [[{link_path}|{date_display}]]\n"

    md += f"""

---

*[[Index - Master|← Back to Master Index]]*
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Obsidian-friendly index files for Limitless archive"
    )
    parser.add_argument(
        "--month",
        help="Generate index for specific month (YYYY-MM)"
    )
    parser.add_argument(
        "--rebuild-all",
        action="store_true",
        help="Rebuild all index files"
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("📚 Generating Archive Indexes")
    print(f"{'='*60}\n")

    # Scan archive
    print("📂 Scanning archive...")
    catalog = scan_archive()

    total_files = sum(len(files) for files in catalog.values())
    print(f"   Found {total_files:,} files across {len(catalog)} categories\n")

    exports_dir = Path(__file__).parent.parent / "exports"

    # Generate master index
    print("📝 Generating master index...")
    master_path = exports_dir / "Index - Master.md"
    generate_master_index(catalog, master_path)
    print(f"   ✅ {master_path.name}")

    # Generate monthly indexes
    if args.rebuild_all or not args.month:
        print("\n📅 Generating monthly indexes...")

        # Find all months
        all_dates = []
        for category in catalog.values():
            all_dates.extend([item["date"] for item in category if item["date"]])

        months = sorted(set(date[:7] for date in all_dates if date))

        for month in months:
            month_path = exports_dir / f"Index - {month}.md"
            generate_monthly_index(catalog, month, month_path)
            month_date = datetime.strptime(month, "%Y-%m")
            month_name = month_date.strftime("%b %Y")
            print(f"   ✅ {month_name}")

    elif args.month:
        print(f"\n📅 Generating index for {args.month}...")
        month_path = exports_dir / f"Index - {args.month}.md"
        generate_monthly_index(catalog, args.month, month_path)
        print(f"   ✅ {month_path.name}")

    # Generate type indexes
    if args.rebuild_all:
        print("\n📂 Generating type indexes...")

        type_configs = [
            ("insights", "Daily Insights"),
            ("daily_summaries", "Daily Summaries"),
            ("done_better", "Done Better"),
            ("chats", "Chats"),
            ("lifelogs", "Lifelogs"),
            ("analytics", "Analytics"),
            ("audio", "Audio")
        ]

        for category_key, category_display in type_configs:
            if catalog[category_key]:
                type_path = exports_dir / f"Index - {category_display}.md"
                generate_type_index(catalog, category_key, category_display, type_path)
                print(f"   ✅ {category_display}")

    # Summary
    print(f"\n{'='*60}")
    print("✅ Index Generation Complete!")
    print(f"{'='*60}")
    print(f"\n📍 Open in Obsidian:")
    print(f"   File → Open Vault → {exports_dir}")
    print(f"\n📖 Start here:")
    print(f"   Open: Index - Master.md")
    print(f"\n💡 To update indexes:")
    print(f"   python generate_index.py --rebuild-all")


if __name__ == "__main__":
    main()


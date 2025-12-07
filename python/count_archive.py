#!/usr/bin/env python3
"""
Count files in the archive and compare to what should be there.
"""

from pathlib import Path

base_dir = Path(__file__).parent.parent / "exports"

# Count files in each directory
insights_count = len(list((base_dir / "insights").rglob("*.md"))) if (base_dir / "insights").exists() else 0
daily_summaries_count = len(list((base_dir / "daily-summaries").rglob("*.md"))) if (base_dir / "daily-summaries").exists() else 0
done_better_count = len(list((base_dir / "done-better").rglob("*.md"))) if (base_dir / "done-better").exists() else 0
chats_count = len(list((base_dir / "chats").rglob("*.md"))) if (base_dir / "chats").exists() else 0

total = insights_count + daily_summaries_count + done_better_count + chats_count

print("="*60)
print("Archive File Count")
print("="*60)
print(f"  insights/          {insights_count:3d} files")
print(f"  daily-summaries/   {daily_summaries_count:3d} files")
print(f"  done-better/       {done_better_count:3d} files")
print(f"  chats/             {chats_count:3d} files")
print("-"*60)
print(f"  TOTAL:             {total:3d} files")
print("="*60)
print()
print("Expected:")
print(f"  Daily insights:     79 (Limitless-generated)")
print(f"  Daily Summary:      83 (Your summaries)")
print(f"  Done Better:        83 (Your reflections)")
print(f"  Other chats:       232 (Everything else)")
print(f"  TOTAL:             477")
print()
print(f"Difference: {477 - total} files missing")


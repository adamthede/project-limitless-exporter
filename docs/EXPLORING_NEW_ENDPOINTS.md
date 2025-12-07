# Exploring Audio & Reminders Endpoints

## 🎯 Overview

This guide helps you investigate two additional Limitless API capabilities:
1. **Audio Files** - Access to raw audio recordings
2. **Reminders** - Push notification reminders sent by Limitless

## 🎵 Audio Endpoint Investigation

### What We're Looking For

- Access to raw audio recordings from your Pendant
- Audio file metadata (duration, timestamps, etc.)
- Download URLs for audio files
- Organization by date or lifelog

### How to Explore

**Basic exploration:**
```bash
cd python
source venv/bin/activate
python explore_audio_endpoint.py
```

**With specific date:**
```bash
python explore_audio_endpoint.py --date 2025-11-20
```

**Save response for analysis:**
```bash
python explore_audio_endpoint.py --save audio_test.json
```

**Yesterday's audio:**
```bash
python explore_audio_endpoint.py --yesterday
```

### What to Expect

**If the endpoint exists:**
```json
{
  "data": {
    "audio": [
      {
        "id": "...",
        "url": "https://...",
        "duration": 123,
        "createdAt": "...",
        "lifelog_id": "..."
      }
    ]
  },
  "meta": {
    "nextCursor": "..."
  }
}
```

**If it doesn't exist:**
- 404 Not Found
- 403 Forbidden (exists but no access)
- Empty response

### Possible Outcomes

#### ✅ Success
- You get audio file URLs
- Can download recordings
- Access metadata

**Next steps:**
- Create audio download script
- Organize by date
- Link to lifelogs

#### ⚠️ Access Restricted
- Endpoint exists but returns 403
- May require special API permissions
- Contact Limitless support

**Next steps:**
- Request audio API access
- Check if available in higher tier

#### ❌ Not Available
- 404 Not Found
- Feature not in API yet

**Alternatives:**
- Audio might be embedded in lifelog data
- May need to use web interface
- Future API update needed

## 🔔 Reminders Endpoint Investigation

### What We're Looking For

- Push notification reminders
- Reminder content and timing
- Reminder status (sent, pending, dismissed)
- Ability to create/manage reminders via API

### How to Explore

**Try all possible endpoints:**
```bash
python explore_reminders_endpoint.py
```

**Save results:**
```bash
python explore_reminders_endpoint.py --save reminders_test.json
```

**Quiet mode (less verbose):**
```bash
python explore_reminders_endpoint.py --quiet
```

### Endpoints Being Tested

The script automatically tries:
- `/v1/reminders`
- `/v1/notifications`
- `/v1/alerts`
- `/v1/tasks`
- `/v1/todos`

### What to Expect

**If reminders endpoint exists:**
```json
{
  "data": {
    "reminders": [
      {
        "id": "...",
        "text": "Remember to...",
        "scheduledFor": "2025-11-21T10:00:00Z",
        "status": "sent",
        "createdAt": "..."
      }
    ]
  }
}
```

**If it doesn't exist:**
- All endpoints return 404
- May be part of another endpoint

### Possible Outcomes

#### ✅ Success
- Found working reminders endpoint
- Can access reminder data
- See notification history

**Next steps:**
- Create reminders export script
- Archive reminder history
- Analyze reminder patterns

#### 🔍 Hidden in Chats
- No dedicated endpoint
- Reminders might be special chats

**How to check:**
```bash
# Search your chats for reminders
python analyze_chats.py --save-raw
grep -i "reminder" ../exports/all_chats_raw.json
```

**Look for:**
- Chat summaries containing "reminder"
- System-generated messages
- Specific prompt patterns

#### ❌ Not Available Yet
- No endpoint found
- Feature not in API

**Alternatives:**
- Reminders may be app-only
- Check for future API updates
- Contact Limitless support

## 🔬 Systematic Investigation Process

### Step 1: Test Audio Endpoint

```bash
# Test basic audio endpoint
python explore_audio_endpoint.py --save audio_test.json

# Check the response
cat ../exports/audio_test.json
```

**Analyze results:**
- Status code (200 = success, 404 = not found, 403 = forbidden)
- Response structure
- Available fields
- Data format

### Step 2: Test Reminders Endpoint

```bash
# Try all possible reminders endpoints
python explore_reminders_endpoint.py --save reminders_test.json

# Check the response
cat ../exports/reminders_test.json
```

**Analyze results:**
- Which endpoints were tried
- Status codes for each
- Any successful responses
- Error messages

### Step 3: Search Existing Data

If dedicated endpoints don't exist, search your archived data:

```bash
# Search chats for audio references
grep -i "audio\|recording\|media" ../exports/all_chats_raw.json

# Search chats for reminders
grep -i "reminder\|notification\|alert" ../exports/all_chats_raw.json

# Search lifelogs
grep -i "reminder" ../exports/lifelogs/*.md
```

### Step 4: Check Lifelog Contents

Structured lifelog data might contain references:

```bash
# Look in contents JSON
grep -i "audio\|reminder" ../exports/contents/*.json
```

## 📊 Expected Scenarios

### Scenario A: Both Endpoints Exist ✅

**Audio:** `/v1/audio` returns data
**Reminders:** `/v1/reminders` returns data

**Action:**
- Create download/export scripts
- Add to sync workflow
- Update documentation

### Scenario B: Only Audio Exists 🎵

**Audio:** Works
**Reminders:** Not found

**Action:**
- Create audio export script
- Search for reminders in chats
- Document audio access

### Scenario C: Only Reminders Exist 🔔

**Audio:** Not found
**Reminders:** Works

**Action:**
- Create reminders export script
- Audio may be in lifelogs
- Document reminders access

### Scenario D: Neither Exists ❌

**Both:** Not found

**Action:**
- Check if data is in chats/lifelogs
- Contact Limitless support
- Document limitations
- Wait for API updates

## 🛠️ Next Steps Based on Results

### If Audio Endpoint Works

Create these scripts:
1. `export_audio_files.py` - Download audio by date
2. `batch_export_audio.py` - Bulk download
3. Add to `sync_all_chats.py` workflow

Update archive structure:
```
exports/
  audio/
    2025-11/
      2025-11-20-recording-001.mp3
      2025-11-20-recording-002.mp3
```

### If Reminders Endpoint Works

Create these scripts:
1. `export_reminders.py` - Get all reminders
2. `analyze_reminders.py` - Pattern analysis
3. Add to sync workflow

Update archive structure:
```
exports/
  reminders/
    2025-11-reminders.json
    2025-11-reminders.md
```

### If Hidden in Chats

Update `analyze_chats.py` to:
- Detect reminder chats
- Separate from regular chats
- Extract reminder content

### If Not Available

Document findings:
- Which endpoints were tested
- Status codes received
- Alternative access methods
- Feature requests for Limitless

## 💡 Tips for Investigation

### 1. Save All Responses

Always use `--save` flag to preserve responses:
```bash
python explore_audio_endpoint.py --save audio_response.json
python explore_reminders_endpoint.py --save reminders_response.json
```

### 2. Check Status Codes

- **200** - Success! Data available
- **404** - Endpoint doesn't exist
- **403** - Exists but access denied
- **401** - Authentication issue (check API key)

### 3. Look for Patterns

Even if endpoints don't work, error messages may hint at:
- Correct endpoint paths
- Required parameters
- Access requirements

### 4. Cross-Reference

Compare with:
- Existing chats data
- Lifelog contents
- API documentation

### 5. Document Everything

Keep notes on:
- What you tried
- What worked/didn't work
- Error messages
- Interesting findings

## 📝 Reporting Results

After investigation, document:

1. **Endpoint Status**
   - Which endpoints exist
   - Status codes
   - Response structures

2. **Data Availability**
   - What data is accessible
   - Format and structure
   - Limitations

3. **Alternative Access**
   - If not in API, where is it?
   - Workarounds
   - Future possibilities

4. **Next Actions**
   - Scripts to create
   - Features to request
   - Documentation to update

## 🎯 Success Criteria

### Audio Investigation Success
- ✅ Confirmed endpoint exists (or doesn't)
- ✅ Understand data structure
- ✅ Know how to access audio files
- ✅ Have plan for integration

### Reminders Investigation Success
- ✅ Confirmed endpoint exists (or doesn't)
- ✅ Understand reminder format
- ✅ Know how to access reminders
- ✅ Have plan for archiving

## 🚀 Ready to Explore?

Run the exploration scripts and see what you discover!

```bash
# Test audio
python explore_audio_endpoint.py --save audio_test.json

# Test reminders
python explore_reminders_endpoint.py --save reminders_test.json
```

Then share the results and we can build the appropriate export/archive tools based on what's available! 🔍


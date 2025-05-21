import json
import os
import argparse
from datetime import datetime, date, timedelta, time # Added date, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates # For better time formatting on axes
import re # Added for date pattern matching

def get_boundary_date_from_files(directory: str, filename_pattern_str: str, find_latest: bool = True) -> date | None:
    """
    Scans a directory for files matching a regex pattern that captures a date (YYYY-MM-DD)
    and returns either the latest or earliest date found.

    Args:
        directory: The directory to scan.
        filename_pattern_str: Regex string that must contain one capturing group for the date string (e.g., r"(\d{4}-\d{2}-\d{2})-analytics\.md").
        find_latest: If True, finds the most recent (latest) date. If False, finds the oldest (earliest) date.

    Returns:
        A date object or None if no matching files are found or an error occurs.
    """
    boundary_date = None
    date_pattern = re.compile(filename_pattern_str)
    try:
        if not os.path.exists(directory):
            # print(f"Directory not found: {directory}")
            return None
        for filename in os.listdir(directory):
            match = date_pattern.fullmatch(filename)
            if match:
                date_str = match.group(1)
                try:
                    current_file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    if boundary_date is None:
                        boundary_date = current_file_date
                    elif find_latest and current_file_date > boundary_date:
                        boundary_date = current_file_date
                    elif not find_latest and current_file_date < boundary_date:
                        boundary_date = current_file_date
                except ValueError:
                    # print(f"Warning: Found file with invalid date format in name: {filename}")
                    continue
    except Exception as e:
        print(f"Error scanning directory {directory} with pattern {filename_pattern_str}: {e}")
        return None
    return boundary_date

def load_contents_data(filepath):
    if not os.path.exists(filepath):
        print(f"Error: Data file not found at {filepath}")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f) # Expects a list of lifelog objects
        print(f"[DEBUG load_contents_data] Successfully loaded JSON. Type: {type(data)}, Length (if list): {len(data) if isinstance(data, list) else 'N/A'}")
        if isinstance(data, list) and len(data) > 0:
            print(f"[DEBUG load_contents_data] First element type: {type(data[0])}")
            print(f"[DEBUG load_contents_data] First element keys (if dict): {data[0].keys() if isinstance(data[0], dict) else 'N/A'}")
        return data
    except Exception as e:
        print(f"Error loading or parsing JSON from {filepath}: {e}")
        return None

def extract_session_spans(lifelogs_data):
    print(f"[DEBUG extract_session_spans] Received lifelogs_data. Type: {type(lifelogs_data)}, Length (if list): {len(lifelogs_data) if isinstance(lifelogs_data, list) else 'N/A'}")
    session_spans = []
    if not isinstance(lifelogs_data, list):
        print("Error: Expected a list of lifelog objects.")
        return pd.DataFrame()

    for log_entry in lifelogs_data:
        log_id = log_entry.get('lifelog_id', 'N/A')
        # print(f"[DEBUG extract_session_spans] Processing log_entry. ID: {log_id}") # Can be too verbose
        contents = log_entry.get('contents')

        if not contents or not isinstance(contents, list) or len(contents) == 0:
            # print(f"[DEBUG extract_session_spans] Log ID {log_id}: No contents, not a list, or empty list.")
            continue

        timestamped_segments = [seg for seg in contents if isinstance(seg, dict) and 'startTime' in seg and seg.get('type') != 'heading1' and seg.get('type') != 'heading2' and seg.get('type') != 'heading3']

        # print(f"[DEBUG extract_session_spans] Log ID {log_id}: Found {len(timestamped_segments)} timestamped segments out of {len(contents)} total content items.")

        if not timestamped_segments:
            # print(f"[DEBUG extract_session_spans] Log ID {log_id}: No timestamped segments found (e.g., only headings).")
            continue

        first_segment_with_time = timestamped_segments[0]
        last_segment_with_time = timestamped_segments[-1]

        # print(f"[DEBUG extract_session_spans] Log ID {log_id}: First timed segment: {first_segment_with_time.get('startTime')}")
        # print(f"[DEBUG extract_session_spans] Log ID {log_id}: Last timed segment: {last_segment_with_time.get('startTime')}, endTime (if any): {last_segment_with_time.get('endTime')}")

        try:
            first_ts = pd.to_datetime(first_segment_with_time['startTime'])

            if 'endTime' in last_segment_with_time and last_segment_with_time['endTime']:
                last_ts_of_span = pd.to_datetime(last_segment_with_time['endTime'])
            else:
                last_ts_of_span = pd.to_datetime(last_segment_with_time['startTime'])

            if last_ts_of_span < first_ts:
                # print(f"[DEBUG extract_session_spans] Log ID {log_id}: last_ts_of_span ({last_ts_of_span}) < first_ts ({first_ts}). Adjusting.")
                if 'endTime' in first_segment_with_time and first_segment_with_time['endTime']:
                    potential_end = pd.to_datetime(first_segment_with_time['endTime'])
                    if potential_end >= first_ts:
                        last_ts_of_span = potential_end
                    else:
                        last_ts_of_span = first_ts + pd.Timedelta(seconds=1)
                else:
                     last_ts_of_span = first_ts + pd.Timedelta(seconds=1)
                # print(f"[DEBUG extract_session_spans] Log ID {log_id}: Adjusted last_ts_of_span to {last_ts_of_span}")

            session_spans.append({
                'first_timestamp': first_ts,
                'last_timestamp_of_span': last_ts_of_span
            })
            # print(f"[DEBUG extract_session_spans] Log ID {log_id}: Successfully extracted span: {first_ts} -> {last_ts_of_span}")
        except Exception as e:
            print(f"Warning: Could not parse timestamps for log entry ID {log_id}: {e}.")

    return pd.DataFrame(session_spans)

def plot_timeline(df, date_str, output_dir):
    if df.empty:
        print(f"Plotting: No data for {date_str}.")
        return None

    plt.figure(figsize=(18, 10))
    for i, row in df.iterrows():
        plt.plot([row['first_timestamp'], row['last_timestamp_of_span']], [i, i], linewidth=5, marker='|', markersize=10, label=f"Session {i+1}" if len(df) < 20 else None)

    plt.title(f'Recording Session Spans for {date_str}', fontsize=18, pad=20)
    plt.xlabel('Hour of Day', fontsize=15, labelpad=15)
    plt.ylabel('Recording Session Index', fontsize=15, labelpad=15)

    target_tz_for_formatter = None
    if not df.empty and hasattr(df['first_timestamp'].iloc[0], 'tzinfo') and df['first_timestamp'].iloc[0].tzinfo:
        target_tz_for_formatter = df['first_timestamp'].iloc[0].tzinfo

    if target_tz_for_formatter:
        formatter = mdates.DateFormatter('%H:%M', tz=target_tz_for_formatter)
    else:
        formatter = mdates.DateFormatter('%H:%M') # Fallback to default if no tz info in data
    plt.gca().xaxis.set_major_formatter(formatter)
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
    plt.gcf().autofmt_xdate(rotation=45)

    target_tz = None
    if not df.empty and hasattr(df['first_timestamp'].iloc[0], 'tzinfo') and df['first_timestamp'].iloc[0].tzinfo:
        target_tz = df['first_timestamp'].iloc[0].tzinfo

    day_start_naive = pd.to_datetime(date_str).replace(hour=0, minute=0, second=0, microsecond=0)

    if target_tz:
        try:
            day_start = day_start_naive.tz_localize(target_tz)
        except Exception as e:
            print(f"Warning: Could not localize day_start for {date_str} to {target_tz}. Using naive. Error: {e}")
            day_start = day_start_naive
    else:
        day_start = day_start_naive
        if not df.empty :
             print(f"Warning: Could not determine timezone for x-axis limits for {date_str}. Using naive timestamps for xlim.")

    day_end = day_start + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    plt.xlim(day_start, day_end)
    plt.grid(True, linestyle=':', alpha=0.6)

    if not df.empty:
        plt.ylim(-1, len(df))
        if len(df) <= 20 :
            plt.yticks(range(len(df)), [f"{j+1}" for j in range(len(df))])
        else:
            plt.yticks([])
    else:
        plt.yticks([])

    if 'duration' not in df.columns:
         df['duration'] = (df['last_timestamp_of_span'] - df['first_timestamp'])
    total_recording_time_seconds = df['duration'].sum().total_seconds()
    total_recording_time_hours = total_recording_time_seconds / 3600

    plt.figtext(0.5, 0.01,
                f"Total sessions: {len(df)} | Total recorded content span: {total_recording_time_hours:.2f} hours",
                ha="center", fontsize=14, bbox=dict(facecolor='aliceblue', alpha=0.7, pad=5))

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plot_filename_only = f"{date_str}-usage-timeline.png"
    plot_filepath = os.path.join(output_dir, plot_filename_only)
    try:
        plt.savefig(plot_filepath)
        print(f"Timeline plot for {date_str} saved to: {plot_filepath}")
    except Exception as e:
        print(f"Error saving plot for {date_str}: {e}")
        plt.close()
        return None
    plt.close()
    return plot_filename_only

def print_statistics(df, date_str):
    stats_lines = []
    if df.empty:
        no_data_message = f"Statistics: No recording sessions found for {date_str} to analyze."
        print(no_data_message)
        stats_lines.append(no_data_message)
        return stats_lines

    num_sessions = len(df)
    if 'duration' not in df.columns:
        df['duration'] = df['last_timestamp_of_span'] - df['first_timestamp']
    if 'duration_seconds' not in df.columns:
        df['duration_seconds'] = df['duration'].dt.total_seconds()
    if 'duration_minutes' not in df.columns:
        df['duration_minutes'] = df['duration_seconds'] / 60

    total_duration_seconds = df['duration_seconds'].sum()
    total_duration_hours = total_duration_seconds / 3600
    earliest_start_dt = df['first_timestamp'].min()
    latest_end_dt = df['last_timestamp_of_span'].max()

    stats_lines.append(f"--- Comprehensive Usage Analytics for {date_str} ---")
    stats_lines.append(f"Date Range of Recordings: {earliest_start_dt.strftime('%Y-%m-%d %H:%M:%S')} to {latest_end_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    active_day_span_seconds = (latest_end_dt - earliest_start_dt).total_seconds() if num_sessions > 0 else 0
    active_day_span_hours = active_day_span_seconds / 3600
    stats_lines.append(f"Active Recording Span (first to last session): {active_day_span_hours:.2f} hours")
    recording_ratio = (total_duration_seconds / active_day_span_seconds * 100) if active_day_span_seconds > 0 else 0
    stats_lines.append(f"Ratio of Recorded Time to Active Recording Span: {recording_ratio:.2f}%")
    stats_lines.append(f"Total Recorded Content Span: {total_duration_hours:.2f} hours ({total_duration_seconds/60:.2f} minutes)")
    stats_lines.append(f"Total number of recording sessions: {num_sessions}")

    if num_sessions > 0:
        stats_lines.append("Session Duration Statistics (minutes):")
        stats_lines.append(f"  - Mean (Average): {df['duration_minutes'].mean():.2f}")
        stats_lines.append(f"  - Median: {df['duration_minutes'].median():.2f}")
        stats_lines.append(f"  - Standard Deviation: {df['duration_minutes'].std():.2f}")
        stats_lines.append(f"  - Shortest Session: {df['duration_minutes'].min():.2f}")
        stats_lines.append(f"  - Longest Session: {df['duration_minutes'].max():.2f}")
        bins = [0, 1, 5, 15, 30, 60, float('inf')]
        labels = ['<1 min', '1-5 min', '5-15 min', '15-30 min', '30-60 min', '>60 min']
        df_copy = df.copy() # Ensure operations are on a copy
        df_copy['duration_bin'] = pd.cut(df_copy['duration_minutes'], bins=bins, labels=labels, right=False)
        stats_lines.append("Session Duration Distribution:")
        dist_str = df_copy['duration_bin'].value_counts().sort_index().to_string()
        stats_lines.append(dist_str)

    if num_sessions > 1:
        df_gaps_calc = df.sort_values(by='first_timestamp').copy()
        df_gaps_calc['gap_to_next_seconds'] = (df_gaps_calc['first_timestamp'].shift(-1) - df_gaps_calc['last_timestamp_of_span']).dt.total_seconds()
        df_gaps = df_gaps_calc[df_gaps_calc['gap_to_next_seconds'] >= 0] # Consider only positive gaps
        df_gaps_minutes = df_gaps['gap_to_next_seconds'] / 60
        stats_lines.append("Gap Between Sessions Statistics (minutes):")
        if not df_gaps_minutes.empty:
            stats_lines.append(f"  - Mean (Average): {df_gaps_minutes.mean():.2f}")
            stats_lines.append(f"  - Median: {df_gaps_minutes.median():.2f}")
            stats_lines.append(f"  - Standard Deviation: {df_gaps_minutes.std():.2f}")
            stats_lines.append(f"  - Shortest Gap: {df_gaps_minutes.min():.2f}")
            stats_lines.append(f"  - Longest Gap: {df_gaps_minutes.max():.2f}")
        else:
            stats_lines.append("  - No significant gaps between sessions found.")

    if num_sessions > 0:
        df_hour_calc = df.copy()
        df_hour_calc['hour_of_day'] = df_hour_calc['first_timestamp'].dt.hour
        hourly_duration = df_hour_calc.groupby('hour_of_day')['duration_seconds'].sum()
        if not hourly_duration.empty:
            busiest_hour_val = hourly_duration.idxmax()
            busiest_hour_duration_min = hourly_duration.max() / 60
            busiest_hour_str = f"{time(busiest_hour_val).strftime('%H:%M')} - {time((busiest_hour_val + 1) % 24).strftime('%H:%M')}"
            stats_lines.append(f"Busiest Hour (by total recording time): {busiest_hour_str} (with {busiest_hour_duration_min:.2f} minutes of recording)")
        stats_lines.append("Sessions Started Per Hour:")
        sessions_per_hour = df_hour_calc['hour_of_day'].value_counts().sort_index()
        for hour, count in sessions_per_hour.items():
            hour_str = f"{time(hour).strftime('%H:%M')} - {time((hour + 1) % 24).strftime('%H:%M')}"
            stats_lines.append(f"  - {hour_str}: {count} session(s)")
    stats_lines.append("---")
    for line in stats_lines:
        print(line)
    return stats_lines

def daterange(start_date_dt, end_date_dt):
    for n in range(int((end_date_dt - start_date_dt).days) + 1):
        yield start_date_dt + timedelta(n)

def process_single_day_analysis(date_str, base_dir, contents_subdir, analytics_subdir):
    print(f"--- Starting analysis for date: {date_str} ---")
    contents_file_path = os.path.join(base_dir, contents_subdir, f"{date_str}-contents.json")
    analytics_output_dir = os.path.join(base_dir, analytics_subdir)
    os.makedirs(analytics_output_dir, exist_ok=True)

    lifelogs_data = load_contents_data(contents_file_path)
    if lifelogs_data is None:
        print(f"No contents data found for {date_str}, or error loading. Skipping analysis.")
        return False

    session_spans_df = extract_session_spans(lifelogs_data)

    if session_spans_df.empty:
        print(f"No processable session spans extracted for {date_str}. This might mean no actual recording segments were found.")
        report_lines = [f"# Usage Analytics for {date_str}\\n", f"No recording session data found to analyze for {date_str}."]
        report_filepath = os.path.join(analytics_output_dir, f"{date_str}-analytics.md")
        try:
            with open(report_filepath, 'w', encoding='utf-8') as f:
                f.write("\n".join(report_lines))
            print(f"Minimal analytics report for {date_str} (no data) saved to: {report_filepath}")
        except Exception as e:
            print(f"Error saving minimal analytics report for {date_str}: {e}")
            return False
        return True

    if 'duration' not in session_spans_df.columns:
        session_spans_df['duration'] = (session_spans_df['last_timestamp_of_span'] - session_spans_df['first_timestamp'])
    if 'duration_seconds' not in session_spans_df.columns:
        session_spans_df['duration_seconds'] = session_spans_df['duration'].dt.total_seconds()
    if 'duration_minutes' not in session_spans_df.columns:
        session_spans_df['duration_minutes'] = session_spans_df['duration_seconds'] / 60

    plot_filename = plot_timeline(session_spans_df, date_str, analytics_output_dir)
    statistics_output_list = print_statistics(session_spans_df, date_str)

    markdown_lines = []
    markdown_lines.append(f"# Usage Analytics for {date_str}")
    markdown_lines.append("") # Blank line
    markdown_lines.append("## Statistics")
    markdown_lines.append("") # Blank line
    markdown_lines.append("```text")
    markdown_lines.extend(statistics_output_list)
    markdown_lines.append("```")

    if plot_filename:
        markdown_lines.append("") # Blank line
        markdown_lines.append("## Usage Timeline Plot")
        markdown_lines.append("") # Blank line
        markdown_lines.append(f"![Usage Timeline for {date_str}](./{plot_filename})")

    report_filepath = os.path.join(analytics_output_dir, f"{date_str}-analytics.md")
    final_markdown_string = "\n".join(markdown_lines) + "\n"

    try:
        with open(report_filepath, 'w', encoding='utf-8') as f:
            f.write(final_markdown_string)
        print(f"Full analytics report for {date_str} saved to: {report_filepath}")
    except Exception as e:
        print(f"Error saving full analytics report for {date_str}: {e}")
        return False

    print(f"Analysis for {date_str} completed successfully.")
    return True

def main():
    parser = argparse.ArgumentParser(description="Analyze daily usage from structured JSON lifelog data for a date or date range.")
    parser.add_argument("start_date_str", metavar="START_DATE", type=str, nargs='?', default=None,
                        help="Start date for analysis (YYYY-MM-DD). Defaults to smart range based on last processed analytics and available content.")
    parser.add_argument("end_date_str", metavar="END_DATE", type=str, nargs='?', default=None,
                        help="End date for analysis (YYYY-MM-DD). Defaults to START_DATE if START_DATE is provided, otherwise part of smart range or yesterday.")
    args = parser.parse_args()

    today = date.today()
    yesterday = today - timedelta(days=1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    base_exports_dir = os.path.join(project_root, "exports")
    contents_subdir_name = "contents"
    analytics_subdir_name = "analytics"

    analytics_dir_abs = os.path.join(base_exports_dir, analytics_subdir_name)
    os.makedirs(analytics_dir_abs, exist_ok=True)
    contents_dir_abs = os.path.join(base_exports_dir, contents_subdir_name)
    os.makedirs(contents_dir_abs, exist_ok=True)

    # Define filename patterns for boundary checks
    analytics_file_pattern = r"(\d{4}-\d{2}-\d{2})-analytics\.md"
    contents_file_pattern = r"(\d{4}-\d{2}-\d{2})-contents\.json"

    start_dt = None
    end_dt = None

    if args.start_date_str is None and args.end_date_str is None:
        print("No start or end date provided. Attempting to determine optimal date range...")

        last_analytics_dt = get_boundary_date_from_files(analytics_dir_abs, analytics_file_pattern, find_latest=True)
        earliest_contents_dt = get_boundary_date_from_files(contents_dir_abs, contents_file_pattern, find_latest=False)
        latest_contents_dt = get_boundary_date_from_files(contents_dir_abs, contents_file_pattern, find_latest=True)

        if last_analytics_dt:
            print(f"Last analytics report found for: {last_analytics_dt.strftime('%Y-%m-%d')}")
            start_dt = last_analytics_dt + timedelta(days=1)
        elif earliest_contents_dt:
            print(f"No analytics reports found. Starting from earliest available content: {earliest_contents_dt.strftime('%Y-%m-%d')}")
            start_dt = earliest_contents_dt
        else:
            print(f"No analytics reports or content files found. Defaulting to analyze yesterday ({yesterday.strftime('%Y-%m-%d')}), if content becomes available.")
            start_dt = yesterday

        # Determine end date: should not be later than yesterday, and not later than latest available content.
        potential_end_dt = yesterday
        if latest_contents_dt:
            print(f"Latest content file found for: {latest_contents_dt.strftime('%Y-%m-%d')}")
            if latest_contents_dt < potential_end_dt:
                potential_end_dt = latest_contents_dt
                print(f"Adjusting potential end date to latest content date: {potential_end_dt.strftime('%Y-%m-%d')}")
        else: # No content files at all
             print("No content files found. Cannot determine an end date for processing range based on content.")
             # If start_dt was also set to yesterday due to no analytics/content, this leads to a single day attempt.
             # If start_dt was set from analytics and there's no content, this might lead to start > end.
             if start_dt > potential_end_dt : # e.g. last analytics yesterday, no content at all
                 print(f"No content available to process from calculated start date {start_dt.strftime('%Y-%m-%d')}. Nothing to do.")
                 return


        end_dt = potential_end_dt

        if not start_dt: # Should only happen if no analytics, no content, and yesterday logic somehow failed (defensive)
            print("Could not determine a start date. Defaulting to yesterday.")
            start_dt = yesterday
            if not end_dt: # If end_dt also not set
                end_dt = yesterday


        if start_dt > end_dt:
            print(f"Calculated start date {start_dt.strftime('%Y-%m-%d')} is after end date {end_dt.strftime('%Y-%m-%d')}. All available data seems analyzed.")
            return

    elif args.start_date_str and args.end_date_str is None: # Start provided, end is same as start
        try:
            start_dt = datetime.strptime(args.start_date_str, "%Y-%m-%d").date()
            end_dt = start_dt
            print(f"Start date provided ({start_dt.strftime('%Y-%m-%d')}), end date defaults to start date.")
        except ValueError:
            print(f"Error: Invalid start_date format ('{args.start_date_str}'). Please use YYYY-MM-DD.")
            return
    elif args.start_date_str is None and args.end_date_str: # End provided, start defaults to yesterday (or could be an error/clarify)
        # This specific combination is a bit ambiguous without a start.
        # Current argparse setup defaults start_date_str to None, so this path implies only end_date_str was given.
        # For consistency with other scripts, let's default start to yesterday if only end is given.
        start_dt = yesterday
        try:
            end_dt = datetime.strptime(args.end_date_str, "%Y-%m-%d").date()
            print(f"End date provided ({end_dt.strftime('%Y-%m-%d')}), start date defaults to yesterday ({start_dt.strftime('%Y-%m-%d')}).")
        except ValueError:
            print(f"Error: Invalid end_date format ('{args.end_date_str}'). Please use YYYY-MM-DD.")
            return
    else: # Both start and end date are provided by user
        try:
            start_dt = datetime.strptime(args.start_date_str, "%Y-%m-%d").date()
            end_dt = datetime.strptime(args.end_date_str, "%Y-%m-%d").date()
            print(f"User provided start date: {start_dt.strftime('%Y-%m-%d')} and end date: {end_dt.strftime('%Y-%m-%d')}")
        except ValueError:
            print(f"Error: Invalid date format for start_date ('{args.start_date_str}') or end_date ('{args.end_date_str}'). Please use YYYY-MM-DD.")
            return

    if start_dt > end_dt:
        print(f"Error: Final calculated start date ({start_dt.strftime('%Y-%m-%d')}) is after end date ({end_dt.strftime('%Y-%m-%d')}). Cannot analyze.")
        return

    print(f"Starting analysis for date range: {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")

    successful_days = 0
    failed_days = 0
    days_with_no_data_to_analyze = 0 # Renamed for clarity
    days_skipped_missing_content = 0

    for single_date_dt in daterange(start_dt, end_dt):
        date_str_loop = single_date_dt.strftime("%Y-%m-%d")

        contents_file_to_check = os.path.join(contents_dir_abs, f"{date_str_loop}-contents.json")
        if not os.path.exists(contents_file_to_check):
            print(f"Prerequisite contents file '{contents_file_to_check}' not found for {date_str_loop}. Skipping analysis for this day.")
            days_skipped_missing_content +=1
            continue

        # process_single_day_analysis now handles its own file loading and empty data checks
        # It returns True if it successfully created a report (even a minimal one for no data)
        # and False if there was an error during processing (e.g., cannot write report).

        # To check if it was a "no data" scenario vs "data analyzed":
        # We need to know if the function returned True because it made a *minimal* report
        # or a *full* one. The current return of process_single_day_analysis doesn't distinguish.
        # Let's refine process_single_day_analysis to return a status or make the check here.
        # For now, we'll assume if process_single_day_analysis returns True, it's "successful"
        # and the distinction of "no data" vs "data" is logged by that function.

        if process_single_day_analysis(date_str_loop, base_exports_dir, contents_subdir_name, analytics_subdir_name):
            successful_days += 1
            # To correctly count days_with_no_data_to_analyze, we'd need more info from process_single_day_analysis
            # or re-evaluate here. For now, this counter might not be accurate based on new structure.
            # The function `process_single_day_analysis` already prints if no spans were extracted.
            # We can add a specific check here if needed:
            temp_contents_data = load_contents_data(contents_file_to_check)
            if temp_contents_data:
                temp_spans = extract_session_spans(temp_contents_data)
                if temp_spans.empty:
                    days_with_no_data_to_analyze +=1 # Increment if processed successfully but had no actual spans.
        else:
            failed_days += 1

    print("\n--- Analysis batch finished ---")
    print(f"Days processed successfully (analytics report generated): {successful_days}")
    if days_with_no_data_to_analyze > 0 and successful_days > 0 : # only relevant if some days were successful
         print(f"  (Out of these, {days_with_no_data_to_analyze} days had content but no actual recording spans to analyze in depth, resulting in a minimal report.)")
    if days_skipped_missing_content > 0:
        print(f"Days skipped due to missing prerequisite content files: {days_skipped_missing_content}")
    if failed_days > 0:
        print(f"Days where analysis processing failed (error during report generation): {failed_days}")

    if successful_days == 0 and days_skipped_missing_content == 0 and failed_days == 0:
        print("No days in the specified range required processing or were available for processing.")


if __name__ == "__main__":
    main()
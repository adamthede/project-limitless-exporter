import json
import os
import argparse
from datetime import datetime, date, timedelta, time # Added date, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates # For better time formatting on axes

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

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
    plt.gcf().autofmt_xdate(rotation=45)

    day_start = pd.to_datetime(date_str).replace(hour=0, minute=0, second=0, microsecond=0)
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
        stats_lines.append("\nSession Duration Statistics (minutes):")
        stats_lines.append(f"  - Mean (Average): {df['duration_minutes'].mean():.2f}")
        stats_lines.append(f"  - Median: {df['duration_minutes'].median():.2f}")
        stats_lines.append(f"  - Standard Deviation: {df['duration_minutes'].std():.2f}")
        stats_lines.append(f"  - Shortest Session: {df['duration_minutes'].min():.2f}")
        stats_lines.append(f"  - Longest Session: {df['duration_minutes'].max():.2f}")

        bins = [0, 1, 5, 15, 30, 60, float('inf')]
        labels = ['<1 min', '1-5 min', '5-15 min', '15-30 min', '30-60 min', '>60 min']
        df_copy = df.copy()
        df_copy['duration_bin'] = pd.cut(df_copy['duration_minutes'], bins=bins, labels=labels, right=False)
        stats_lines.append("\nSession Duration Distribution:")
        dist_str = df_copy['duration_bin'].value_counts().sort_index().to_string()
        stats_lines.append(dist_str)

    if num_sessions > 1:
        df_gaps_calc = df.sort_values(by='first_timestamp').copy()
        df_gaps_calc['gap_to_next_seconds'] = (df_gaps_calc['first_timestamp'].shift(-1) - df_gaps_calc['last_timestamp_of_span']).dt.total_seconds()
        df_gaps = df_gaps_calc[df_gaps_calc['gap_to_next_seconds'] >= 0]
        df_gaps_minutes = df_gaps['gap_to_next_seconds'] / 60

        stats_lines.append("\nGap Between Sessions Statistics (minutes):")
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
            stats_lines.append(f"\nBusiest Hour (by total recording time): {busiest_hour_str} (with {busiest_hour_duration_min:.2f} minutes of recording)")

        stats_lines.append("\nSessions Started Per Hour:")
        sessions_per_hour = df_hour_calc['hour_of_day'].value_counts().sort_index()
        for hour, count in sessions_per_hour.items():
            hour_str = f"{time(hour).strftime('%H:%M')} - {time((hour + 1) % 24).strftime('%H:%M')}"
            stats_lines.append(f"  - {hour_str}: {count} session(s)")
    stats_lines.append("\n---")

    for line in stats_lines:
        print(line)

    return stats_lines

def daterange(start_date_dt, end_date_dt):
    for n in range(int((end_date_dt - start_date_dt).days) + 1):
        yield start_date_dt + timedelta(n)

def main():
    parser = argparse.ArgumentParser(description="Analyze daily lifelog usage from local contents.json files for a date range and generate markdown reports.")
    parser.add_argument("start_date", type=str, nargs='?', default=None, help="Start date to analyze, in YYYY-MM-DD format. Defaults to yesterday if not provided.")
    parser.add_argument("end_date", type=str, nargs='?', default=None, help="Optional end date to analyze, in YYYY-MM-DD format. If not provided and start_date is also not provided, defaults to yesterday; otherwise defaults to start_date.")

    args = parser.parse_args()

    today = date.today()
    yesterday = today - timedelta(days=1)

    start_date_dt = None
    end_date_dt = None

    if args.start_date is None:
        start_date_dt = yesterday
        # If start_date defaults to yesterday, and end_date is not given, end_date also defaults to yesterday
        if args.end_date is None:
            end_date_dt = yesterday
        else: # end_date is given
            try:
                end_date_dt = datetime.strptime(args.end_date, "%Y-%m-%d").date()
            except ValueError:
                print(f"Error: Invalid end_date format ({args.end_date}). Please use YYYY-MM-DD.")
                return
    else: # start_date is provided
        try:
            start_date_dt = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid start_date format ({args.start_date}). Please use YYYY-MM-DD.")
            return

        if args.end_date is None: # end_date not provided, so defaults to start_date
            end_date_dt = start_date_dt
        else: # end_date is provided
            try:
                end_date_dt = datetime.strptime(args.end_date, "%Y-%m-%d").date()
            except ValueError:
                print(f"Error: Invalid end_date format ({args.end_date}). Please use YYYY-MM-DD.")
                return

    if end_date_dt < start_date_dt:
        print("Error: End date cannot be before start date.")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    analytics_output_dir = os.path.join(project_root, "exports", "analytics")
    os.makedirs(analytics_output_dir, exist_ok=True)

    processed_dates = []
    failed_dates = []

    print(f"Starting usage analysis for date range: {start_date_dt.strftime('%Y-%m-%d')} to {end_date_dt.strftime('%Y-%m-%d')}")

    for current_date_dt in daterange(start_date_dt, end_date_dt):
        target_date_str = current_date_dt.strftime("%Y-%m-%d")
        print(f"\n--- Processing analytics for date: {target_date_str} ---")

        contents_file_path = os.path.join(project_root, "exports", "contents", f"{target_date_str}-contents.json")

        lifelogs_data = load_contents_data(contents_file_path)
        if not lifelogs_data:
            print(f"No data loaded for {target_date_str}. Skipping analytics for this date.")
            failed_dates.append(target_date_str)
            continue

        df_sessions = extract_session_spans(lifelogs_data)

        if not df_sessions.empty:
            df_sessions = df_sessions.sort_values(by='first_timestamp').reset_index(drop=True)

            df_sessions['duration'] = df_sessions['last_timestamp_of_span'] - df_sessions['first_timestamp']
            df_sessions['duration_seconds'] = df_sessions['duration'].dt.total_seconds()
            df_sessions['duration_minutes'] = df_sessions['duration_seconds'] / 60

            png_filename_only = plot_timeline(df_sessions, target_date_str, analytics_output_dir)
            stats_output_lines = print_statistics(df_sessions, target_date_str)

            if png_filename_only and stats_output_lines:
                md_filename = f"{target_date_str}-analytics.md"
                md_filepath = os.path.join(analytics_output_dir, md_filename)

                full_stats_string = "\n".join(stats_output_lines)
                markdown_content = f"# Usage Analytics for {target_date_str}\n\n"
                markdown_content += "## Statistics\n\n"
                markdown_content += f"```text\n{full_stats_string}\n```\n"
                markdown_content += "\n## Timeline Chart\n\n"
                markdown_content += f"![Usage Timeline](./{png_filename_only})\n"

                try:
                    with open(md_filepath, 'w', encoding='utf-8') as md_file:
                        md_file.write(markdown_content)
                    print(f"Analytics markdown report for {target_date_str} saved to: {md_filepath}")
                    processed_dates.append(target_date_str)
                except IOError as e:
                    print(f"Error writing markdown report for {target_date_str} to {md_filepath}: {e}")
                    failed_dates.append(target_date_str)
            elif not png_filename_only and not stats_output_lines:
                 print(f"Skipping markdown report for {target_date_str} as no data was available to plot or gather stats.")
                 # If stats_output_lines contained the "No data" message, it would have been printed by print_statistics
                 # If df_sessions was empty, it means no data to process, effectively a failure to produce a report.
                 failed_dates.append(target_date_str)
            elif not png_filename_only:
                print(f"Skipping markdown report for {target_date_str} as timeline plot was not created.")
                failed_dates.append(target_date_str)
            else: # not stats_output_lines (should not happen if df_sessions is not empty)
                print(f"Skipping markdown report for {target_date_str} as no statistics were generated.")
                failed_dates.append(target_date_str)

        else:
            print_statistics(df_sessions, target_date_str) # Prints "No recording sessions..."
            print(f"No valid session spans extracted for {target_date_str}. No analytics report generated.")
            failed_dates.append(target_date_str)

    print("\n--- Batch Analysis Summary ---")
    if processed_dates:
        print("Successfully generated analytics reports for:")
        for pd_date in processed_dates:
            print(f"  - {pd_date}")
    if failed_dates:
        print("Failed to generate analytics reports for (or no data found for):")
        for fd_date in failed_dates:
            print(f"  - {fd_date}")
    if not processed_dates and not failed_dates:
        print("No dates were processed in the given range.")

if __name__ == "__main__":
    main()
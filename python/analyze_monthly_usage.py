import json
import os
import argparse
from datetime import datetime, date, timedelta, time
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import calendar
import numpy as np

# --- Data Loading & Initial Processing (Adapted from analyze_daily_usage.py) ---

def load_contents_data(filepath):
    if not os.path.exists(filepath):
        # print(f"Info: Data file not found at {filepath}") # Less verbose for batch processing
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading or parsing JSON from {filepath}: {e}")
        return None

def extract_session_spans(lifelogs_data, log_date_str):
    session_spans = []
    if not isinstance(lifelogs_data, list):
        print(f"Error for {log_date_str}: Expected a list of lifelog objects.")
        return pd.DataFrame()

    for log_entry in lifelogs_data:
        log_id = log_entry.get('lifelog_id', 'N/A')
        contents = log_entry.get('contents')

        if not contents or not isinstance(contents, list) or len(contents) == 0:
            continue

        timestamped_segments = [seg for seg in contents if isinstance(seg, dict) and 'startTime' in seg and seg.get('type') != 'heading1' and seg.get('type') != 'heading2' and seg.get('type') != 'heading3']

        if not timestamped_segments:
            continue

        first_segment_with_time = timestamped_segments[0]
        last_segment_with_time = timestamped_segments[-1]

        try:
            first_ts = pd.to_datetime(first_segment_with_time['startTime'])
            if 'endTime' in last_segment_with_time and last_segment_with_time['endTime']:
                last_ts_of_span = pd.to_datetime(last_segment_with_time['endTime'])
            else:
                last_ts_of_span = pd.to_datetime(last_segment_with_time['startTime'])

            if last_ts_of_span < first_ts:
                if 'endTime' in first_segment_with_time and first_segment_with_time['endTime']:
                    potential_end = pd.to_datetime(first_segment_with_time['endTime'])
                    if potential_end >= first_ts:
                        last_ts_of_span = potential_end
                    else:
                        last_ts_of_span = first_ts + pd.Timedelta(seconds=1)
                else:
                     last_ts_of_span = first_ts + pd.Timedelta(seconds=1)

            session_spans.append({
                'first_timestamp': first_ts,
                'last_timestamp_of_span': last_ts_of_span
            })
        except Exception as e:
            print(f"Warning for {log_date_str} (log ID {log_id}): Could not parse timestamps: {e}.")

    return pd.DataFrame(session_spans)

# --- Monthly Plotting Functions ---

def plot_daily_trends(daily_summary_df, month_year_str, output_dir):
    if daily_summary_df.empty:
        print(f"Plotting: No daily summary data for {month_year_str} to plot trends.")
        return None

    fig, ax1 = plt.subplots(figsize=(18, 10))

    # Plot Total Duration
    color = 'tab:blue'
    ax1.set_xlabel('Date', fontsize=15, labelpad=15)
    ax1.set_ylabel('Total Recorded Hours', color=color, fontsize=15, labelpad=15)
    ax1.plot(daily_summary_df['date'], daily_summary_df['total_duration_hours'], color=color, marker='o', linestyle='-')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d')) # More specific date format
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right")


    # Plot Session Count on a second y-axis
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Number of Sessions', color=color, fontsize=15, labelpad=15)
    ax2.plot(daily_summary_df['date'], daily_summary_df['session_count'], color=color, marker='x', linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color)

    fig.tight_layout(rect=[0, 0.05, 1, 0.93]) # Adjust layout to prevent overlap
    plt.title(f'Daily Recording Trends for {month_year_str}', fontsize=18, pad=20)
    plt.grid(True, linestyle=':', alpha=0.7)

    plot_filename_only = f"{month_year_str}-daily-trends.png"
    plot_filepath = os.path.join(output_dir, plot_filename_only)
    try:
        plt.savefig(plot_filepath)
        print(f"Daily trends plot for {month_year_str} saved to: {plot_filepath}")
    except Exception as e:
        print(f"Error saving daily trends plot for {month_year_str}: {e}")
        plt.close()
        return None
    plt.close()
    return plot_filename_only


def plot_session_duration_histogram(all_sessions_combined_df, month_year_str, output_dir):
    if all_sessions_combined_df.empty or 'duration_minutes' not in all_sessions_combined_df:
        print(f"Plotting: No session duration data for {month_year_str} to plot histogram.")
        return None

    plt.figure(figsize=(12, 7))
    plt.hist(all_sessions_combined_df['duration_minutes'], bins=20, color='skyblue', edgecolor='black')
    plt.title(f'Distribution of Session Durations for {month_year_str}', fontsize=16, pad=15)
    plt.xlabel('Session Duration (minutes)', fontsize=12, labelpad=10)
    plt.ylabel('Number of Sessions', fontsize=12, labelpad=10)
    plt.grid(axis='y', alpha=0.75)
    plt.tight_layout()

    plot_filename_only = f"{month_year_str}-session-durations-histogram.png"
    plot_filepath = os.path.join(output_dir, plot_filename_only)
    try:
        plt.savefig(plot_filepath)
        print(f"Session duration histogram for {month_year_str} saved to: {plot_filepath}")
    except Exception as e:
        print(f"Error saving session duration histogram for {month_year_str}: {e}")
        plt.close()
        return None
    plt.close()
    return plot_filename_only

def plot_hourly_activity_barchart(all_sessions_combined_df, month_year_str, output_dir):
    if all_sessions_combined_df.empty or 'hour_of_day' not in all_sessions_combined_df:
        print(f"Plotting: No hourly activity data for {month_year_str} to plot barchart.")
        return None

    hourly_total_duration_hours = all_sessions_combined_df.groupby('hour_of_day')['duration_seconds'].sum() / 3600
    hourly_total_duration_hours = hourly_total_duration_hours.reindex(range(24), fill_value=0) # Ensure all hours are present

    plt.figure(figsize=(15, 8))
    hourly_total_duration_hours.plot(kind='bar', color='lightcoral', edgecolor='black')
    plt.title(f'Total Recording Duration per Hour for {month_year_str}', fontsize=16, pad=15)
    plt.xlabel('Hour of Day (00:00 - 23:00)', fontsize=12, labelpad=10)
    plt.ylabel('Total Recorded Hours', fontsize=12, labelpad=10)
    plt.xticks(ticks=range(24), labels=[f"{h:02d}:00" for h in range(24)], rotation=45, ha="right")
    plt.grid(axis='y', alpha=0.75)
    plt.tight_layout()

    plot_filename_only = f"{month_year_str}-hourly-activity.png"
    plot_filepath = os.path.join(output_dir, plot_filename_only)
    try:
        plt.savefig(plot_filepath)
        print(f"Hourly activity barchart for {month_year_str} saved to: {plot_filepath}")
    except Exception as e:
        print(f"Error saving hourly activity barchart for {month_year_str}: {e}")
        plt.close()
        return None
    plt.close()
    return plot_filename_only

# --- Main Analysis and Reporting ---

def generate_monthly_stats_text(month_year_str, daily_summary_df, all_sessions_combined_df, days_with_data, total_days_in_month):
    stats_lines = []
    stats_lines.append(f"--- Comprehensive Monthly Usage Analytics for {month_year_str} ---")
    stats_lines.append(f"Data processed for {days_with_data} out of {total_days_in_month} days in the month.")

    if daily_summary_df.empty or all_sessions_combined_df.empty:
        stats_lines.append("\nNo recording data found for this month.")
        return "\n".join(stats_lines)

    # Overall Monthly Stats
    total_recorded_hours_month = daily_summary_df['total_duration_hours'].sum()
    avg_daily_recorded_hours = daily_summary_df['total_duration_hours'].mean()
    std_daily_recorded_hours = daily_summary_df['total_duration_hours'].std()
    total_sessions_month = daily_summary_df['session_count'].sum()
    avg_daily_sessions = daily_summary_df['session_count'].mean()

    stats_lines.append("\nOverall Monthly Recording Summary:")
    stats_lines.append(f"  - Total Recorded Hours: {total_recorded_hours_month:.2f} hours")
    stats_lines.append(f"  - Average Daily Recorded Hours: {avg_daily_recorded_hours:.2f} hours/day (Std Dev: {std_daily_recorded_hours:.2f})")
    stats_lines.append(f"  - Total Recording Sessions: {int(total_sessions_month)} sessions")
    stats_lines.append(f"  - Average Daily Sessions: {avg_daily_sessions:.2f} sessions/day")

    # Session Duration Statistics (Month-wide)
    if 'duration_minutes' in all_sessions_combined_df and not all_sessions_combined_df['duration_minutes'].empty:
        stats_lines.append("\nSession Duration Statistics (all sessions in month, minutes):")
        stats_lines.append(f"  - Mean (Average): {all_sessions_combined_df['duration_minutes'].mean():.2f}")
        stats_lines.append(f"  - Median: {all_sessions_combined_df['duration_minutes'].median():.2f}")
        stats_lines.append(f"  - Standard Deviation: {all_sessions_combined_df['duration_minutes'].std():.2f}")
        stats_lines.append(f"  - Shortest Session: {all_sessions_combined_df['duration_minutes'].min():.2f}")
        stats_lines.append(f"  - Longest Session: {all_sessions_combined_df['duration_minutes'].max():.2f}")

        bins = [0, 1, 5, 15, 30, 60, float('inf')]
        labels = ['<1 min', '1-5 min', '5-15 min', '15-30 min', '30-60 min', '>60 min']
        # Ensure 'duration_minutes' is present before using it for cut
        if 'duration_minutes' in all_sessions_combined_df.columns:
            duration_bin_counts = pd.cut(all_sessions_combined_df['duration_minutes'], bins=bins, labels=labels, right=False).value_counts().sort_index()
            stats_lines.append("  - Session Duration Distribution:")
            for label, count in duration_bin_counts.items():
                stats_lines.append(f"    - {label}: {count}")


    # Hourly Activity (Month-wide)
    if 'hour_of_day' in all_sessions_combined_df and not all_sessions_combined_df.empty:
        hourly_total_duration_seconds = all_sessions_combined_df.groupby('hour_of_day')['duration_seconds'].sum()
        if not hourly_total_duration_seconds.empty:
            busiest_hour_val = hourly_total_duration_seconds.idxmax()
            busiest_hour_duration_min = hourly_total_duration_seconds.max() / 60
            busiest_hour_str = f"{time(busiest_hour_val).strftime('%H:00')} - {time((busiest_hour_val + 1) % 24).strftime('%H:00')}" # Simpler format for month
            stats_lines.append(f"\nBusiest Hour (by total recording time across month): {busiest_hour_str} (with {busiest_hour_duration_min:.2f} total minutes of recording)")

        sessions_per_hour_month = all_sessions_combined_df['hour_of_day'].value_counts().sort_index()
        stats_lines.append("\nTotal Sessions Started Per Hour (across month):")
        for hour, count in sessions_per_hour_month.items():
            hour_str = f"{time(hour).strftime('%H:00')} - {time((hour + 1) % 24).strftime('%H:00')}"
            stats_lines.append(f"  - {hour_str}: {count} session(s)")

    # Day-level Extremes
    if not daily_summary_df.empty:
        day_max_hours = daily_summary_df.loc[daily_summary_df['total_duration_hours'].idxmax()]
        day_min_hours = daily_summary_df.loc[daily_summary_df['total_duration_hours'].idxmin()] # Only if days_with_data > 0
        stats_lines.append("\nDaily Recording Extremes:")
        stats_lines.append(f"  - Day with Most Recorded Time: {day_max_hours['date'].strftime('%Y-%m-%d')} ({day_max_hours['total_duration_hours']:.2f} hours from {int(day_max_hours['session_count'])} sessions)")
        if days_with_data > 0: # Ensure there's data before finding min
             stats_lines.append(f"  - Day with Least Recorded Time (among days with data): {day_min_hours['date'].strftime('%Y-%m-%d')} ({day_min_hours['total_duration_hours']:.2f} hours from {int(day_min_hours['session_count'])} sessions)")

    stats_lines.append("\n---")
    return "\n".join(stats_lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze monthly lifelog usage from local contents.json files and generate a markdown report.")
    parser.add_argument("year_month", type=str, help="Month to analyze, in YYYY-MM format.")
    args = parser.parse_args()

    try:
        year, month = map(int, args.year_month.split('-'))
        if not (1 <= month <= 12):
            raise ValueError("Month must be between 01 and 12.")
        # Validate year if necessary, e.g., within a reasonable range
        if not (2000 <= year <= datetime.now().year + 5) : # Example range
             raise ValueError(f"Year {year} seems out of a typical range.")
        month_year_str = f"{year:04d}-{month:02d}"
        start_date_month = date(year, month, 1)
        _, num_days_in_month = calendar.monthrange(year, month)
    except ValueError as e:
        print(f"Error: Invalid year_month format or value. Please use YYYY-MM. Details: {e}")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    monthly_analytics_base_dir = os.path.join(project_root, "exports", "analytics", "monthly")
    # Specific output directory for this month's plots
    monthly_plots_output_dir = os.path.join(monthly_analytics_base_dir, f"{month_year_str}_plots")
    os.makedirs(monthly_plots_output_dir, exist_ok=True) # For plots

    daily_metrics_list = []
    all_sessions_dfs = []
    days_with_data_count = 0
    processed_dates_for_log = []


    print(f"Starting monthly usage analysis for: {month_year_str}")
    print(f"Plots will be saved in: {monthly_plots_output_dir}")
    print(f"Report will be saved in: {monthly_analytics_base_dir}")


    for day_num in range(num_days_in_month):
        current_date_dt = start_date_month + timedelta(days=day_num)
        target_date_str = current_date_dt.strftime("%Y-%m-%d")
        # print(f"Processing data for {target_date_str}...")

        contents_file_path = os.path.join(project_root, "exports", "contents", f"{target_date_str}-contents.json")
        lifelogs_data = load_contents_data(contents_file_path)

        if lifelogs_data:
            df_day_sessions = extract_session_spans(lifelogs_data, target_date_str)
            if not df_day_sessions.empty:
                days_with_data_count += 1
                processed_dates_for_log.append(target_date_str)

                df_day_sessions = df_day_sessions.sort_values(by='first_timestamp').reset_index(drop=True)
                df_day_sessions['duration'] = df_day_sessions['last_timestamp_of_span'] - df_day_sessions['first_timestamp']
                df_day_sessions['duration_seconds'] = df_day_sessions['duration'].dt.total_seconds()
                df_day_sessions['duration_minutes'] = df_day_sessions['duration_seconds'] / 60
                df_day_sessions['hour_of_day'] = df_day_sessions['first_timestamp'].dt.hour # For hourly aggregation

                total_duration_seconds_day = df_day_sessions['duration_seconds'].sum()
                session_count_day = len(df_day_sessions)

                daily_metrics_list.append({
                    'date': current_date_dt, # Store as datetime.date for easier plotting
                    'total_duration_hours': total_duration_seconds_day / 3600,
                    'session_count': session_count_day
                })
                all_sessions_dfs.append(df_day_sessions)
            # else:
                # print(f"No valid session spans extracted for {target_date_str}.")
        # else:
            # print(f"No contents file found for {target_date_str}.")

    if not daily_metrics_list:
        print(f"\nNo data found for any day in {month_year_str}. Cannot generate monthly report.")
        # Create a minimal report indicating no data?
        md_filename = f"{month_year_str}-analytics.md"
        md_filepath = os.path.join(monthly_analytics_base_dir, md_filename)
        markdown_content = f"# Monthly Usage Analytics for {month_year_str}\n\n"
        markdown_content += f"No recording data found for {month_year_str} (checked {num_days_in_month} days).\n"
        markdown_content += "Please ensure `exports/contents/YYYY-MM-DD-contents.json` files exist for this period."
        try:
            with open(md_filepath, 'w', encoding='utf-8') as md_file:
                md_file.write(markdown_content)
            print(f"Minimal monthly report for {month_year_str} (no data) saved to: {md_filepath}")
        except IOError as e:
            print(f"Error writing minimal markdown report for {month_year_str} to {md_filepath}: {e}")
        return

    print(f"\nProcessed data for {days_with_data_count} out of {num_days_in_month} days in {month_year_str}.")
    if days_with_data_count > 0:
        print(f"Days with data: {', '.join(processed_dates_for_log)}")


    daily_summary_df = pd.DataFrame(daily_metrics_list)
    all_sessions_combined_df = pd.concat(all_sessions_dfs, ignore_index=True) if all_sessions_dfs else pd.DataFrame()


    # Generate Plots
    plot_paths = {}
    plot_paths['daily_trends'] = plot_daily_trends(daily_summary_df, month_year_str, monthly_plots_output_dir)
    if not all_sessions_combined_df.empty:
        plot_paths['session_duration_histogram'] = plot_session_duration_histogram(all_sessions_combined_df, month_year_str, monthly_plots_output_dir)
        plot_paths['hourly_activity'] = plot_hourly_activity_barchart(all_sessions_combined_df, month_year_str, monthly_plots_output_dir)
    else: # Handle cases where all_sessions_combined_df might be empty even if daily_summary_df is not (e.g. all sessions were empty)
        print("Warning: Combined session data is empty, skipping session-specific plots.")
        plot_paths['session_duration_histogram'] = None
        plot_paths['hourly_activity'] = None


    # Generate Statistics Text
    stats_text = generate_monthly_stats_text(month_year_str, daily_summary_df, all_sessions_combined_df, days_with_data_count, num_days_in_month)
    print("\n--- Monthly Statistics Summary ---")
    print(stats_text)
    print("---------------------------------")


    # Generate Markdown Report
    md_filename = f"{month_year_str}-analytics.md"
    md_filepath = os.path.join(monthly_analytics_base_dir, md_filename)

    markdown_content = f"# Monthly Usage Analytics for {month_year_str}\n\n"
    markdown_content += f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    markdown_content += "## Summary Statistics\n\n"
    markdown_content += f"```text\n{stats_text}\n```\n"

    markdown_content += "\n## Visualizations\n\n"
    if plot_paths.get('daily_trends'):
        # Relative path from monthly_analytics_base_dir to monthly_plots_output_dir/plot_filename
        relative_plot_path = os.path.join(f"{month_year_str}_plots", plot_paths['daily_trends'])
        markdown_content += f"### Daily Recording Trends\n\n![Daily Trends](./{relative_plot_path})\n\n"
    if plot_paths.get('session_duration_histogram'):
        relative_plot_path = os.path.join(f"{month_year_str}_plots", plot_paths['session_duration_histogram'])
        markdown_content += f"### Session Duration Distribution (Month-wide)\n\n![Session Durations](./{relative_plot_path})\n\n"
    if plot_paths.get('hourly_activity'):
        relative_plot_path = os.path.join(f"{month_year_str}_plots", plot_paths['hourly_activity'])
        markdown_content += f"### Hourly Recording Activity (Month-wide)\n\n![Hourly Activity](./{relative_plot_path})\n\n"

    if not any(plot_paths.values()):
        markdown_content += "No visualizations could be generated for this month.\n"

    try:
        with open(md_filepath, 'w', encoding='utf-8') as md_file:
            md_file.write(markdown_content)
        print(f"Monthly analytics markdown report for {month_year_str} saved to: {md_filepath}")
    except IOError as e:
        print(f"Error writing monthly markdown report for {month_year_str} to {md_filepath}: {e}")

    print(f"\nAnalysis for {month_year_str} complete.")

if __name__ == "__main__":
    main()
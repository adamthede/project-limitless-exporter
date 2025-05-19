import os
import argparse
import json
import re
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def summarize_daily_markdown(daily_markdown_content: str, should_stream: bool = True):
    """Summarizes a string of concatenated daily markdown content."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    if not daily_markdown_content or not daily_markdown_content.strip():
        print("No content provided to summarize from the input file.")
        return ""

    response = client.chat.completions.create(
        model="gpt-4.1-mini", # Ensure this model is available to your key
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes daily lifelogs into a markdown journal entry."},
            {"role": "user", "content": f"""You are an AI assistant tasked with compiling a clear and concise daily record based on a collection of personal lifelogs. Your objective is to accurately recount the main events, significant conversations, decisions made, and notable observations from the day, identifying and including the names of the people involved whenever they are mentioned or can be clearly inferred from the context. Present this information as a factual, journal-style entry. While maintaining a narrative flow that connects the day's occurrences, avoid overly literary embellishments, deep emotional interpretations unless explicitly stated in the text, or excessive speculation. The tone should be direct, informative, and reflective of a personal log. Please use markdown to structure the summary, such as headings for different parts of the day or key activities (including timestamps if applicable), to enhance clarity and organization.

Please compile a journal-style daily record from the attached collection of my recorded conversations and events. Focus on creating a clear, factual narrative of what happened throughout the day, using markdown for structure:

{daily_markdown_content}"""
            }
        ],
        stream=should_stream
    )

    if should_stream:
        full_summary = []
        print("\nAI Summary Stream:\n")
        for chunk in response:
            if chunk.choices[0].delta and chunk.choices[0].delta.content:
                content_piece = chunk.choices[0].delta.content
                print(content_piece, end='', flush=True)
                full_summary.append(content_piece)
        print("\n\nEnd of Stream.\n")
        return "".join(full_summary)
    else:
        return response.choices[0].message.content

def main():
    parser = argparse.ArgumentParser(description="Summarize a previously exported daily lifelog markdown file.")
    parser.add_argument("input_file", type=str, help="Path to the local daily lifelog markdown file (e.g., exports/lifelogs/YYYY-MM-DD-lifelogs.md).")
    parser.add_argument("--stream", action=argparse.BooleanOptionalAction, default=False, help="Stream the summary to the console. If not used, summary is only saved to file.")

    args = parser.parse_args()
    input_filepath = args.input_file
    should_stream_summary = args.stream

    # Extract date from filename for the output summary file
    # Assumes filename format YYYY-MM-DD-lifelogs.md or similar ending with -lifelogs.md
    match = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(input_filepath))
    if not match:
        print(f"Error: Could not extract date from input filename: {input_filepath}")
        print("Please ensure the input file is named like 'YYYY-MM-DD-lifelogs.md'.")
        return
    target_date_str = match.group(1)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        return

    try:
        with open(input_filepath, "r", encoding="utf-8") as f:
            daily_markdown_content = f.read()
        print(f"Successfully read lifelog data from: {input_filepath}")
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_filepath}")
        return
    except IOError as e:
        print(f"Error reading input file {input_filepath}: {e}")
        return

    if not daily_markdown_content.strip():
        print(f"The file {input_filepath} is empty or contains only whitespace. Cannot generate summary.")
        return

    print(f"Summarizing content for date: {target_date_str} from local file...")

    summary_text = summarize_daily_markdown(daily_markdown_content, should_stream=should_stream_summary)

    if not summary_text or not summary_text.strip():
        print(f"No summary was generated for {target_date_str}.")
        return

    # Define the output directory and filename
    # Assume input file is in a directory like 'exports/lifelogs/'
    input_file_abspath = os.path.abspath(input_filepath)
    lifelogs_dir = os.path.dirname(input_file_abspath)
    exports_dir = os.path.dirname(lifelogs_dir) # Should be the parent 'exports' directory

    # Specific subdirectory for summaries
    output_summaries_dir = os.path.join(exports_dir, "summaries")

    try:
        os.makedirs(output_summaries_dir, exist_ok=True)
    except OSError as e:
        print(f"Error creating summaries output directory {output_summaries_dir}: {e}")
        return

    output_filename = os.path.join(output_summaries_dir, f"{target_date_str}-summary.md")

    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(summary_text)
        print(f"Successfully saved summary for {target_date_str} to {output_filename}")
    except IOError as e:
        print(f"Error writing summary to file {output_filename}: {e}")

if __name__ == "__main__":
    main()

import os
import argparse
import re
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from .env file
load_dotenv()

def generate_daily_sketch(summary_content: str, target_date_str: str, output_dir: str):
    """Generates a visual sketch image from a daily summary using Gemini's Nano Banana Pro."""

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Please add GEMINI_API_KEY to your .env file.")
        return None

    # Create the Gemini client
    client = genai.Client(api_key=gemini_api_key)

    if not summary_content or not summary_content.strip():
        print("No content provided to generate sketch from the input file.")
        return None

    # Construct the full prompt with the user's detailed instructions
    full_prompt = f"""Role: You are an expert visual synthesizer and sketchnote artist.

Objective: Take the provided text summary of a journal entry and translate it into a single, cohesive "visual sketch" image that metaphorically and literally maps out the day.

Step 1: Conceptual Analysis
Before generating the image, briefly analyze the "shape" of this specific day to determine the best layout.

Is it linear? (Use a winding path or timeline).
Is it chaotic? (Use a storm or vortex center).
Is it a journey? (Use a map or mountain climb).
Is it balanced? (Use scales or a split screen).

Define the layout clearly.

Step 2: Image Generation
Create an image based on your analysis using the following Style Guidelines:

Aesthetic: A double-page spread in a high-quality, hand-drawn field explorer's notebook or visual diary.

Medium: Ink pens (for outlines), colored pencils (for shading), and watercolor washes (for mood).

Visual Elements: Combine literal sketches of events (e.g., a fire pit, a laptop) with metaphorical elements (e.g., storm clouds for stress, sun rays for joy). Use arrows, connectors, thought bubbles, and annotated labels.

Text: Include legible, handwritten-style headers or key phrases from the summary where appropriate (e.g., "Morning Chaos," "The Big Win").

Sidebar: If there are tasks/todos, include a "clipboard" or "sticky note" element pinned to the page.

Input Data: Here is the journal summary for the day:

{summary_content}"""

    print(f"Generating visual sketch for {target_date_str}...")
    print("Using Gemini 3 Pro Image (Nano Banana Pro)...")

    try:
        # Generate the image using Gemini 3 Pro Image (Nano Banana Pro)
        response = client.models.generate_content(
            model='gemini-3-pro-image-preview',
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE'],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9",  # Wide format for double-page spread
                    image_size="4K"       # High resolution
                )
            )
        )

        # Process the response parts
        text_output = []
        image_saved = False
        output_filename = None

        for part in response.parts:
            # Display any text (conceptual analysis)
            if part.text is not None:
                text_output.append(part.text)

            # Save any images
            elif part.inline_data is not None:
                # Get the image
                image = part.as_image()

                # Save to file
                output_filename = os.path.join(output_dir, f"{target_date_str}-sketch.png")
                image.save(output_filename)
                image_saved = True

        # Display the conceptual analysis if present
        if text_output:
            print("\nConceptual Analysis from Gemini:")
            print("\n".join(text_output))
            print()

        if image_saved and output_filename:
            print(f"✅ Successfully saved sketch to: {output_filename}")
            return output_filename
        else:
            print("⚠️  No image was generated in the response.")
            return None

    except Exception as e:
        print(f"❌ Error generating sketch: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description="Generate a visual sketch from a daily summary using Gemini's Nano Banana Pro.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_daily_sketch.py ../exports/summaries/2025-03-02-summary.md
  python generate_daily_sketch.py ../exports/summaries/2025-03-02-summary.md --output-dir ../exports/sketches
        """
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the daily summary markdown file (e.g., exports/summaries/YYYY-MM-DD-summary.md)."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save the sketch. Defaults to exports/sketches/"
    )

    args = parser.parse_args()
    input_filepath = args.input_file

    # Extract date from filename
    # Assumes filename format YYYY-MM-DD-summary.md
    match = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(input_filepath))
    if not match:
        print(f"Error: Could not extract date from input filename: {input_filepath}")
        print("Please ensure the input file is named like 'YYYY-MM-DD-summary.md'.")
        return
    target_date_str = match.group(1)

    # Read the summary content
    try:
        with open(input_filepath, "r", encoding="utf-8") as f:
            summary_content = f.read()
        print(f"Successfully read summary from: {input_filepath}")
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_filepath}")
        return
    except IOError as e:
        print(f"Error reading input file {input_filepath}: {e}")
        return

    if not summary_content.strip():
        print(f"The file {input_filepath} is empty or contains only whitespace. Cannot generate sketch.")
        return

    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        # Default: place in exports/sketches/
        input_file_abspath = os.path.abspath(input_filepath)
        summaries_dir = os.path.dirname(input_file_abspath)
        exports_dir = os.path.dirname(summaries_dir)
        output_dir = os.path.join(exports_dir, "sketches")

    # Create output directory if it doesn't exist
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        print(f"Error creating output directory {output_dir}: {e}")
        return

    # Generate the sketch
    result = generate_daily_sketch(summary_content, target_date_str, output_dir)

    if result:
        print(f"\n🎨 Sketch generation complete!")
        print(f"📁 Saved to: {result}")
    else:
        print(f"\n❌ Failed to generate sketch for {target_date_str}")

if __name__ == "__main__":
    main()

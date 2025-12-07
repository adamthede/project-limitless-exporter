import os
import json
import time
import argparse
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
import base64

# Load environment variables from .env file
load_dotenv()

def create_image_prompt(summary_content: str) -> str:
    """Create the image generation prompt from summary content."""
    return f"""Role: You are an expert visual synthesizer and sketchnote artist.

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

def scan_summary_files(summaries_dir: str, output_dir: str) -> list:
    """Scan for summary files and identify which need sketches generated."""
    summary_files = []

    # Find all summary markdown files
    summaries_path = Path(summaries_dir)
    if not summaries_path.exists():
        print(f"Error: Summaries directory not found: {summaries_dir}")
        return []

    all_summaries = sorted(summaries_path.glob("*-summary.md"))

    print(f"\n📂 Scanning {summaries_dir}...")
    print(f"   Found {len(all_summaries)} summary files")

    # Check which ones already have sketches
    output_path = Path(output_dir)
    existing_sketches = set()
    if output_path.exists():
        for sketch in output_path.glob("*-sketch.png"):
            # Extract date from filename
            match = re.search(r'(\d{4}-\d{2}-\d{2})', sketch.name)
            if match:
                existing_sketches.add(match.group(1))

    print(f"   Found {len(existing_sketches)} existing sketches")

    # Filter to only files that need processing
    for summary_file in all_summaries:
        match = re.search(r'(\d{4}-\d{2}-\d{2})', summary_file.name)
        if match:
            date_str = match.group(1)
            if date_str not in existing_sketches:
                summary_files.append({
                    'path': str(summary_file),
                    'date': date_str
                })

    print(f"   Need to generate: {len(summary_files)} sketches\n")
    return summary_files

def create_batch_requests(summary_files: list) -> list:
    """Create batch request objects from summary files."""
    requests = []

    print("📝 Creating batch requests...")
    for i, file_info in enumerate(summary_files, 1):
        try:
            with open(file_info['path'], 'r', encoding='utf-8') as f:
                summary_content = f.read()

            if not summary_content.strip():
                print(f"   ⚠️  Skipping {file_info['date']}: Empty file")
                continue

            # Create the prompt
            prompt = create_image_prompt(summary_content)

            # Create request object in the format expected by Gemini Batch API
            request = {
                'contents': [{
                    'parts': [{'text': prompt}],
                    'role': 'user'
                }]
            }

            # Store the date with the request for later use
            requests.append({
                'request': request,
                'date': file_info['date']
            })

            if i % 50 == 0:
                print(f"   Processed {i}/{len(summary_files)}...")

        except Exception as e:
            print(f"   ❌ Error reading {file_info['date']}: {e}")
            continue

    print(f"   ✅ Created {len(requests)} requests\n")
    return requests

def create_jsonl_file(requests: list, jsonl_path: str) -> bool:
    """Create a JSONL file with all batch requests."""
    print(f"💾 Creating JSONL file: {jsonl_path}...")

    try:
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for item in requests:
                # Write just the request object (not the metadata)
                json.dump(item['request'], f)
                f.write('\n')

        file_size = os.path.getsize(jsonl_path)
        print(f"   ✅ JSONL file created: {file_size / 1024 / 1024:.2f} MB\n")
        return True
    except Exception as e:
        print(f"   ❌ Error creating JSONL file: {e}\n")
        return False

def upload_file(client: genai.Client, jsonl_path: str) -> str:
    """Upload JSONL file to Google's File API."""
    print("☁️  Uploading JSONL to Google File API...")

    try:
        # Upload the file
        uploaded_file = client.files.upload(path=jsonl_path)
        print(f"   ✅ File uploaded: {uploaded_file.name}")
        print(f"   URI: {uploaded_file.uri}\n")
        return uploaded_file.name
    except Exception as e:
        print(f"   ❌ Error uploading file: {e}\n")
        return None

def submit_batch_job(client: genai.Client, file_name: str, model: str, image_size: str) -> str:
    """Submit the batch job to Gemini API."""
    print("🚀 Submitting batch job...")

    try:
        # Create the batch job
        batch_job = client.batches.create(
            model=model,
            src={'file_uri': file_name},
            config={
                'display_name': f'daily-sketches-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
                'response_modalities': ['TEXT', 'IMAGE'],
                'image_config': {
                    'aspect_ratio': '16:9',
                    'image_size': image_size
                }
            }
        )

        print(f"   ✅ Batch job created: {batch_job.name}")
        print(f"   State: {batch_job.state.name}")
        print(f"   Display name: {batch_job.display_name}\n")
        return batch_job.name
    except Exception as e:
        print(f"   ❌ Error creating batch job: {e}\n")
        return None

def monitor_batch_job(client: genai.Client, job_name: str, check_interval: int = 300) -> bool:
    """Monitor batch job until completion."""
    print(f"⏳ Monitoring batch job (checking every {check_interval//60} minutes)...\n")

    start_time = time.time()

    while True:
        try:
            job = client.batches.get(name=job_name)
            elapsed = time.time() - start_time
            elapsed_str = f"{int(elapsed//3600)}h {int((elapsed%3600)//60)}m"

            state = job.state.name
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Get completion stats if available
            stats = ""
            if hasattr(job, 'request_counts'):
                total = job.request_counts.total if hasattr(job.request_counts, 'total') else 0
                succeeded = job.request_counts.succeeded if hasattr(job.request_counts, 'succeeded') else 0
                failed = job.request_counts.failed if hasattr(job.request_counts, 'failed') else 0
                stats = f" | {succeeded}/{total} succeeded, {failed} failed"

            print(f"[{timestamp}] State: {state} | Elapsed: {elapsed_str}{stats}")

            if state == 'JOB_STATE_SUCCEEDED':
                print(f"\n✅ Batch job completed successfully!\n")
                return True
            elif state == 'JOB_STATE_FAILED':
                print(f"\n❌ Batch job failed\n")
                return False
            elif state == 'JOB_STATE_CANCELLED':
                print(f"\n⚠️  Batch job was cancelled\n")
                return False

            # Wait before checking again
            time.sleep(check_interval)

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Monitoring interrupted by user")
            print(f"Job is still running. You can check status later with:")
            print(f"  Job name: {job_name}\n")
            return False
        except Exception as e:
            print(f"   ❌ Error checking job status: {e}")
            time.sleep(check_interval)

def download_results(client: genai.Client, job_name: str, requests: list, output_dir: str) -> int:
    """Download and save all generated images."""
    print("📥 Downloading results...\n")

    try:
        # Get the completed job
        job = client.batches.get(name=job_name)

        # Get the output file
        if not hasattr(job, 'output_uri') or not job.output_uri:
            print("❌ No output file found in job")
            return 0

        # Download the output JSONL file
        output_file_name = job.output_uri.split('/')[-1]
        print(f"   Downloading output file: {output_file_name}")

        # Create output directory if needed
        os.makedirs(output_dir, exist_ok=True)

        # The output is a file reference, we need to download it
        output_file = client.files.get(name=job.output_uri)

        # Read the results (this is a JSONL file)
        # Each line contains the response for one request
        saved_count = 0

        # Download the file content
        temp_output_path = "/tmp/batch_results.jsonl"
        # Note: The SDK may not have a direct download method
        # We'll need to access the response data differently

        # Alternative: iterate through responses if available
        if hasattr(job, 'responses'):
            for i, response in enumerate(job.responses):
                if i >= len(requests):
                    break

                date_str = requests[i]['date']

                # Process the response
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        # Save the image
                        image = part.as_image()
                        output_path = os.path.join(output_dir, f"{date_str}-sketch.png")
                        image.save(output_path)
                        saved_count += 1

                        if saved_count % 10 == 0:
                            print(f"   Saved {saved_count} images...")

        print(f"\n✅ Saved {saved_count} sketches to {output_dir}\n")
        return saved_count

    except Exception as e:
        print(f"❌ Error downloading results: {e}\n")
        import traceback
        traceback.print_exc()
        return 0

def main():
    parser = argparse.ArgumentParser(
        description="Batch generate visual sketches for all daily summaries using Gemini Batch API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate sketches for all summaries (4K resolution)
  python batch_generate_sketches.py

  # Use 2K resolution for faster/cheaper processing
  python batch_generate_sketches.py --image-size 2K

  # Custom directories
  python batch_generate_sketches.py --summaries-dir ../exports/summaries --output-dir ../exports/sketches

  # Check status of existing job
  python batch_generate_sketches.py --check-job BATCH_JOB_NAME
        """
    )

    parser.add_argument(
        "--summaries-dir",
        type=str,
        default="../exports/summaries",
        help="Directory containing summary markdown files"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="../exports/sketches",
        help="Directory to save generated sketches"
    )
    parser.add_argument(
        "--image-size",
        type=str,
        choices=["2K", "4K"],
        default="4K",
        help="Image resolution (2K=$0.067/image, 4K=$0.12/image)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="models/gemini-3-pro-image-preview",
        help="Model to use for image generation"
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=300,
        help="Seconds between status checks (default: 300 = 5 minutes)"
    )
    parser.add_argument(
        "--check-job",
        type=str,
        help="Check status of existing job by name"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually submitting the job"
    )

    args = parser.parse_args()

    # Verify API key
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("❌ Error: GEMINI_API_KEY environment variable not set.")
        print("Please add GEMINI_API_KEY to your .env file.")
        return

    # Create client
    client = genai.Client(api_key=gemini_api_key)

    # If checking existing job
    if args.check_job:
        print(f"Checking status of job: {args.check_job}\n")
        success = monitor_batch_job(client, args.check_job, args.check_interval)
        return

    # Display header
    print("\n" + "="*70)
    print("🎨 BATCH SKETCH GENERATION - Gemini Nano Banana Pro")
    print("="*70 + "\n")

    # Scan for summary files
    summary_files = scan_summary_files(args.summaries_dir, args.output_dir)

    if not summary_files:
        print("✅ All summaries already have sketches! Nothing to do.\n")
        return

    # Calculate cost
    cost_per_image = 0.12 if args.image_size == "4K" else 0.067
    total_cost = len(summary_files) * cost_per_image

    print(f"💰 Cost Estimate:")
    print(f"   Images: {len(summary_files)}")
    print(f"   Resolution: {args.image_size}")
    print(f"   Rate: ${cost_per_image}/image (batch pricing)")
    print(f"   Total: ${total_cost:.2f}\n")

    if args.dry_run:
        print("🏃 DRY RUN - Not actually submitting job\n")
        return

    # Confirm with user
    response = input(f"Continue with batch generation? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Cancelled.\n")
        return

    print()

    # Create batch requests
    requests = create_batch_requests(summary_files)

    if not requests:
        print("❌ No valid requests created. Exiting.\n")
        return

    # Create JSONL file
    jsonl_path = "/tmp/batch_sketch_requests.jsonl"
    if not create_jsonl_file(requests, jsonl_path):
        return

    # Upload file
    file_name = upload_file(client, jsonl_path)
    if not file_name:
        return

    # Submit batch job
    job_name = submit_batch_job(client, file_name, args.model, args.image_size)
    if not job_name:
        return

    # Save job info for later reference
    print(f"💾 Save this job name to check status later:")
    print(f"   {job_name}\n")

    # Monitor job
    success = monitor_batch_job(client, job_name, args.check_interval)

    if success:
        # Download results
        saved_count = download_results(client, job_name, requests, args.output_dir)

        if saved_count > 0:
            print("="*70)
            print(f"🎉 SUCCESS! Generated {saved_count} sketches")
            print(f"📁 Saved to: {args.output_dir}")
            print("="*70 + "\n")
        else:
            print("⚠️  Job completed but no images were saved. Check the output.\n")
    else:
        print(f"⚠️  Job did not complete successfully.")
        print(f"You can check the status later with:")
        print(f"  python batch_generate_sketches.py --check-job {job_name}\n")

if __name__ == "__main__":
    main()

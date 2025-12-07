#!/usr/bin/env python3
"""
Simple script to check the status of a Gemini batch job.
"""
import os
import argparse
from dotenv import load_dotenv
from google import genai

load_dotenv()

def check_batch_status(job_name: str):
    """Check and display the status of a batch job."""

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("❌ Error: GEMINI_API_KEY not set")
        return

    client = genai.Client(api_key=gemini_api_key)

    try:
        job = client.batches.get(name=job_name)

        print("\n" + "="*60)
        print("📊 BATCH JOB STATUS")
        print("="*60)
        print(f"\nJob Name: {job.name}")
        print(f"Display Name: {job.display_name if hasattr(job, 'display_name') else 'N/A'}")
        print(f"State: {job.state.name}")
        print(f"Model: {job.model if hasattr(job, 'model') else 'N/A'}")

        # Show request counts if available
        if hasattr(job, 'request_counts'):
            counts = job.request_counts
            print("\nProgress:")
            if hasattr(counts, 'total'):
                print(f"  Total: {counts.total}")
            if hasattr(counts, 'succeeded'):
                print(f"  Succeeded: {counts.succeeded}")
            if hasattr(counts, 'failed'):
                print(f"  Failed: {counts.failed}")
            if hasattr(counts, 'pending'):
                print(f"  Pending: {counts.pending}")

        # Show timestamps if available
        if hasattr(job, 'create_time'):
            print(f"\nCreated: {job.create_time}")
        if hasattr(job, 'update_time'):
            print(f"Updated: {job.update_time}")

        # Show output info if completed
        if hasattr(job, 'output_uri') and job.output_uri:
            print(f"\nOutput File: {job.output_uri}")

        print("\n" + "="*60 + "\n")

        # Interpret state
        state = job.state.name
        if state == 'JOB_STATE_SUCCEEDED':
            print("✅ Job completed successfully!")
            print("Run the batch script again to download results.\n")
        elif state == 'JOB_STATE_FAILED':
            print("❌ Job failed")
        elif state == 'JOB_STATE_CANCELLED':
            print("⚠️  Job was cancelled")
        elif state in ['JOB_STATE_PENDING', 'JOB_STATE_RUNNING']:
            print("⏳ Job is still processing...")
            print("Check back later for results.\n")

    except Exception as e:
        print(f"\n❌ Error checking job status: {e}\n")

def main():
    parser = argparse.ArgumentParser(
        description="Check the status of a Gemini batch job"
    )
    parser.add_argument(
        "job_name",
        type=str,
        help="The batch job name (e.g., batches/abc123)"
    )

    args = parser.parse_args()
    check_batch_status(args.job_name)

if __name__ == "__main__":
    main()

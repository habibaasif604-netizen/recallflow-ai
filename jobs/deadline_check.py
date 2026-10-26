import sys
import os
import argparse
import json

# Force Python to look in the project root directory first
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.reminders import run_deadline_check

def main():
    parser = argparse.ArgumentParser(description="Run RecallFlow AI deadline reminder check.")
    parser.add_argument("--token", type=str, default="", help="Secret job token for authentication")
    parser.add_argument("--dry-run", action="store_true", help="Run check without writing to reminder log")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    # Authenticate via environment variable or argument token
    expected_token = os.environ.get("RECALLFLOW_JOB_TOKEN", "")
    provided_token = args.token or os.environ.get("RECALLFLOW_JOB_TOKEN_PROVIDED", "")

    if expected_token and provided_token != expected_token:
        if args.json:
            print(json.dumps({"error": "Unauthorized: Invalid job token"}))
        else:
            print("❌ Unauthorized: Invalid job token.", file=sys.stderr)
        sys.exit(2)

    try:
        results = run_deadline_check(dry_run=args.dry_run)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"=== Deadline Check Complete ===")
            print(f"Checked at: {results['checked_at']}")
            print(f"Overdue tasks: {len(results['overdue'])}")
            print(f"Due today tasks: {len(results['due_today'])}")
            print(f"Reminders sent (new): {len(results['reminders_sent'])}")
            print(f"Reminders skipped (deduplicated): {len(results['reminders_skipped'])}")
            print("Job finished successfully. ✓")
        sys.exit(0)
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"❌ Job failed with error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
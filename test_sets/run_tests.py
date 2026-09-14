"""Automated test runner for Room Change Detector.

Usage:
    python run_tests.py --api-key sk-...
    # or set OPENAI_API_KEY environment variable
"""

import os
import sys
import json
import time
import argparse
import requests


def run_tests():
    parser = argparse.ArgumentParser(description="Run tests against the analyze API.")
    parser.add_argument(
        "--api-key",
        type=str,
        help="OpenAI API key",
        default=os.environ.get("OPENAI_API_KEY"),
    )
    parser.add_argument(
        "--base-url",
        type=str,
        help="Base URL of the server",
        default="http://localhost:8000",
    )
    args = parser.parse_args()

    if not args.api_key:
        print("ERROR: Provide --api-key or set OPENAI_API_KEY env var.")
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    expected_file = os.path.join(script_dir, "expected_results.json")

    if not os.path.exists(expected_file):
        print(f"ERROR: {expected_file} not found. Run generate_test_set.py first.")
        sys.exit(1)

    with open(expected_file, "r") as f:
        expected_results = json.load(f)

    actual_results_log = {}
    summary = {"total_sets": 0, "passed_sets": 0, "total_objects": 0, "correct": 0, "false_positives": 0, "false_negatives": 0}

    for set_name, expected_data in expected_results.items():
        print(f"\n{'='*60}")
        print(f"TEST SET: {set_name}")
        print(f"Description: {expected_data.get('description')}")
        print(f"{'='*60}")

        before_dir = os.path.join(script_dir, f"{set_name}_before")
        after_dir = os.path.join(script_dir, f"{set_name}_after")

        before_img = os.path.join(before_dir, "photo1.png")
        after_img = os.path.join(after_dir, "photo1.png")

        if not os.path.exists(before_img) or not os.path.exists(after_img):
            print(f"  SKIP: images not found (run generate_test_set.py first)")
            continue

        # Build multipart form data (matches the FastAPI endpoint)
        files = [
            ("before_images", ("photo1.png", open(before_img, "rb"), "image/png")),
            ("after_images", ("photo1.png", open(after_img, "rb"), "image/png")),
        ]
        form_data = {"api_key": args.api_key}

        start_time = time.time()
        error = None
        result = {}

        try:
            resp = requests.post(
                f"{args.base_url}/api/analyze",
                files=files,
                data=form_data,
                timeout=120,
            )
            resp.raise_for_status()
            result = resp.json()
        except requests.RequestException as e:
            print(f"  API ERROR: {e}")
            error = str(e)

        elapsed = time.time() - start_time

        # Close file handles
        for _, fobj in files:
            fobj[1].close()

        # ── Compare results ──────────────────────────────────────────────
        summary["total_sets"] += 1
        set_passed = True

        if error:
            actual_results_log[set_name] = {"error": error, "elapsed": elapsed}
            continue

        # Extract actual statuses
        actual_changes = {}
        for obj in result.get("confirmed_changes", []):
            actual_changes[obj["name"].lower()] = obj["status"]
        for obj in result.get("unchanged_objects", []):
            actual_changes[obj["name"].lower()] = "unchanged"
        for obj in result.get("uncertain_matches", []):
            actual_changes[obj["object_name"].lower()] = "not_verifiable"

        expected_changes = expected_data.get("expected_changes", [])

        print(f"\n  Processing time: {elapsed:.1f}s (server: {result.get('processing_time_seconds', 0):.1f}s)")
        print(f"  Tokens: {result.get('token_usage', {}).get('total_tokens', 0):,}")
        print(f"  Est. cost: ${result.get('estimated_cost_usd', 0):.4f}")

        print(f"\n  {'Object':<20} {'Expected':<18} {'Actual':<18} {'Match?'}")
        print(f"  {'-'*20} {'-'*18} {'-'*18} {'-'*6}")

        matched_names = set()
        for exp in expected_changes:
            obj_name = exp["object"].lower()
            exp_status = exp["expected_status"]
            act_status = actual_changes.get(obj_name, "MISSING")
            matched_names.add(obj_name)
            summary["total_objects"] += 1

            match = "✓" if act_status == exp_status else "✗"
            if act_status == exp_status:
                summary["correct"] += 1
            else:
                set_passed = False
                if exp_status == "unchanged" and act_status not in ("unchanged", "MISSING"):
                    summary["false_positives"] += 1
                elif act_status == "MISSING":
                    summary["false_negatives"] += 1

            print(f"  {exp['object']:<20} {exp_status:<18} {act_status:<18} {match}")

        # Check for false positives (objects the model reported as changed but shouldn't be)
        for name, status in actual_changes.items():
            if name not in matched_names and status not in ("unchanged",):
                summary["false_positives"] += 1
                set_passed = False
                print(f"  {'[FP] ' + name:<20} {'(not expected)':<18} {status:<18} ✗")

        if set_passed:
            summary["passed_sets"] += 1
            print(f"\n  ✓ SET PASSED")
        else:
            print(f"\n  ✗ SET FAILED")

        actual_results_log[set_name] = {
            "elapsed": elapsed,
            "processing_time_seconds": result.get("processing_time_seconds"),
            "token_usage": result.get("token_usage"),
            "estimated_cost_usd": result.get("estimated_cost_usd"),
            "confirmed_changes": result.get("confirmed_changes", []),
            "unchanged_objects": result.get("unchanged_objects", []),
            "uncertain_matches": result.get("uncertain_matches", []),
            "scene": result.get("scene"),
            "warnings": result.get("warnings", []),
        }

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Sets passed:     {summary['passed_sets']}/{summary['total_sets']}")
    print(f"  Objects correct: {summary['correct']}/{summary['total_objects']}")
    print(f"  False positives: {summary['false_positives']}")
    print(f"  False negatives: {summary['false_negatives']}")

    # Save detailed results
    out_path = os.path.join(script_dir, "actual_results.json")
    with open(out_path, "w") as f:
        json.dump(actual_results_log, f, indent=2)
    print(f"\n  Detailed results saved to {out_path}")


if __name__ == "__main__":
    run_tests()

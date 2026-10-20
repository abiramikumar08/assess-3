"""IncuBrix Batch Runner (Integration Standard Requirement 10).

Runs a folder or file of test inputs against the B-roll Engine API
and writes all results (videos, timeline.json, manifest.json, captions.srt)
to a designated output folder.

Usage:
    python batch_runner.py --input test_inputs/ --output test_outputs/ [--api-url http://localhost:8000]
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
import httpx

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def parse_args():
    parser = argparse.ArgumentParser(description="IncuBrix B-Roll Engine Batch Runner")
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to an input JSON file, text file, or directory of input files",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Path to directory where batch results will be written",
    )
    parser.add_argument(
        "--api-url",
        "-u",
        default="http://localhost:8000",
        help="Base URL of running IncuBrix engine API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Execute pipeline directly in-process without requiring live HTTP server/Redis",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Seconds between polling job status",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Maximum seconds to wait for a job to complete",
    )
    return parser.parse_args()


def load_input_file(path: Path) -> dict:
    content = path.read_text(encoding="utf-8").strip()
    if path.suffix.lower() == ".json":
        return json.loads(content)
    else:
        # Plain text script
        return {
            "script": content,
            "aspect_ratios": ["16:9"],
            "captions": {"burn_in": False, "srt": True},
        }


def run_batch():
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    items: list[tuple[str, dict]] = []
    if input_path.is_file():
        items.append((input_path.stem, load_input_file(input_path)))
    elif input_path.is_dir():
        for p in sorted(input_path.iterdir()):
            if p.is_file() and p.suffix.lower() in (".json", ".txt"):
                items.append((p.stem, load_input_file(p)))
    else:
        print(f"Error: Input path {input_path} does not exist", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(items)} test input(s) to process.")
    results_summary = []

    if args.direct:
        from app.jobs import process_job
        for name, payload in items:
            print(f"\nProcessing '{name}' in direct mode...")
            item_out = output_dir / name
            item_out.mkdir(parents=True, exist_ok=True)
            t0 = time.time()
            try:
                res = process_job(payload)
                elapsed = time.time() - t0
                print(f"  [OK] Finished in {elapsed:.2f}s")
                summary = {"name": name, "status": "succeeded", "elapsed_s": round(elapsed, 2), "result": res}
            except Exception as exc:
                print(f"  [FAIL] Failed: {exc}")
                summary = {"name": name, "status": "failed", "error": str(exc)}
            results_summary.append(summary)
    else:
        client = httpx.Client(base_url=args.api_url, timeout=30.0)
        # Check health
        try:
            r = client.get("/health")
            if r.status_code != 200:
                print(f"Warning: /health returned {r.status_code}: {r.text}")
        except Exception as exc:
            print(f"Could not connect to {args.api_url} ({exc}). Running directly in-process...")
            from app.jobs import process_job
            for name, payload in items:
                print(f"\nProcessing '{name}' (fallback direct)...")
                t0 = time.time()
                try:
                    res = process_job(payload)
                    elapsed = time.time() - t0
                    print(f"  [OK] Finished in {elapsed:.2f}s")
                    summary = {"name": name, "status": "succeeded", "elapsed_s": round(elapsed, 2), "result": res}
                except Exception as exc:
                    print(f"  [FAIL] Failed: {exc}")
                    summary = {"name": name, "status": "failed", "error": str(exc)}
                results_summary.append(summary)
            # Write summary
            (output_dir / "batch_summary.json").write_text(json.dumps(results_summary, indent=2), encoding="utf-8")
            return

        for name, payload in items:
            print(f"\nSubmitting '{name}' to {args.api_url}...")
            t0 = time.time()
            headers = {"Idempotency-Key": f"batch-{name}-{int(time.time())}"}
            resp = client.post("/api/v1/broll/jobs", json=payload, headers=headers)
            if resp.status_code != 202:
                print(f"  [FAIL] Submission failed: HTTP {resp.status_code} {resp.text}")
                results_summary.append({"name": name, "status": "submission_failed", "error": resp.text})
                continue

            job_id = resp.json()["job_id"]
            print(f"  Job queued with ID: {job_id}. Waiting for completion...")

            deadline = time.time() + args.timeout
            final_status = "timeout"
            job_data = {}
            while time.time() < deadline:
                time.sleep(args.poll_interval)
                s_resp = client.get(f"/api/v1/jobs/{job_id}")
                if s_resp.status_code != 200:
                    continue
                job_data = s_resp.json()
                st = job_data.get("status")
                print(f"    Progress: {job_data.get('progress', 0)}% (status: {st})")
                if st in ("succeeded", "failed"):
                    final_status = st
                    break

            elapsed = time.time() - t0
            if final_status == "succeeded":
                print(f"  [OK] Succeeded in {elapsed:.2f}s")
            else:
                print(f"  [FAIL] Status: {final_status} ({job_data.get('error')})")

            results_summary.append({
                "name": name,
                "job_id": job_id,
                "status": final_status,
                "elapsed_s": round(elapsed, 2),
                "data": job_data,
            })

    summary_file = output_dir / "batch_summary.json"
    summary_file.write_text(json.dumps(results_summary, indent=2), encoding="utf-8")
    print(f"\nBatch run complete! Summary written to: {summary_file}")


if __name__ == "__main__":
    run_batch()

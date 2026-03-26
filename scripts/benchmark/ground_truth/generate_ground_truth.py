"""Ground truth generator.

Reads questions/questions.json, runs the mongodb_query for each question
against the live database, and writes raw results to ground_truth/raw/.

Usage (one-time, or when the question set changes):

    python scripts/benchmark/ground_truth/generate_ground_truth.py

Each output file is ground_truth/raw/{question_id:03d}.json with the shape:

    {
      "id": 1,
      "question": "...",
      "generated_at": "2026-03-23T...",
      "manual_only": false,
      "records": [...],          // raw DB records (list)
      "record_count": N,
      "error": null              // or an error string
    }

Questions where manual_only=true (no parseable mongodb_query) still get a
stub file so the judge pipeline doesn't need special-casing.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the project src is importable when running directly.
REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
BENCHMARK_DIR = Path(__file__).parent.parent

from aind_data_access_api.document_db import MetadataDbClient  # noqa: E402

_DB_HOST = "api.allenneuraldynamics.org"
_DB_VERSION = "v2"


def _make_client() -> MetadataDbClient:
    return MetadataDbClient(host=_DB_HOST, version=_DB_VERSION)


def _run_query(client: MetadataDbClient, mongodb_query: dict) -> list:
    """Execute a query dict and return raw records."""
    if "agg_pipeline" in mongodb_query:
        return client.aggregate_docdb_records(mongodb_query["agg_pipeline"])

    # Simple filter / projection query.
    filter_q = mongodb_query.get("filter", {})
    projection = mongodb_query.get("projection", {})
    # Use a generous limit so we capture complete result sets.  Very large
    # result sets (>500) are unlikely for the benchmark questions.
    limit = mongodb_query.get("limit", 500)
    return client.retrieve_docdb_records(
        filter_query=filter_q,
        projection=projection,
        limit=limit,
    )


def generate(
    questions_file: Path | None = None,
    output_dir: Path | None = None,
    overwrite: bool = False,
) -> None:
    if questions_file is None:
        questions_file = BENCHMARK_DIR / "questions" / "questions.json"
    if output_dir is None:
        output_dir = BENCHMARK_DIR / "ground_truth" / "raw"

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(questions_file, encoding="utf-8") as fh:
        questions = json.load(fh)

    client = _make_client()
    total = len(questions)

    for i, q in enumerate(questions, 1):
        q_id = q["id"]
        out_path = output_dir / f"{q_id:03d}.json"

        if out_path.exists() and not overwrite:
            print(f"[{i}/{total}] #{q_id} — skipping (already exists)", file=sys.stderr)
            continue

        stub: dict = {
            "id": q_id,
            "question": q["question"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "manual_only": q.get("manual_only", True),
            "records": [],
            "record_count": 0,
            "error": None,
        }

        if q.get("manual_only"):
            print(f"[{i}/{total}] #{q_id} — manual_only, writing stub", file=sys.stderr)
            out_path.write_text(json.dumps(stub, indent=2, default=str))
            continue

        print(f"[{i}/{total}] #{q_id} — running query …", end="", file=sys.stderr)
        try:
            records = _run_query(client, q["mongodb_query"])
            stub["records"] = records
            stub["record_count"] = len(records)
            print(f" {len(records)} records", file=sys.stderr)
        except Exception as exc:
            stub["error"] = str(exc)
            print(f" ERROR: {exc}", file=sys.stderr)

        out_path.write_text(json.dumps(stub, indent=2, default=str))

    print(f"\nDone — results in {output_dir}", file=sys.stderr)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate ground-truth raw DB results")
    parser.add_argument("--overwrite", action="store_true", help="Re-run even if output file exists")
    parser.add_argument("--questions", type=Path, default=None, help="Path to questions.json")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory for raw/*.json files")
    args = parser.parse_args()

    generate(
        questions_file=args.questions,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
    )

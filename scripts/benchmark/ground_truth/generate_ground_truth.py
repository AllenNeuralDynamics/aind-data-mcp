"""Ground truth generator.

Reads questions/questions.json, runs the query for each question against the
live database, and writes raw results to ground_truth/raw/.

Usage (one-time, or when the question set changes):

    python scripts/benchmark/ground_truth/generate_ground_truth.py

Each output file is ground_truth/raw/{question_id:03d}.json with the shape:

    {
      "id": 1,
      "question": "...",
      "generated_at": "...",
      "records": [...],          // raw DB records (list)
      "record_count": N,
      "error": null              // or an error string
    }
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


def _run_query(client: MetadataDbClient, q: dict) -> list:
    """Execute a question's query and return raw records.

    Dispatches on whether the question has an agg_pipeline or a filter.
    """
    agg_pipeline = q.get("agg_pipeline")
    if agg_pipeline:
        return client.aggregate_docdb_records(agg_pipeline)

    return client.retrieve_docdb_records(
        filter_query=q.get("filter", {}),
        projection=q.get("projection", {}),
        limit=q.get("limit", 500),
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
            "records": [],
            "record_count": 0,
            "error": None,
        }

        print(f"[{i}/{total}] #{q_id} — running query ...", end="", file=sys.stderr)
        try:
            records = _run_query(client, q)
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

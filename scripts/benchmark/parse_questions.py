"""Parse the source benchmark CSV into questions/questions.json.

Run once (or re-run to refresh) before generating ground truth or running
the benchmark agent:

    python scripts/benchmark/parse_questions.py
"""

import csv
import json
import sys
from pathlib import Path

# Allow running from any cwd.
BENCHMARK_DIR = Path(__file__).parent
CSV_PATH = BENCHMARK_DIR.parent / "gamer_benchmark_6_16(dataset_941e2a78-3066-458c-99b8).csv"
OUTPUT_PATH = BENCHMARK_DIR / "questions" / "questions.json"


def _try_parse_json(raw: str) -> tuple[dict | list | None, bool]:
    """Attempt to parse a string as JSON.

    Returns (parsed_value, success).  Returns (None, False) if the string is
    blank, looks like Python code, or is invalid JSON.
    """
    if not raw:
        return None, False
    stripped = raw.strip()
    # Heuristic: Python code fragments start with keywords or identifiers.
    python_hints = ("import ", "from ", "agg_pipeline", "docdb_api_client", "filter =")
    if any(stripped.startswith(h) for h in python_hints):
        return None, False
    try:
        return json.loads(stripped), True
    except json.JSONDecodeError:
        return None, False


def parse_questions(csv_path: Path = CSV_PATH, output_path: Path = OUTPUT_PATH) -> list[dict]:
    questions = []
    q_id = 1

    with open(csv_path, newline="", encoding="latin-1") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            question_text = row.get("input_question", "").strip()
            if not question_text:
                continue

            mongodb_query, has_query = _try_parse_json(row.get("output_mongodb_query", ""))

            q = {
                "id": q_id,
                "question": question_text,
                "expected_answer": row.get("output_answer", "").strip(),
                # Stored for reference but not used as authoritative ground truth.
                "python_query": row.get("output_python", "").strip(),
                # Parsed MongoDB query dict; None when the column contains
                # Python code or is blank.
                "mongodb_query": mongodb_query,
                # True when no machine-runnable query is available — judge
                # will compare against the expected_answer text only.
                "manual_only": not has_query,
                "query_type": row.get("query_type", "").strip(),
                "complexity": row.get("complexity", "").strip(),
                "ambiguous": row.get("ambiguous", "0").strip() == "1",
            }
            questions.append(q)
            q_id += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(questions, fh, indent=2)

    print(f"Parsed {len(questions)} questions → {output_path}", file=sys.stderr)
    return questions


if __name__ == "__main__":
    parse_questions()

"""Generate a Harbor task dataset from the benchmark questions.

Each question in ``questions/questions.json`` becomes a self-contained Harbor
task directory. The authoritative answer for a question comes from its
ground-truth records (``ground_truth/raw/{id:03d}.json``), which are baked into
the task's ``tests/ground_truth.json`` for the LLM judge to grade against.

Layout produced under ``harbor/tasks/``::

    tasks/
      aind-q001/
        task.toml                 # metadata + MCP sidecar declaration
        instruction.md            # the question (agent writes answer to /app/answer.txt)
        environment/              # agent container + aind-data-mcp sidecar (copied)
        tests/
          test.sh                 # verifier entrypoint (copied)
          llm_judge.py            # LLM judge (copied)
          ground_truth.json       # authoritative raw DB records for this question

Usage::

    python scripts/benchmark/harbor/build_dataset.py
    # then, e.g.:
    harbor run -p scripts/benchmark/harbor/tasks/aind-q001 \
        -a claude-code -m anthropic/claude-sonnet-5 --env docker

Run ``generate_ground_truth.py`` first (or pass ``--generate-ground-truth``)
so the ground-truth files exist before the dataset is built.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HARBOR_DIR = Path(__file__).parent
BENCHMARK_DIR = HARBOR_DIR.parent
TEMPLATE_DIR = HARBOR_DIR / "template"
DEFAULT_QUESTIONS = BENCHMARK_DIR / "questions" / "questions.json"
DEFAULT_GROUND_TRUTH = BENCHMARK_DIR / "ground_truth" / "raw"
DEFAULT_TASKS_DIR = HARBOR_DIR / "tasks"

INSTRUCTION_TEMPLATE = """\
# AIND Data Question

You have access to an MCP server named `aind-data-mcp` (streamable-http
transport at `https://metadata-portal.allenneuraldynamics.org/mcp/`). It exposes
tools for querying the Allen Institute for Neural Dynamics (AIND) neuroscience
metadata database.

Use the MCP server's tools to answer the following question:

> {question}

When you are confident in your answer, write your final answer as plain text to
the file `/app/answer.txt`. Only the contents of that file are graded, so make
it a complete, self-contained response to the question.
"""

TASK_TOML_HEAD = """\
version = "1.0"

[metadata]
question_id = {question_id}
complexity = "{complexity}"
benchmark = "aind-data-mcp"
verify_mode = "{verify_mode}"
"""

# LLM-judge verifier: needs model + provider credentials.
VERIFIER_LLM = """
[verifier]
timeout_sec = 300.0

[verifier.env]
# litellm model id for the judge. Use a bedrock/... id to grade via Amazon
# Bedrock (litellm reads AWS_BEARER_TOKEN_BEDROCK or the standard AWS chain).
JUDGE_MODEL = "${JUDGE_MODEL:-anthropic/claude-haiku-4-5}"
# Amazon Bedrock credentials (API-key/bearer-token auth or the standard chain).
AWS_BEARER_TOKEN_BEDROCK = "${AWS_BEARER_TOKEN_BEDROCK:-}"
AWS_REGION = "${AWS_REGION:-us-west-2}"
AWS_ACCESS_KEY_ID = "${AWS_ACCESS_KEY_ID:-}"
AWS_SECRET_ACCESS_KEY = "${AWS_SECRET_ACCESS_KEY:-}"
AWS_SESSION_TOKEN = "${AWS_SESSION_TOKEN:-}"
# Direct-provider keys (used when JUDGE_MODEL is an Anthropic/OpenAI id).
ANTHROPIC_API_KEY = "${ANTHROPIC_API_KEY:-}"
OPENAI_API_KEY = "${OPENAI_API_KEY:-}"
"""

# Deterministic verifier: stdlib-only string checks, no model/credentials.
VERIFIER_DETERMINISTIC = """
[verifier]
timeout_sec = 120.0
"""

TASK_TOML_TAIL = """
[agent]
timeout_sec = 300.0

[environment]
build_timeout_sec = 900.0

[[environment.mcp_servers]]
name = "aind-data-mcp"
transport = "streamable-http"
url = "https://metadata-portal.allenneuraldynamics.org/mcp/"
"""


def _load_questions(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load_ground_truth(ground_truth_dir: Path, q_id: int) -> dict | None:
    gt_path = ground_truth_dir / f"{q_id:03d}.json"
    if not gt_path.exists():
        return None
    with open(gt_path, encoding="utf-8") as fh:
        return json.load(fh)


def _write_task(
    task_dir: Path,
    question: dict,
    ground_truth: dict,
) -> str:
    """Write one task directory. Returns the verify mode used ('deterministic'
    or 'llm')."""
    # Fresh directory each run so removed questions don't leave stale tasks.
    if task_dir.exists():
        shutil.rmtree(task_dir)
    task_dir.mkdir(parents=True)

    verify = question.get("verify")
    mode = "deterministic" if verify else "llm"

    # Environment is identical for every task.
    shutil.copytree(TEMPLATE_DIR / "environment", task_dir / "environment")

    # Verifier files + task.toml depend on the mode.
    if verify:
        shutil.copytree(TEMPLATE_DIR / "verify", task_dir / "tests")
        (task_dir / "tests" / "expected.json").write_text(
            json.dumps(
                {
                    "id": question["id"],
                    "question": question["question"],
                    "must_include": verify.get("must_include", []),
                    "min_matches": verify.get("min_matches"),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        verifier_block = VERIFIER_DETERMINISTIC
    else:
        shutil.copytree(TEMPLATE_DIR / "tests", task_dir / "tests")
        (task_dir / "tests" / "ground_truth.json").write_text(
            json.dumps(
                {
                    "id": question["id"],
                    "question": question["question"],
                    "records": ground_truth.get("records", []),
                    "record_count": ground_truth.get("record_count"),
                },
                indent=2,
                default=str,
            )
        )
        verifier_block = VERIFIER_LLM

    # Per-task files.
    (task_dir / "instruction.md").write_text(
        INSTRUCTION_TEMPLATE.format(question=question["question"])
    )
    task_toml = (
        TASK_TOML_HEAD.format(
            question_id=question["id"],
            complexity=question.get("complexity", "unknown"),
            verify_mode=mode,
        )
        + verifier_block
        + TASK_TOML_TAIL
    )
    (task_dir / "task.toml").write_text(task_toml)
    return mode


def build(
    questions_path: Path,
    ground_truth_dir: Path,
    tasks_dir: Path,
    question_ids: list[int] | None = None,
) -> None:
    questions = _load_questions(questions_path)
    if question_ids:
        id_set = set(question_ids)
        questions = [q for q in questions if q["id"] in id_set]

    tasks_dir.mkdir(parents=True, exist_ok=True)

    built = 0
    modes = {"deterministic": 0, "llm": 0}
    skipped: list[int] = []
    for q in questions:
        gt = _load_ground_truth(ground_truth_dir, q["id"])
        # Deterministic tasks grade against expected.json (not raw records), so
        # they don't need a ground-truth file; LLM-judge tasks do.
        if gt is None and not q.get("verify"):
            skipped.append(q["id"])
            gt_file = ground_truth_dir / f"{q['id']:03d}.json"
            print(
                f"  ! skipping q{q['id']:03d}: no ground-truth file ({gt_file})",
                file=sys.stderr,
            )
            continue
        task_dir = tasks_dir / f"aind-q{q['id']:03d}"
        mode = _write_task(task_dir, q, gt or {})
        modes[mode] += 1
        built += 1
        rel = task_dir.relative_to(HARBOR_DIR.parent.parent.parent)
        print(f"  + {rel}  [{mode}]")

    print(
        f"\nBuilt {built} task(s) in {tasks_dir} "
        f"({modes['deterministic']} deterministic, {modes['llm']} llm-judge)",
        file=sys.stderr,
    )
    if skipped:
        print(
            f"Skipped {len(skipped)} question(s) without ground truth: "
            f"{sorted(skipped)}.\nRun the ground-truth generator first:\n"
            f"  python {DEFAULT_GROUND_TRUTH.parent / 'generate_ground_truth.py'}",
            file=sys.stderr,
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Harbor task dataset from benchmark questions"
    )
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_GROUND_TRUTH)
    parser.add_argument("--tasks-dir", type=Path, default=DEFAULT_TASKS_DIR)
    parser.add_argument(
        "--ids",
        nargs="+",
        type=int,
        default=None,
        metavar="ID",
        help="Only build these question IDs",
    )
    parser.add_argument(
        "--generate-ground-truth",
        action="store_true",
        help="Run the ground-truth generator before building the dataset",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if args.generate_ground_truth:
        sys.path.insert(0, str(BENCHMARK_DIR / "ground_truth"))
        from generate_ground_truth import generate  # noqa: E402

        generate(
            questions_file=args.questions,
            output_dir=args.ground_truth,
            overwrite=False,
        )

    build(
        questions_path=args.questions,
        ground_truth_dir=args.ground_truth,
        tasks_dir=args.tasks_dir,
        question_ids=args.ids,
    )

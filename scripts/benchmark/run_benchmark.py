"""Main benchmark orchestrator.

Runs the full pipeline:
  1. (optional) Generate ground truth
  2. Run Sonnet 4.6 agent on benchmark questions
  3. Judge answers with Haiku 4.5
  4. Write summary statistics

Usage examples:

  # Full run (all 145 questions, new timestamped run directory):
  python scripts/benchmark/run_benchmark.py

  # Quick smoke-test on 3 easy questions:
  python scripts/benchmark/run_benchmark.py --ids 2 3 31

  # Re-use existing agent answers, only re-judge:
  python scripts/benchmark/run_benchmark.py --skip-agent --run-id my-run-id

  # Generate ground truth only:
  python scripts/benchmark/run_benchmark.py --ground-truth-only

  # Specify a named run directory:
  python scripts/benchmark/run_benchmark.py --run-id experiment-1
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BENCHMARK_DIR = Path(__file__).parent
sys.path.insert(0, str(BENCHMARK_DIR))

import config  # noqa: E402


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------

_CRITERIA = ("factual_accuracy", "completeness", "relevance", "clarity", "data_match")


def _compute_summary(
    questions: list[dict],
    agent_answers: list[dict],
    judge_scores: list[dict],
) -> dict:
    question_by_id = {q["id"]: q for q in questions}
    agent_by_id = {a["id"]: a for a in agent_answers}
    score_by_id = {s["id"]: s for s in judge_scores}

    all_ids = sorted(question_by_id.keys())

    # Per-question rows
    rows = []
    for q_id in all_ids:
        q = question_by_id[q_id]
        agent = agent_by_id.get(q_id, {})
        scored = score_by_id.get(q_id, {})
        rows.append(
            {
                "id": q_id,
                "complexity": q.get("complexity", ""),
                "query_type": q.get("query_type", ""),
                "ambiguous": q.get("ambiguous", False),
                "agent_elapsed_s": agent.get("elapsed_seconds"),
                "agent_error": agent.get("error"),
                "tool_call_count": len(agent.get("tool_calls", [])),
                "overall_score": scored.get("overall"),
                "judge_error": scored.get("error"),
                "criteria_scores": {
                    k: scored.get("scores", {}).get(k, {}).get("score")
                    for k in _CRITERIA
                },
            }
        )

    # Aggregate: overall
    scored_rows = [r for r in rows if r["overall_score"] is not None]
    overall_mean = (
        round(sum(r["overall_score"] for r in scored_rows) / len(scored_rows), 3)
        if scored_rows
        else None
    )

    # Aggregate: per criterion
    criteria_means = {}
    for crit in _CRITERIA:
        vals = [
            r["criteria_scores"][crit]
            for r in rows
            if r["criteria_scores"].get(crit) is not None
        ]
        criteria_means[crit] = round(sum(vals) / len(vals), 3) if vals else None

    # Aggregate: by complexity
    by_complexity: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        if r["overall_score"] is not None:
            by_complexity[r["complexity"]].append(r["overall_score"])
    complexity_means = {
        k: round(sum(v) / len(v), 3) for k, v in sorted(by_complexity.items())
    }

    # Aggregate: by query_type
    by_type: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        if r["overall_score"] is not None:
            by_type[r["query_type"]].append(r["overall_score"])
    type_means = {
        k: round(sum(v) / len(v), 3) for k, v in sorted(by_type.items())
    }

    # Tool call stats
    tool_counts = [r["tool_call_count"] for r in rows if r["agent_error"] is None]
    tool_stats = (
        {
            "mean": round(sum(tool_counts) / len(tool_counts), 2),
            "min": min(tool_counts),
            "max": max(tool_counts),
        }
        if tool_counts
        else {}
    )

    # Error rates
    agent_errors = sum(1 for r in rows if r["agent_error"])
    judge_errors = sum(1 for r in rows if r["judge_error"])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sonnet_model_id": config.SONNET_MODEL_ID,
        "haiku_model_id": config.HAIKU_MODEL_ID,
        "total_questions": len(all_ids),
        "scored_questions": len(scored_rows),
        "agent_errors": agent_errors,
        "judge_errors": judge_errors,
        "overall_mean_score": overall_mean,
        "criteria_means": criteria_means,
        "by_complexity": complexity_means,
        "by_query_type": type_means,
        "tool_call_stats": tool_stats,
        "per_question": rows,
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run(
    run_id: str | None = None,
    question_ids: list[int] | None = None,
    skip_agent: bool = False,
    skip_judge: bool = False,
    ground_truth_only: bool = False,
    overwrite_ground_truth: bool = False,
    no_skip_existing: bool = False,
    questions_path: Path | None = None,
) -> None:
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    run_dir = config.RESULTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    questions_path = questions_path or config.QUESTIONS_FILE
    ground_truth_dir = config.GROUND_TRUTH_DIR
    agent_answers_path = run_dir / "agent_answers.json"
    judge_scores_path = run_dir / "judge_scores.json"
    summary_path = run_dir / "summary.json"

    with open(questions_path, encoding="utf-8") as fh:
        all_questions: list[dict] = json.load(fh)

    if question_ids:
        id_set = set(question_ids)
        all_questions = [q for q in all_questions if q["id"] in id_set]
        print(f"Running subset: {len(all_questions)} questions (ids={sorted(id_set)})", file=sys.stderr)

    # ── Step 0: Ground truth ─────────────────────────────────────────────────
    print("\n=== Step 0: Ground Truth ===", file=sys.stderr)
    from ground_truth.generate_ground_truth import generate  # noqa: E402

    generate(
        questions_file=questions_path,
        output_dir=ground_truth_dir,
        overwrite=overwrite_ground_truth,
    )

    if ground_truth_only:
        print("Done (ground-truth-only mode).", file=sys.stderr)
        return

    # ── Step 1: Agent runner ──────────────────────────────────────────────────
    agent_answers: list[dict] = []

    if skip_agent:
        if agent_answers_path.exists():
            with open(agent_answers_path, encoding="utf-8") as fh:
                agent_answers = json.load(fh)
            print(f"\n=== Step 1: Agent (skipped — loaded {len(agent_answers)} from disk) ===", file=sys.stderr)
        else:
            print(
                f"\nERROR: --skip-agent requested but {agent_answers_path} does not exist.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print("\n=== Step 1: Agent ===", file=sys.stderr)
        from agent_runner import run_agent  # noqa: E402

        agent_answers = run_agent(
            questions=all_questions,
            output_path=agent_answers_path,
            skip_existing=not no_skip_existing,
        )

    # ── Step 2: Judge ─────────────────────────────────────────────────────────
    judge_scores: list[dict] = []

    if skip_judge:
        if judge_scores_path.exists():
            with open(judge_scores_path, encoding="utf-8") as fh:
                judge_scores = json.load(fh)
            print(f"\n=== Step 2: Judge (skipped — loaded {len(judge_scores)} from disk) ===", file=sys.stderr)
        else:
            print(
                f"\nERROR: --skip-judge requested but {judge_scores_path} does not exist.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print("\n=== Step 2: Judge ===", file=sys.stderr)
        from judge import judge as run_judge  # noqa: E402

        judge_scores = run_judge(
            agent_answers_path=agent_answers_path,
            ground_truth_dir=ground_truth_dir,
            questions_path=questions_path,
            output_path=judge_scores_path,
            skip_existing=not no_skip_existing,
        )

    # ── Step 3: Summary ───────────────────────────────────────────────────────
    print("\n=== Step 3: Summary ===", file=sys.stderr)
    summary = _compute_summary(all_questions, agent_answers, judge_scores)

    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    # Print top-level stats to stdout.
    print(f"\nRun ID          : {run_id}")
    print(f"Questions scored: {summary['scored_questions']} / {summary['total_questions']}")
    print(f"Agent errors    : {summary['agent_errors']}")
    print(f"Judge errors    : {summary['judge_errors']}")
    print(f"Overall mean    : {summary['overall_mean_score']}")
    print(f"\nBy complexity   : {summary['by_complexity']}")
    print(f"By query type   : {summary['by_query_type']}")
    print(f"\nCriteria means  :")
    for crit, val in summary["criteria_means"].items():
        print(f"  {crit:<20}: {val}")
    print(f"\nResults written to {run_dir}/")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the aind-data-mcp benchmark end-to-end")
    parser.add_argument(
        "--run-id",
        default=None,
        help="Name for the results sub-directory (default: UTC timestamp)",
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        type=int,
        default=None,
        metavar="ID",
        help="Only run these question IDs",
    )
    parser.add_argument(
        "--skip-agent",
        action="store_true",
        help="Skip agent step and re-use existing agent_answers.json from the run directory",
    )
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="Skip judge step and re-use existing judge_scores.json from the run directory",
    )
    parser.add_argument(
        "--ground-truth-only",
        action="store_true",
        help="Only (re-)generate ground truth files and exit",
    )
    parser.add_argument(
        "--overwrite-ground-truth",
        action="store_true",
        help="Re-fetch ground truth even if raw files already exist",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Re-run all steps even if partial results already exist",
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=None,
        help="Path to questions.json (default: questions/questions.json)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(
        run_id=args.run_id,
        question_ids=args.ids,
        skip_agent=args.skip_agent,
        skip_judge=args.skip_judge,
        ground_truth_only=args.ground_truth_only,
        overwrite_ground_truth=args.overwrite_ground_truth,
        no_skip_existing=args.no_skip,
        questions_path=args.questions,
    )

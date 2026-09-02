"""Locally exercise a task's verifier (LLM judge) without the Harbor harness.

This runs the same `tests/llm_judge.py` a task uses, but against a temporary
workspace on your machine, so you can confirm the verifier writes a valid
`reward.json` before spending time on a full `harbor run`.

Examples::

    # Judge a canned answer against task aind-q001's ground truth
    python scripts/benchmark/harbor/check_verifier.py --id 1 \
        --answer "The instrument was SmartSPIM1-7."

    # Read the answer from a file
    python scripts/benchmark/harbor/check_verifier.py --id 1 --answer-file /tmp/a.txt

    # Skip the LLM call entirely and just verify the plumbing writes a reward
    # file (uses a dummy judge model that always errors -> zero reward):
    python scripts/benchmark/harbor/check_verifier.py --id 1 --answer "x" --dry-run

The judge model and credentials come from the same env vars Harbor uses
(`JUDGE_MODEL`, `ANTHROPIC_API_KEY`, `AWS_BEARER_TOKEN_BEDROCK`, ...).
"""

from __future__ import annotations

import argparse
import json
import os
import runpy
import sys
import tempfile
from pathlib import Path

HARBOR_DIR = Path(__file__).parent
DEFAULT_TASKS_DIR = HARBOR_DIR / "tasks"


def _resolve_task_dir(task_id: int | None, task_dir: Path | None) -> Path:
    if task_dir is not None:
        return task_dir
    if task_id is not None:
        return DEFAULT_TASKS_DIR / f"aind-q{task_id:03d}"
    raise SystemExit("Provide --id or --task-dir")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--id", type=int, help="Question id (e.g. 1 -> aind-q001)"
    )
    group.add_argument(
        "--task-dir", type=Path, help="Path to a task directory"
    )

    ans = parser.add_mutually_exclusive_group()
    ans.add_argument("--answer", help="Answer text to grade")
    ans.add_argument(
        "--answer-file", type=Path, help="File containing the answer"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force the judge model to a bogus id so no real LLM call is made; "
        "just checks that a reward.json is produced.",
    )
    args = parser.parse_args()

    task_dir = _resolve_task_dir(args.id, args.task_dir)
    llm_script = task_dir / "tests" / "llm_judge.py"
    det_script = task_dir / "tests" / "verify_answer.py"
    if det_script.exists():
        judge_script = det_script
        gt_file = task_dir / "tests" / "expected.json"
        gt_env = "EXPECTED_PATH"
        deterministic = True
    elif llm_script.exists():
        judge_script = llm_script
        gt_file = task_dir / "tests" / "ground_truth.json"
        gt_env = "GROUND_TRUTH_PATH"
        deterministic = False
    else:
        raise SystemExit(
            f"Task not found or not generated: {task_dir}\n"
            "Run build_dataset.py first."
        )
    if not gt_file.exists():
        raise SystemExit(
            f"Missing {gt_file.name} in {task_dir}. Run build_dataset.py."
        )

    # Resolve the answer text.
    if args.answer_file:
        answer_text = args.answer_file.read_text()
    elif args.answer is not None:
        answer_text = args.answer
    else:
        answer_text = "(placeholder answer for verifier plumbing check)"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        answer_path = tmp_path / "answer.txt"
        reward_path = tmp_path / "reward.json"
        answer_path.write_text(answer_text)

        env_overrides = {
            "ANSWER_PATH": str(answer_path),
            gt_env: str(gt_file),
            "REWARD_PATH": str(reward_path),
        }
        if args.dry_run and not deterministic:
            env_overrides["JUDGE_MODEL"] = "dry-run/nonexistent-model"

        old = {k: os.environ.get(k) for k in env_overrides}
        os.environ.update(env_overrides)
        try:
            # Execute the exact judge script the task ships with.
            runpy.run_path(str(judge_script), run_name="__main__")
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        if not reward_path.exists():
            print(
                "FAIL: verifier did not write a reward file", file=sys.stderr
            )
            return 1

        reward = json.loads(reward_path.read_text())
        print("\n--- reward.json ---")
        print(json.dumps(reward, indent=2))
        if "error" in reward:
            print(
                f"\nNote: judge reported an error: {reward['error']}",
                file=sys.stderr,
            )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

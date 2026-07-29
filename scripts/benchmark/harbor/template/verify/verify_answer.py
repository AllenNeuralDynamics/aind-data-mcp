"""Deterministic verifier for the aind-data-mcp Harbor benchmark.

Used for questions whose answer is a specific set of facts (identifiers, names,
counts) that can be checked exactly — no LLM judge required. Reads the agent's
answer from ``/app/answer.txt`` and the expected facts from
``/tests/expected.json`` (baked in at task-generation time), then writes
``/logs/verifier/reward.json``.

Stdlib only: no litellm, no boto3, no network, no pip install — so it is immune
to the PEP 668 / offline-verifier issues that affect the LLM judge.

expected.json schema::

    {
      "id": 1,
      "question": "...",
      "must_include": ["SmartSPIM1-7", ...],   # candidate facts to look for
      "min_matches": 1                          # how many must appear (default: all)
    }

Matching is case-insensitive and comma/whitespace-insensitive (so "11,585"
matches "11585" and multi-space differences don't matter).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

ANSWER_PATH = Path(os.environ.get("ANSWER_PATH", "/app/answer.txt"))
EXPECTED_PATH = Path(os.environ.get("EXPECTED_PATH", "/tests/expected.json"))
REWARD_PATH = Path(os.environ.get("REWARD_PATH", "/logs/verifier/reward.json"))


def _normalize(text: str) -> str:
    text = text.lower()
    text = text.replace(",", "")          # 11,585 -> 11585
    text = re.sub(r"\s+", " ", text)      # collapse whitespace
    return text


def _write_reward(metrics: dict) -> None:
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REWARD_PATH.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


def main() -> None:
    try:
        spec = json.loads(EXPECTED_PATH.read_text())
    except Exception as exc:  # noqa: BLE001 - always emit a reward file
        _write_reward({"overall": 0.0, "error": f"expected.json read failed: {exc}"})
        return

    must_include = spec.get("must_include", [])
    min_matches = spec.get("min_matches") or len(must_include)

    answer = ANSWER_PATH.read_text() if ANSWER_PATH.exists() else ""
    norm_answer = _normalize(answer)

    matched = [t for t in must_include if _normalize(str(t)) in norm_answer]
    missing = [t for t in must_include if t not in matched]

    passed = len(matched) >= min_matches
    _write_reward(
        {
            "overall": 1.0 if passed else 0.0,
            "matched": matched,
            "missing": missing,
            "required": min_matches,
            "found": len(matched),
        }
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - never exit without a reward file
        _write_reward({"overall": 0.0, "error": f"unexpected: {exc}"})

"""LLM judge verifier for the aind-data-mcp Harbor benchmark.

Runs inside the Harbor verifier container after the agent finishes. It:

  1. Reads the agent's answer from ``/app/answer.txt``.
  2. Reads the raw ground-truth database records from ``/tests/ground_truth.json``
     (baked into the task at generation time).
  3. Asks an LLM judge to score the answer on four criteria (1-5 each).
  4. Writes ``/logs/verifier/reward.json`` with per-criterion scores plus an
     ``overall`` metric (normalised to 0-1, which is Harbor's reward
     convention).

The scoring rubric mirrors the original standalone benchmark judge so results
stay comparable across the migration.

Configuration (via ``[verifier.env]`` in ``task.toml``):
  JUDGE_MODEL      litellm model id for the judge (default:
                   ``bedrock/us.anthropic.claude-sonnet-5``).
  ANTHROPIC_API_KEY / OPENAI_API_KEY / AWS_* credentials as required by the
                   chosen model.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

# Paths default to the in-container Harbor locations but can be overridden via
# environment variables so the verifier can be exercised locally (e.g. by
# check_verifier.py) without a running Harbor harness.
ANSWER_PATH = Path(os.environ.get("ANSWER_PATH", "/app/answer.txt"))
GROUND_TRUTH_PATH = Path(
    os.environ.get("GROUND_TRUTH_PATH", "/tests/ground_truth.json")
)
REWARD_PATH = Path(os.environ.get("REWARD_PATH", "/logs/verifier/reward.json"))

MAX_JUDGE_RAW_RECORDS = 500
MAX_JUDGE_TOKENS = 4096
MAX_JUDGE_ATTEMPTS = 2
CRITERIA = ("factual_accuracy", "completeness", "relevance", "clarity")

# The judge system prompt lives in a sibling file so it can be edited without
# touching this script. It is copied alongside llm_judge.py into each task.
SYSTEM_PROMPT_PATH = Path(
    os.environ.get(
        "SYSTEM_PROMPT_PATH", Path(__file__).parent / "system_prompt.txt"
    )
)
SYSTEM_PROMPT = SYSTEM_PROMPT_PATH.read_text()


def _build_user_prompt(
    question: str, answer: str | None, records: list | None
) -> str:
    parts = [
        f"## Question\n{question}",
        f"## Agent Answer\n{answer or '(no answer -- the agent did not write /app/answer.txt)'}",
    ]
    if records:
        truncated = records[:MAX_JUDGE_RAW_RECORDS]
        note = (
            f" (showing {len(truncated)} of {len(records)})"
            if len(records) > len(truncated)
            else ""
        )
        parts.append(
            f"## Raw Database Records (authoritative ground truth){note}\n"
            + json.dumps(truncated, separators=(",", ":"), default=str)
        )
    else:
        parts.append(
            "## Raw Database Records\n(none available -- query returned zero "
            "records or errored)"
        )
    return "\n\n".join(parts)


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = (
            stripped.split("\n", 1)[1] if "\n" in stripped else stripped[3:]
        )
        stripped = stripped.rsplit("```", 1)[0]
    return stripped.strip()


def _parse_scores(raw_text: str) -> dict:
    cleaned = _strip_markdown_fence(raw_text)
    if not cleaned:
        raise ValueError("judge returned empty content")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pattern = (
            r'"(factual_accuracy|completeness|relevance|clarity)"\s*:'
            r'\s*\{\s*"score"\s*:\s*([1-5])'
        )
        matches = dict(
            (key, int(score)) for key, score in re.findall(pattern, cleaned)
        )
        if set(matches) != set(CRITERIA):
            raise ValueError("judge response did not contain all score criteria")
        return {key: {"score": score} for key, score in matches.items()}


def _response_text(response) -> str:
    """Extract text from both string and structured provider responses."""
    message = response["choices"][0]["message"]
    if isinstance(message, dict):
        content = message.get("content")
        if not content:
            content = message.get("reasoning_content")
    else:
        content = getattr(message, "content", None)
        if not content:
            content = getattr(message, "reasoning_content", None)

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text") or block.get("output_text")
            else:
                text = getattr(block, "text", None) or getattr(
                    block, "output_text", None
                )
            if text:
                text_parts.append(text)
        return "".join(text_parts)
    return "" if content is None else str(content)


def _request_scores(litellm, model: str, prompt: str) -> dict:
    last_error = None
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    for attempt in range(MAX_JUDGE_ATTEMPTS):
        if attempt:
            messages.append(
                {
                    "role": "user",
                    "content": "Return only the required JSON object.",
                }
            )
        response = litellm.completion(
            model=model,
            messages=messages,
            max_tokens=MAX_JUDGE_TOKENS,
        )
        try:
            return _parse_scores(_response_text(response))
        except (
            TypeError,
            ValueError,
            KeyError,
            IndexError,
            json.JSONDecodeError,
        ) as exc:
            last_error = exc
    raise last_error or ValueError("judge returned no response")


def _write_reward(metrics: dict) -> None:
    numeric_metrics = {
        key: value
        for key, value in metrics.items()
        if isinstance(value, (float, int)) and not isinstance(value, bool)
    }
    numeric_metrics["reward"] = numeric_metrics.get("overall", 0.0)
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REWARD_PATH.write_text(json.dumps(numeric_metrics, indent=2))
    print(json.dumps(metrics, indent=2))


def main() -> None:
    try:
        gt = json.loads(GROUND_TRUTH_PATH.read_text())
    except Exception as exc:  # noqa: BLE001 - always emit a reward file
        print(f"ERROR: could not read ground truth: {exc}")
        _write_reward(
            {"overall": 0.0, "error": f"ground_truth read failed: {exc}"}
        )
        return
    question = gt.get("question", "")
    records = gt.get("records") or None

    answer = ANSWER_PATH.read_text().strip() if ANSWER_PATH.exists() else None

    model = os.environ.get(
        "JUDGE_MODEL", "bedrock/us.anthropic.claude-sonnet-5"
    )
    prompt = _build_user_prompt(question, answer, records)

    try:
        import litellm

        scores = _request_scores(litellm, model, prompt)
    except Exception as exc:  # noqa: BLE001 - judge failure => zero reward
        print(f"ERROR: judge failed: {exc}")
        _write_reward({"overall": 0.0, "error": str(exc)})
        return

    values = []
    metrics: dict[str, float] = {}
    for key in CRITERIA:
        entry = scores.get(key)
        if not isinstance(entry, dict) or "score" not in entry:
            _write_reward(
                {"overall": 0.0, "error": f"missing criterion '{key}'"}
            )
            return
        score = float(entry["score"])
        # Normalise each 1-5 criterion to Harbor's 0-1 reward convention.
        metrics[key] = round((score - 1) / 4, 4)
        values.append(score)

    overall_1_5 = sum(values) / len(values)
    metrics["overall"] = round((overall_1_5 - 1) / 4, 4)
    _write_reward(metrics)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - never exit without a reward file
        print(f"ERROR: unexpected judge failure: {exc}")
        _write_reward({"overall": 0.0, "error": f"unexpected: {exc}"})

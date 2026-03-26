"""LLM judge — scores each agent answer using Claude Haiku 4.5 via Bedrock.

The judge reads agent_answers.json and the ground_truth/raw/ files and
produces judge_scores.json.

Scoring criteria (each 1–5, 5 = best):

  factual_accuracy  — Key facts (counts, names, dates, values) match
                      the ground-truth data.
  completeness      — All relevant aspects of the question are addressed.
  relevance         — Answer is focused; no significant off-topic content.
  clarity           — Well-structured and appropriately formatted.
  data_match        — (Only when raw DB records are available and non-empty)
                      The agent's answer correctly reflects the actual DB
                      results (right numbers, listed items, etc.).

Output schema (one element of judge_scores.json):

    {
      "id": 1,
      "question": "...",
      "scores": {
        "factual_accuracy": {"score": 4, "reasoning": "..."},
        "completeness":     {"score": 5, "reasoning": "..."},
        "relevance":        {"score": 5, "reasoning": "..."},
        "clarity":          {"score": 4, "reasoning": "..."},
        "data_match":       {"score": 3, "reasoning": "..."}   // optional
      },
      "overall": 4.25,   // mean of present criteria scores
      "error": null
    }
"""

import json
import sys
import time
from pathlib import Path

import boto3

BENCHMARK_DIR = Path(__file__).parent
sys.path.insert(0, str(BENCHMARK_DIR))

import config  # noqa: E402

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert judge evaluating answers produced by an AI data assistant.
The data comes from the Allen Institute for Neural Dynamics (AIND) neuroscience
database.

You will be shown:
1. The original user question
2. The agent's answer to evaluate
3. An expected/reference answer written by a domain expert
4. (Optionally) a sample of the actual raw database records returned for this
   question — use this as the authoritative factual source

Score each applicable criterion from 1 (very poor) to 5 (excellent).
Be critical: only award 5 when the answer is essentially perfect for that
criterion.

Criteria:
  factual_accuracy : Do specific facts (counts, names, dates, values) in the
                     agent answer match the ground-truth data?
  completeness     : Does the answer address ALL relevant aspects of the
                     question without omitting important information?
  relevance        : Is the answer focused on what was asked?  Penalise
                     irrelevant tangents or excessive boilerplate.
  clarity          : Is the answer well-structured and appropriately formatted
                     (tables where useful, no walls of repetitive text)?
  data_match       : (Only when raw DB records are present) Does the answer
                     correctly reflect the actual database results — right
                     record counts, correct listed items, accurate values?

Return ONLY a valid JSON object with EXACTLY this structure (no markdown, no
extra keys, no commentary):

{
  "factual_accuracy": {"score": <1-5>, "reasoning": "<one sentence>"},
  "completeness":     {"score": <1-5>, "reasoning": "<one sentence>"},
  "relevance":        {"score": <1-5>, "reasoning": "<one sentence>"},
  "clarity":          {"score": <1-5>, "reasoning": "<one sentence>"},
  "data_match":       {"score": <1-5>, "reasoning": "<one sentence>"}
}

Omit the "data_match" key entirely when no raw DB records are provided.
"""


def _build_user_prompt(
    question: str,
    agent_answer: str | None,
    expected_answer: str,
    raw_records: list | None,
) -> str:
    parts = [
        f"## Question\n{question}",
        f"## Agent Answer\n{agent_answer or '(no answer — agent returned an error)'}",
        f"## Expected Answer (reference, written by a domain expert)\n{expected_answer or '(none provided)'}",
    ]
    if raw_records:
        truncated = raw_records[: config.MAX_JUDGE_RAW_RECORDS]
        note = f" (showing {len(truncated)} of {len(raw_records)})" if len(raw_records) > len(truncated) else ""
        parts.append(
            f"## Raw Database Records{note}\n"
            + json.dumps(truncated, indent=2, default=str)
        )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Bedrock Converse call
# ---------------------------------------------------------------------------

def _invoke_judge(
    prompt: str,
    bedrock_client,
) -> dict:
    response = bedrock_client.converse(
        modelId=config.HAIKU_MODEL_ID,
        system=[{"text": _SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={
            "maxTokens": 1024,
            "temperature": 0.0,
        },
    )
    raw_text: str = response["output"]["message"]["content"][0]["text"]
    return json.loads(raw_text)


def _overall_score(scores: dict) -> float:
    values = [v["score"] for v in scores.values() if isinstance(v, dict) and "score" in v]
    return round(sum(values) / len(values), 3) if values else 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def judge(
    agent_answers_path: Path,
    ground_truth_dir: Path,
    questions_path: Path,
    output_path: Path,
    skip_existing: bool = True,
) -> list[dict]:
    """Score agent answers and write judge_scores.json.

    Parameters
    ----------
    agent_answers_path:
        Path to agent_answers.json produced by agent_runner.py.
    ground_truth_dir:
        Directory containing raw/{id:03d}.json ground-truth files.
    questions_path:
        Path to questions.json (needed for expected_answer text).
    output_path:
        Where to write judge_scores.json.
    skip_existing:
        Skip question IDs that already appear in output_path.
    """
    with open(agent_answers_path, encoding="utf-8") as fh:
        agent_answers: list[dict] = json.load(fh)

    with open(questions_path, encoding="utf-8") as fh:
        questions_by_id: dict[int, dict] = {q["id"]: q for q in json.load(fh)}

    # Load previous judge scores for resume support.
    existing: dict[int, dict] = {}
    if skip_existing and output_path.exists():
        with open(output_path, encoding="utf-8") as fh:
            for item in json.load(fh):
                existing[item["id"]] = item
        print(f"Loaded {len(existing)} existing judge scores", file=sys.stderr)

    session = boto3.Session(profile_name=config.AWS_PROFILE, region_name=config.AWS_REGION)
    bedrock = session.client("bedrock-runtime")

    results: list[dict] = list(existing.values())
    existing_ids = set(existing.keys())
    pending = [a for a in agent_answers if a["id"] not in existing_ids]
    total = len(pending)

    for i, answer in enumerate(pending, 1):
        q_id = answer["id"]
        question_meta = questions_by_id.get(q_id, {})
        question_text = answer.get("question", question_meta.get("question", ""))
        expected = question_meta.get("expected_answer", "")

        # Load raw DB records (may not exist yet).
        raw_records = None
        gt_path = ground_truth_dir / f"{q_id:03d}.json"
        if gt_path.exists():
            with open(gt_path, encoding="utf-8") as fh:
                gt = json.load(fh)
            raw_records = gt.get("records") or None  # treat empty list as None

        print(
            f"[{i}/{total}] judging #{q_id} [{question_meta.get('complexity', '?')}] …",
            end="",
            file=sys.stderr,
        )

        stub: dict = {
            "id": q_id,
            "question": question_text,
            "scores": {},
            "overall": 0.0,
            "error": None,
        }

        if answer.get("error"):
            stub["error"] = f"agent_error: {answer['error']}"
            print(" skipped (agent error)", file=sys.stderr)
            results.append(stub)
            _persist(results, output_path)
            continue

        prompt = _build_user_prompt(
            question=question_text,
            agent_answer=answer.get("agent_answer"),
            expected_answer=expected,
            raw_records=raw_records,
        )

        try:
            scores = _invoke_judge(prompt, bedrock)
            # Validate structure minimally.
            for key in ("factual_accuracy", "completeness", "relevance", "clarity"):
                if key not in scores:
                    raise ValueError(f"Missing criterion '{key}' in judge response")
            stub["scores"] = scores
            stub["overall"] = _overall_score(scores)
            print(f" overall={stub['overall']}", file=sys.stderr)
        except Exception as exc:
            stub["error"] = str(exc)
            print(f" ERROR: {exc}", file=sys.stderr)
            # Back off briefly to avoid hammering Bedrock on repeated failures.
            time.sleep(2)

        results.append(stub)
        _persist(results, output_path)

    return results


def _persist(results: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Judge agent answers with Haiku 4.5")
    parser.add_argument("--answers", type=Path, required=True, help="agent_answers.json")
    parser.add_argument("--ground-truth", type=Path, default=None)
    parser.add_argument("--questions", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True, help="judge_scores.json")
    parser.add_argument("--no-skip", action="store_true")
    args = parser.parse_args()

    judge(
        agent_answers_path=args.answers,
        ground_truth_dir=args.ground_truth or (BENCHMARK_DIR / "ground_truth" / "raw"),
        questions_path=args.questions or (BENCHMARK_DIR / "questions" / "questions.json"),
        output_path=args.output,
        skip_existing=not args.no_skip,
    )

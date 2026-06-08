"""Agent runner - Sonnet 4.6 agent via strands-agents + aind-data-mcp MCP server."""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path

import boto3
from mcp.client.stdio import StdioServerParameters, stdio_client

BENCHMARK_DIR = Path(__file__).parent
sys.path.insert(0, str(BENCHMARK_DIR))

import config  # noqa: E402

# ---------------------------------------------------------------------------
# Import strands once at startup — fail fast if not installed.
# ---------------------------------------------------------------------------

try:
    from strands import Agent
    from strands.models import BedrockModel
    from strands.tools.mcp import MCPClient
except ImportError as _exc:
    print(
        "strands-agents is required.\n"
        "Install: pip install 'aind-data-mcp[benchmark]'\n"
        f"Error: {_exc}",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_tool_calls(messages: list[dict]) -> list[dict]:
    tool_calls = []
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        for block in msg.get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_calls.append(
                    {
                        "tool_name": block.get("name"),
                        "input_keys": sorted(block.get("input", {}).keys()),
                    }
                )
    return tool_calls


def _extract_usage(response) -> dict:
    """Extract token counts from a strands AgentResult, if available."""
    try:
        metrics = getattr(response, "metrics", None)
        if metrics is None:
            return {}
        accumulated = getattr(metrics, "accumulated_usage", None)
        if not accumulated:
            return {}
        if isinstance(accumulated, dict):
            return {
                "input_tokens": accumulated.get("inputTokens"),
                "output_tokens": accumulated.get("outputTokens"),
            }
    except Exception:
        pass
    return {}


def _run_one(question: dict, model) -> dict:
    start = time.monotonic()
    try:
        params = StdioServerParameters(command=config.MCP_COMMAND, args=[])
        mcp_client = MCPClient(lambda: stdio_client(params))
        with mcp_client:
            tools = mcp_client.list_tools_sync()
            agent = Agent(model=model, tools=tools)
            response = agent(question["question"])
            answer_text = str(response)
            tool_calls = _extract_tool_calls(getattr(agent, "messages", []))
            usage = _extract_usage(response)
            error = None
    except Exception as exc:
        answer_text = None
        tool_calls = []
        usage = {}
        error = str(exc)
    return {
        "id": question["id"],
        "question": question["question"],
        "agent_answer": answer_text,
        "tool_calls": tool_calls,
        "elapsed_seconds": round(time.monotonic() - start, 2),
        "usage": usage,
        "error": error,
    }


def _run_one_with_timeout(question: dict, model) -> dict:
    """Run the agent for one question, enforcing AGENT_TIMEOUT_SECONDS."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run_one, question, model)
        try:
            return future.result(timeout=config.AGENT_TIMEOUT_SECONDS)
        except FuturesTimeout:
            return {
                "id": question["id"],
                "question": question["question"],
                "agent_answer": None,
                "tool_calls": [],
                "elapsed_seconds": config.AGENT_TIMEOUT_SECONDS,
                "usage": {},
                "error": f"Timed out after {config.AGENT_TIMEOUT_SECONDS}s",
            }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_agent(
    questions: list[dict],
    output_path: Path,
    skip_existing: bool = True,
) -> list[dict]:
    existing: dict[int, dict] = {}
    if skip_existing and output_path.exists():
        with open(output_path, encoding="utf-8") as fh:
            for item in json.load(fh):
                existing[item["id"]] = item
        print(f"Loaded {len(existing)} existing results from {output_path}", file=sys.stderr)

    session = boto3.Session(profile_name=config.AWS_PROFILE, region_name=config.AWS_REGION)
    model = BedrockModel(model_id=config.SONNET_MODEL_ID, boto_session=session)

    results: list[dict] = list(existing.values())
    existing_ids = set(existing.keys())
    pending = [q for q in questions if q["id"] not in existing_ids]
    total = len(pending)

    cumulative_elapsed = 0.0
    total_input_tokens = 0
    total_output_tokens = 0

    for i, question in enumerate(pending, 1):
        eta_str = ""
        if i > 1 and cumulative_elapsed > 0:
            avg_s = cumulative_elapsed / (i - 1)
            remaining_s = avg_s * (total - i + 1)
            eta_str = f"  ETA ~{remaining_s / 60:.1f}min"

        print(
            f"[{i}/{total}] #{question['id']} [{question.get('complexity', '?')}] "
            f"{question['question'][:70]}...{eta_str}",
            file=sys.stderr,
        )

        result = _run_one_with_timeout(question, model)

        elapsed = result["elapsed_seconds"]
        cumulative_elapsed += elapsed

        usage = result.get("usage", {})
        if usage.get("input_tokens"):
            total_input_tokens += usage["input_tokens"]
        if usage.get("output_tokens"):
            total_output_tokens += usage["output_tokens"]

        if result["error"]:
            status = f"error={result['error'][:80]}"
        else:
            token_str = ""
            if usage.get("input_tokens") or usage.get("output_tokens"):
                token_str = (
                    f"  in={usage.get('input_tokens', '?')} "
                    f"out={usage.get('output_tokens', '?')} tokens"
                )
            status = f"{elapsed}s{token_str}"
        print(f"         -> {status}", file=sys.stderr)

        results.append(result)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)

    # Print token totals if we collected any.
    if total_input_tokens or total_output_tokens:
        cost = (
            total_input_tokens / 1000 * config.SONNET_INPUT_COST_PER_1K
            + total_output_tokens / 1000 * config.SONNET_OUTPUT_COST_PER_1K
        )
        print(
            f"\nAgent tokens  : {total_input_tokens} in / {total_output_tokens} out"
            f"  (~${cost:.4f})",
            file=sys.stderr,
        )

    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Sonnet agent on benchmark questions")
    parser.add_argument("--questions", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--no-skip", action="store_true")
    parser.add_argument("--ids", nargs="+", type=int, default=None)
    args = parser.parse_args()

    questions_file = args.questions or (BENCHMARK_DIR / "questions" / "questions.json")
    output_file = args.output or (BENCHMARK_DIR / "results" / "latest" / "agent_answers.json")

    with open(questions_file, encoding="utf-8") as fh:
        all_questions = json.load(fh)

    if args.ids:
        all_questions = [q for q in all_questions if q["id"] in set(args.ids)]

    run_agent(all_questions, output_file, skip_existing=not args.no_skip)

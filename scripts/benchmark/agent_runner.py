"""Agent runner - Sonnet 4.6 agent via strands-agents + aind-data-mcp MCP server."""

import json
import sys
import time
from pathlib import Path

import boto3
from mcp.client.stdio import StdioServerParameters, stdio_client

BENCHMARK_DIR = Path(__file__).parent
sys.path.insert(0, str(BENCHMARK_DIR))

import config  # noqa: E402


def _import_strands():
    try:
        from strands import Agent
        from strands.models import BedrockModel
        from strands.tools.mcp import MCPClient
        return Agent, BedrockModel, MCPClient
    except ImportError as exc:
        print(
            "strands-agents is required.\n"
            "Install: pip install 'aind-data-mcp[benchmark]'\n"
            f"Error: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)


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


def _run_one(question: dict, model) -> dict:
    Agent, _, MCPClient = _import_strands()
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
            error = None
    except Exception as exc:
        answer_text = None
        tool_calls = []
        error = str(exc)
    return {
        "id": question["id"],
        "question": question["question"],
        "agent_answer": answer_text,
        "tool_calls": tool_calls,
        "elapsed_seconds": round(time.monotonic() - start, 2),
        "error": error,
    }


def run_agent(
    questions: list[dict],
    output_path: Path,
    skip_existing: bool = True,
) -> list[dict]:
    Agent, BedrockModel, MCPClient = _import_strands()  # noqa: F841

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

    for i, question in enumerate(pending, 1):
        print(
            f"[{i}/{total}] #{question['id']} [{question.get('complexity', '?')}] "
            f"{question['question'][:70]}...",
            file=sys.stderr,
        )
        result = _run_one(question, model)
        status = f"error={result['error']}" if result["error"] else f"{result['elapsed_seconds']}s"
        print(f"         -> {status}", file=sys.stderr)

        results.append(result)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)

    return results


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

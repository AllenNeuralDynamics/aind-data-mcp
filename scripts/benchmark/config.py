"""Benchmark configuration constants."""

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BENCHMARK_DIR = Path(__file__).parent
QUESTIONS_FILE = BENCHMARK_DIR / "questions" / "questions.json"
GROUND_TRUTH_DIR = BENCHMARK_DIR / "ground_truth" / "raw"
RESULTS_DIR = BENCHMARK_DIR / "results"

# ── AWS / Bedrock ─────────────────────────────────────────────────────────────
# Reads AWS_PROFILE and AWS_DEFAULT_REGION from the environment so whatever
# profile is active in the shell is used automatically.  Override here only
# if you need a fixed profile regardless of the environment.
AWS_PROFILE = os.environ.get("AWS_PROFILE")          # None → boto3 uses env/default chain
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")

# Bedrock model IDs.
# Cross-region inference prefixes (us.*) are used so Bedrock can route across
# availability zones.  Update these when new model versions are released.
SONNET_MODEL_ID = "us.anthropic.claude-sonnet-4-6"
HAIKU_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"    # Haiku 4.5

# ── MCP server ────────────────────────────────────────────────────────────────
# The entry-point script installed by `pip install -e .` in this repo.
MCP_COMMAND = "aind-data-mcp"

# ── Agent settings ────────────────────────────────────────────────────────────
# Maximum wall-clock seconds to wait for an agent response per question.
AGENT_TIMEOUT_SECONDS = 180

# Maximum number of raw DB result records forwarded to the judge LLM.
# Keeps the judge prompt within a reasonable context window.
MAX_JUDGE_RAW_RECORDS = 10

#!/bin/bash
# Harbor verifier (deterministic) for the aind-data-mcp benchmark.
#
# Grades the agent's answer (/app/answer.txt) against a fixed set of expected
# facts (/tests/expected.json) with exact, case/format-insensitive string
# checks. No LLM, no network, no pip install — stdlib Python only.
set -uo pipefail

mkdir -p /logs/verifier

python3 /tests/verify_answer.py || echo "WARNING: verify_answer.py exited non-zero" >&2

if [ ! -f /logs/verifier/reward.json ]; then
    echo "ERROR: verifier produced no reward.json; emitting fallback zero reward" >&2
    echo '{"overall": 0.0, "error": "verifier produced no reward file"}' \
        > /logs/verifier/reward.json
fi

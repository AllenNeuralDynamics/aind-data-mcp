#!/bin/bash
# Harbor verifier for the aind-data-mcp benchmark.
#
# Grades the agent's answer (written to /app/answer.txt) against the raw
# ground-truth database records (baked into /tests/ground_truth.json) using an
# LLM judge, then writes /logs/verifier/reward.json.
set -uo pipefail

mkdir -p /logs/verifier

# litellm gives us a provider-agnostic client so the judge model can be an
# Anthropic or OpenAI model id depending on JUDGE_MODEL.
#
# The verifier container's system Python is often PEP 668 "externally managed"
# (Debian/Ubuntu), which refuses a plain `pip install`. Since this is a
# throwaway grading container, install with --break-system-packages. Fall back
# to a plain install for images that don't need the flag, and don't fail the
# whole verifier if the install has trouble.
if ! python3 -c "import litellm" 2>/dev/null; then
    pip install --quiet --no-cache-dir --break-system-packages litellm boto3 \
        || pip install --quiet --no-cache-dir litellm boto3 \
        || echo "WARNING: pip install of litellm/boto3 failed" >&2
fi

# Run the judge. It writes /logs/verifier/reward.json itself and is designed to
# always emit one, but guard against a hard crash (e.g. import failure) so the
# harness never sees a missing reward file (RewardFileNotFoundError).
python3 /tests/llm_judge.py || echo "WARNING: llm_judge.py exited non-zero" >&2

if [ ! -f /logs/verifier/reward.json ]; then
    echo "ERROR: judge did not write reward.json; emitting fallback zero reward" >&2
    echo '{"overall": 0.0, "error": "verifier produced no reward file"}' \
        > /logs/verifier/reward.json
fi

# AIND Data Harbor benchmark

This benchmark runs the 15 generated AIND metadata questions with agent
harnesses selected for each model. By default, the launcher runs Claude Sonnet
5 through Claude Code on Amazon Bedrock and GPT-5.6 Luna through the Codex CLI
using a ChatGPT account. Each task image installs the published `aind-data-mcp`
package, sets `BIODATA_CACHE_BACKEND=s3`, and exposes it to the agent over local
stdio.

## Setup

```bash
pip install -e ".[benchmark]"
aws sso login --profile aind_octo
```

## Run

The launcher exports fresh credentials from the AWS profile, checks the AWS
identity, then starts Harbor once for each default agent model. The Luna run
uses the local Codex login at `~/.codex/auth.json` (override with
`CODEX_AUTH_JSON_PATH`):

```bash
AWS_PROFILE=aind_octo ./scripts/benchmark/run_harbor.sh
```

If you use the local `switch` helper:

```bash
switch octo
./scripts/benchmark/run_harbor.sh
```

Set `HARBOR_CONCURRENCY=1` to debug one container at a time. The launcher also
accepts `HARBOR_AGENT_MODEL`, `JUDGE_MODEL`, and `HARBOR_TASKS_PATH` overrides.

## View results

Harbor writes runs under `jobs/`. Start the viewer in a second terminal:

```bash
.venv/bin/harbor view jobs --jobs --port 8080
open http://127.0.0.1:8080
```

Select a run and task to inspect the trajectory, agent log, verifier output, and
exceptions. The same files are available under:

```text
jobs/<run>/<task>/agent/claude-code.txt
jobs/<run>/<task>/agent/trajectory.json
jobs/<run>/<task>/trial.log
jobs/<run>/<task>/exception.txt
```

## Editing tasks

The tasks under `tasks/` are self-contained and checked in directly. To tweak a
task, edit its files in place, e.g. the LLM-judge prompt at
`tasks/<task>/tests/system_prompt.txt`.

New task images must include `ENV BIODATA_CACHE_BACKEND="s3"` in their
Dockerfile so cache-backed MCP tools use the S3 environment.

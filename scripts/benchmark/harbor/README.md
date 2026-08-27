# AIND Data Harbor benchmark

This benchmark runs the 15 generated AIND metadata questions with Claude Code
on Amazon Bedrock. The agent uses the hosted MCP server at
`https://metadata-portal.allenneuraldynamics.org/mcp/`.

## Setup

```bash
pip install -e ".[benchmark]"
aws sso login --profile aind_octo
```

## Run

The launcher exports fresh credentials from the AWS profile, checks the AWS
identity, and starts Harbor with Claude Sonnet 5:

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

The current task set can be rebuilt from the benchmark inputs with:

```bash
.venv/bin/python scripts/benchmark/harbor/build_dataset.py \
  --ids 1 3 5 7 8 10 12 13 14 16 17 18 21 22 23
```

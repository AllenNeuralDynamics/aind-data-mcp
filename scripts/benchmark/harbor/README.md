# aind-data-mcp Harbor benchmark

This directory contains the [Harbor](https://harborframework.com)-based harness
for the **aind-data-mcp** benchmark. Harbor is the standard container harness
for evaluating agents: each benchmark question is a self-contained Harbor
**task**, the agent reaches the **hosted** `aind-data-mcp` server over MCP at
`https://metadata-portal.allenneuraldynamics.org/mcp/`, and an LLM judge grades
the agent's answer against the authoritative database records.

## Layout

```
harbor/
├── build_dataset.py            # questions.json + ground truth → Harbor tasks
├── template/                   # shared task files copied into every task
│   ├── environment/
│   │   └── Dockerfile              # agent container ("main")
│   ├── verify/                     # deterministic verifier (no LLM)
│   │   ├── test.sh
│   │   └── verify_answer.py        # exact-match checks → reward.json
│   └── tests/                      # LLM-judge verifier
│       ├── test.sh                 # verifier entrypoint
│       └── llm_judge.py            # LLM judge → /logs/verifier/reward.json
└── tasks/                      # generated; one dir per question (git-ignored)
    └── aind-qNNN/
        ├── task.toml               # metadata (incl. verify_mode) + mcp_servers
        ├── instruction.md          # the question
        ├── environment/            # copied from template/
        └── tests/                  # verify/ OR tests/ depending on mode:
            ├── test.sh
            ├── verify_answer.py + expected.json   # deterministic, OR
            └── llm_judge.py    + ground_truth.json # llm judge
```

## How it maps to the old benchmark

| Old (standalone) | Harbor |
|---|---|
| `questions.json` entry | a task directory (`instruction.md` + `task.toml`) |
| `agent_runner.py` (strands + MCP) | Harbor agent + hosted `[[environment.mcp_servers]]` |
| `judge.py` (Bedrock Haiku) | `tests/llm_judge.py` verifier → `reward.json` |
| `run_benchmark.py` orchestration | `harbor run` |
| ground-truth `raw/*.json` | baked into each task's `tests/ground_truth.json` |

## Verification modes

Each question is graded one of two ways, chosen automatically from whether the
question carries a `verify` block in `questions.json`:

- **deterministic** (16/25) — the answer is a specific set of facts (an
  instrument id, names, a count, a fixed set of IDs). The task ships
  `tests/verify_answer.py` + `tests/expected.json` and does exact,
  case/comma-insensitive substring checks. **No LLM, no network, no pip** — fast
  and reproducible. `reward.json` is `1.0`/`0.0` plus matched/missing detail.
- **llm** (9/25) — open-ended "list every unique X" over hundreds of records, or
  fuzzy reasoning where substring matching is too brittle. The task ships
  `tests/llm_judge.py` + `tests/ground_truth.json` and grades with an LLM
  (see below).

A question opts into deterministic grading by adding, in `questions.json`:

```json
"verify": { "must_include": ["SmartSPIM1-7"], "min_matches": 1 }
```

`min_matches` is optional (defaults to "all of `must_include`"). Matching lowercases
and strips commas, so `11,585` matches `11585`. `task.toml` records the choice as
`metadata.verify_mode`. Deterministic tasks need no `[verifier.env]` credentials.

The LLM judge keeps the original four criteria (`factual_accuracy`,
`completeness`, `relevance`, `clarity`, each 1–5), normalised to 0–1 with an
`overall` metric.

## Setup

```bash
pip install -e ".[benchmark]"     # installs harbor + litellm
```

Harbor needs Docker. Because the MCP server is hosted (not a sidecar), tasks are
single-Dockerfile and also run on cloud sandbox providers, not just `--env
docker`. Two things need outbound network access:

- the agent must reach `metadata-portal.allenneuraldynamics.org` (the hosted MCP);
- the judge calls the LLM provider selected by `JUDGE_MODEL`.

On `public` network baselines (the default) this works out of the box. If you run
an agent under an `allowlist` policy, allow the MCP host with
`--allow-agent-host metadata-portal.allenneuraldynamics.org`.

## Build the dataset

Ground truth must exist first (`ground_truth/raw/{id:03d}.json`). Generate it
and build the tasks in one step:

```bash
python scripts/benchmark/harbor/build_dataset.py --generate-ground-truth
```

Or, if ground truth already exists:

```bash
python scripts/benchmark/harbor/build_dataset.py
python scripts/benchmark/harbor/build_dataset.py --ids 1 2 21   # subset
```

## Run

```bash
export ANTHROPIC_API_KEY=...        # for the agent's model and/or the judge

# single task
harbor run -p scripts/benchmark/harbor/tasks/aind-q001 \
    -a claude-code -m anthropic/claude-sonnet-4-5 --env docker

# the whole dataset
harbor run -p scripts/benchmark/harbor/tasks \
    -a claude-code -m anthropic/claude-sonnet-4-5 \
    --env docker --n-concurrent 4
```

Pick the judge model with `JUDGE_MODEL` (default `anthropic/claude-haiku-4-5`),
a [litellm](https://docs.litellm.ai/docs/providers) model id. See
`harbor run --help` for supported agents, providers, and output options.

## Checking the verifier without Harbor

`harbor run` builds a container, runs an agent, then runs the verifier — slow
when you only want to confirm the **judge** works and writes a valid reward
file. `check_verifier.py` runs a task's `tests/llm_judge.py` locally against a
canned answer, so you can debug the grading path in seconds:

```bash
# Plumbing only — forces a bogus model, so no LLM call / credentials needed.
# Confirms a reward.json is always produced (guards against RewardFileNotFoundError).
python scripts/benchmark/harbor/check_verifier.py --id 1 --answer "x" --dry-run

# Real judge run (uses JUDGE_MODEL + the same env vars Harbor passes the verifier)
export JUDGE_MODEL="anthropic/claude-haiku-4-5"   # or a bedrock/... id
python scripts/benchmark/harbor/check_verifier.py --id 1 \
    --answer "The instrument was SmartSPIM1-7."
# or:  --answer-file /path/to/answer.txt
```

It prints the resulting `reward.json`. For **deterministic** tasks this is
stdlib-only (no deps, no credentials). For **llm** tasks it needs `litellm`
installed locally (`pip install -e ".[benchmark]"`) and the judge credentials.

## Using Amazon Bedrock

Bedrock is supported for both the agent and the judge. The Bedrock **API key**
is the `AWS_BEARER_TOKEN_BEDROCK` environment variable (standard
`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` +
`AWS_REGION` also work).

```bash
export AWS_BEARER_TOKEN_BEDROCK=...        # your Bedrock API key
export AWS_REGION=us-west-2

# Judge via Bedrock: pick a bedrock/ model id (litellm routes it, using the
# token above). The generated task.toml already forwards AWS_* into the verifier.
export JUDGE_MODEL="bedrock/us.anthropic.claude-haiku-4-5-20251001-v1:0"

harbor run -p scripts/benchmark/harbor/tasks \
    -a claude-code \
    -m bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
    --ae AWS_BEARER_TOKEN_BEDROCK=$AWS_BEARER_TOKEN_BEDROCK \
    --ae AWS_REGION=$AWS_REGION \
    --env docker --n-concurrent 4
```

Notes:
- `claude-code` auto-detects Bedrock mode when `AWS_BEARER_TOKEN_BEDROCK` (or
  `CLAUDE_CODE_USE_BEDROCK=1`) is set and forwards the token + region. litellm-based
  agents (e.g. `terminus-2`) just take a `bedrock/...` `-m` model.
- `--ae KEY=VALUE` forwards an env var to the **agent** container. Harbor requires
  the full `KEY=VALUE` form (it does not forward a bare `KEY` by name), so expand
  the value yourself: `--ae AWS_BEARER_TOKEN_BEDROCK=$AWS_BEARER_TOKEN_BEDROCK`. The
  judge already receives the AWS vars through the task's `[verifier.env]`.
- The hosted `aind-data-mcp` server needs no credentials from you — the agent just
  needs network access to `metadata-portal.allenneuraldynamics.org`.

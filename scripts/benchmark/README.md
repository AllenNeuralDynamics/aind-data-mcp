# aind-data-mcp Benchmark

End-to-end benchmark that evaluates the **aind-data-mcp** MCP server by having
an agent answer neuroscience data questions and grading the answers with an LLM
judge.

The benchmark runs on [Harbor](https://harborframework.com), the standard
container-based harness for agent evaluation. Each question is a Harbor task;
the agent reaches the hosted `aind-data-mcp` server over MCP at
`https://metadata-portal.allenneuraldynamics.org/mcp/`; and an LLM judge scores
each answer against the authoritative database records. See
[`harbor/README.md`](harbor/README.md) for the full harness docs.

## Directory layout

```
scripts/benchmark/
├── questions/
│   └── questions.json                 # hand-authored benchmark questions
├── ground_truth/
│   ├── generate_ground_truth.py       # official DB queries → raw results
│   └── raw/{id:03d}.json              # authoritative DB records per question
├── harbor/                            # Harbor harness (see harbor/README.md)
│   ├── build_dataset.py               # questions + ground truth → Harbor tasks
│   ├── template/                      # shared task files (env + verifier)
│   └── tasks/                         # generated tasks (git-ignored)
└── README.md
```

## Question schema

Each entry in `questions/questions.json` has the following shape:

```json
{
  "id": 1,
  "question": "...",
  "filter": { ... },          // MongoDB-style filter; omit for aggregations
  "projection": { ... },      // Aggressive projection; only the fields needed
  "limit": 500,               // Optional, default 500
  "agg_pipeline": [ ... ],    // Optional; use sparingly (see note below)
  "complexity": "easy"        // easy | medium | hard
}
```

Questions are designed to have **stable answers regardless of how the database
grows over time**. They are scoped to specific asset names, subject IDs, or
project + time-window filters with a fixed end date. Aggregations over the whole
DB are used sparingly and only for inherently bounded sets.

The ground-truth pipeline favours `filter` + aggressive `projection` over
server-side aggregation. The judge verifies the agent's answer against the raw
returned records.

## Quickstart

```bash
# 1. Install harness dependencies (harbor + litellm)
pip install -e ".[benchmark]"

# 2. Generate ground truth and build the Harbor task dataset
python scripts/benchmark/harbor/build_dataset.py --generate-ground-truth

# 3. Run (requires Docker + an API key for the agent/judge model)
export ANTHROPIC_API_KEY=...
harbor run -p scripts/benchmark/harbor/tasks \
    -a claude-code -m anthropic/claude-sonnet-4-5 \
    --env docker --n-concurrent 4
```

Smoke-test a few questions first with
`build_dataset.py --ids 1 2 21` and `harbor run -p .../tasks/aind-q001 ...`.

## Ground truth

Run this once (or when the question set changes) to fetch the authoritative
database answers used by the judge. It hits the live AIND database, so it needs
network access and the project's runtime dependencies installed:

```bash
python scripts/benchmark/ground_truth/generate_ground_truth.py
```

`build_dataset.py --generate-ground-truth` runs this for you and then builds the
tasks.

## Judging criteria

| Criterion | Description |
|---|---|
| `factual_accuracy` | Key facts (counts, names, dates, values) match the raw DB records returned for the question |
| `completeness` | All relevant aspects of the question addressed |
| `relevance` | Answer focused; no significant off-topic content |
| `clarity` | Well-structured and appropriately formatted |

Each criterion is scored 1–5 (5 = best). Harbor rewards report these scores
normalised to 0–1 plus an `overall` metric. The raw DB records returned by the
official query are the authoritative ground truth.

## Architecture

```
questions/questions.json (hand-authored)
    │
    ├─► ground_truth/generate_ground_truth.py ──► ground_truth/raw/*.json
    │        (MetadataDbClient → live DB)
    │
    └─► harbor/build_dataset.py ──► harbor/tasks/aind-qNNN/
             (instruction.md + task.toml + environment/ + tests/)
                  │
                  ▼
             harbor run  ──►  agent (→ hosted aind-data-mcp)  ──►  answer.txt
                  │
                  ▼
             tests/llm_judge.py  ──►  /logs/verifier/reward.json
```

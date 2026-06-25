# aind-data-mcp Benchmark

End-to-end benchmark that evaluates the **aind-data-mcp** MCP server by having
a Sonnet 4.6 agent answer neuroscience data questions and then grading the
answers with a Haiku 4.5 judge.

## Directory layout

```
scripts/benchmark/
├── config.py                          # Model IDs, AWS profile, timeouts
├── questions/
│   └── questions.json                 # 25 benchmark questions (hand-authored)
├── ground_truth/
│   ├── generate_ground_truth.py       # Run official DB queries → raw results
│   └── raw/
│       └── {id:03d}.json              # Raw DB records per question
├── agent_runner.py                    # Strands + MCPClient → Sonnet agent
├── judge.py                           # Haiku judge via Bedrock Converse API
├── run_benchmark.py                   # Main orchestrator (see below)
└── results/
    └── {run-id}/
        ├── agent_answers.json
        ├── judge_scores.json
        └── summary.json
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
project + time-window filters with a fixed end date. Aggregations over the
whole DB are used sparingly and only for inherently bounded sets (e.g. unique
data_level values, top-N projects).

The ground-truth pipeline favours `filter` + aggressive `projection` over
server-side aggregation. The judge then verifies the agent's answer against
the raw returned records. `$unwind` is not supported by the current backend,
so array-distribution questions are expressed as filter+projection with
deduplication in the agent or judge.

## Setup

### 1. Install benchmark dependencies

```bash
pip install -e ".[benchmark]"
```

### 2. Configure AWS credentials

The benchmark uses your AWS SSO profile to call Amazon Bedrock.  Set the
profile name in [`config.py`](config.py) (`AWS_PROFILE`), then authenticate:

```bash
aws sso login --profile <your-profile>
```

### 3. Update model IDs (if needed)

Open [`config.py`](config.py) and verify `SONNET_MODEL_ID` and
`HAIKU_MODEL_ID` match the Bedrock model IDs available in your account.
The defaults follow the cross-region inference prefix pattern
(`us.anthropic.claude-*`).

## Running the benchmark

### Quick smoke-test (3 easy questions)

```bash
python scripts/benchmark/run_benchmark.py --ids 1 2 21 --run-id smoke-test
```

### Full run

```bash
python scripts/benchmark/run_benchmark.py
```

Results land in `scripts/benchmark/results/<run-id>/`.

### Generate ground truth only

Run this once (or when the question set changes) to fetch the authoritative
database answers used by the judge:

```bash
python scripts/benchmark/run_benchmark.py --ground-truth-only
```

### Re-judge existing agent answers

```bash
python scripts/benchmark/run_benchmark.py \
    --skip-agent \
    --run-id my-run-id
```

## Output files

### `agent_answers.json`

```json
[
  {
    "id": 1,
    "question": "What instrument was used to acquire ...?",
    "agent_answer": "The instrument was SmartSPIM1-7.",
    "tool_calls": [
      {"tool_name": "get_records", "input_keys": ["filter", "projection"]}
    ],
    "elapsed_seconds": 8.3,
    "error": null
  }
]
```

### `judge_scores.json`

```json
[
  {
    "id": 1,
    "question": "...",
    "scores": {
      "factual_accuracy": {"score": 5, "reasoning": "Matches raw record."},
      "completeness":     {"score": 5, "reasoning": "Directly answers the question."},
      "relevance":        {"score": 5, "reasoning": "No off-topic content."},
      "clarity":          {"score": 5, "reasoning": "Short and clear."}
    },
    "overall": 5.0,
    "error": null
  }
]
```

### `summary.json`

Aggregate statistics: overall mean, per-criterion means, breakdown by
complexity (`easy`/`medium`/`hard`), tool-call statistics, token usage
and cost totals, and a per-question row table.

## Judging criteria

| Criterion | Description |
|---|---|
| `factual_accuracy` | Key facts (counts, names, dates, values) match the raw DB records returned for the question |
| `completeness` | All relevant aspects of the question addressed |
| `relevance` | Answer focused; no significant off-topic content |
| `clarity` | Well-structured and appropriately formatted |

All criteria are scored 1–5 (5 = best). The raw DB records returned by the
official query for each question are the authoritative ground truth; the
judge compares the agent's answer against them.

## Architecture

```
questions/questions.json (hand-authored, ~25 V2-correct questions)
    │
    ├─► ground_truth/generate_ground_truth.py ──► ground_truth/raw/*.json
    │        (MetadataDbClient → live DB)
    │
    ├─► agent_runner.py ──────────────────────────► agent_answers.json
    │        (strands Agent + aind-data-mcp MCP subprocess
    │         Claude Sonnet 4.6 via Bedrock)
    │
    └─► judge.py ─────────────────────────────────► judge_scores.json
             (Claude Haiku 4.5 via Bedrock Converse API)
                  │
                  ▼
             summary.json
```

## Resuming interrupted runs

Both the agent runner and the judge write results to disk after **every
question** and skip question IDs that already have results.  A run can be
safely interrupted and resumed with the same `--run-id`.

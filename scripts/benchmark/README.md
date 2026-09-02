# AIND Data MCP benchmark

This benchmark evaluates the published `aind-data-mcp` package locally with
Harbor. The 15 generated tasks are under `harbor/tasks/`.

Run the benchmark with the AWS SSO profile:

```bash
pip install -e ".[benchmark]"
aws sso login --profile aind_octo
HARBOR_AWS_PROFILE=aind_octo ./scripts/benchmark/run_harbor.sh
```

View completed or partial runs afterward:

```bash
.venv/bin/harbor view jobs --jobs --port 8080
open http://127.0.0.1:8080
```

See [`harbor/README.md`](harbor/README.md) for the short run and troubleshooting
guide.

Every benchmark task image must set `BIODATA_CACHE_BACKEND=s3` so
`aind-data-mcp` uses the S3-backed biodata cache. Include
`ENV BIODATA_CACHE_BACKEND="s3"` in the Dockerfile for any new task.

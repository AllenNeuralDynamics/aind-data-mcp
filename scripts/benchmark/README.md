# AIND Data MCP benchmark

This benchmark evaluates the hosted `aind-data-mcp` MCP server with Harbor. The
15 generated tasks are under `harbor/tasks/`.

Run the benchmark with the AWS SSO profile:

```bash
pip install -e ".[benchmark]"
aws sso login --profile aind_octo
AWS_PROFILE=aind_octo ./scripts/benchmark/run_harbor.sh
```

View completed or partial runs afterward:

```bash
.venv/bin/harbor view jobs --jobs --port 8080
open http://127.0.0.1:8080
```

See [`harbor/README.md`](harbor/README.md) for the short run and troubleshooting
guide.

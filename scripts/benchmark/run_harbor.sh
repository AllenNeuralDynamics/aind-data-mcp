#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../.." && pwd)"
cd "$repo_root"

profile="${AWS_PROFILE:-aind_octo}"
region="${AWS_REGION:-us-west-2}"
agent_model="${HARBOR_AGENT_MODEL:-bedrock/us.anthropic.claude-sonnet-5}"
judge_model="${JUDGE_MODEL:-bedrock/us.anthropic.claude-sonnet-5}"
concurrency="${HARBOR_CONCURRENCY:-4}"
tasks_path="${HARBOR_TASKS_PATH:-scripts/benchmark/harbor/tasks}"
harbor_bin="${HARBOR_BIN:-$repo_root/.venv/bin/harbor}"

if ! command -v aws >/dev/null 2>&1; then
    printf 'error: aws CLI is required\n' >&2
    exit 1
fi

if [[ ! -x "$harbor_bin" ]]; then
    harbor_bin="$(command -v harbor || true)"
fi
if [[ -z "$harbor_bin" ]]; then
    printf 'error: Harbor is not installed; run: pip install -e ".[benchmark]"\n' >&2
    exit 1
fi

export AWS_REGION="$region"
export JUDGE_MODEL="$judge_model"

declare -a agent_auth_args
if [[ -n "${AWS_BEARER_TOKEN_BEDROCK:-}" ]]; then
    unset AWS_PROFILE AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
    unset AWS_SESSION_TOKEN AWS_CREDENTIAL_EXPIRATION
    agent_auth_args=(
        --ae "AWS_BEARER_TOKEN_BEDROCK=$AWS_BEARER_TOKEN_BEDROCK"
    )
else
    export AWS_PROFILE="$profile"
    eval "$(aws configure export-credentials \
        --profile "$AWS_PROFILE" \
        --format env)"
    aws sts get-caller-identity \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" >/dev/null
    unset AWS_PROFILE
    agent_auth_args=(
        --ae "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID"
        --ae "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY"
        --ae "AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN"
    )
fi

exec "$harbor_bin" run \
    -p "$tasks_path" \
    -a claude-code \
    -m "$agent_model" \
    --ae CLAUDE_CODE_USE_BEDROCK=1 \
    "${agent_auth_args[@]}" \
    --ae "AWS_REGION=$AWS_REGION" \
    --env docker \
    --n-concurrent "$concurrency" \
    "$@"

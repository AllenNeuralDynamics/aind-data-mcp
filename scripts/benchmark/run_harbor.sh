#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../.." && pwd)"
cd "$repo_root"

profile="${HARBOR_AWS_PROFILE:-aind_octo}"
region="${AWS_REGION:-us-west-2}"
model_haiku_45="bedrock/us.anthropic.claude-haiku-4-5-20251001-v1:0"
model_sonnet_46="bedrock/us.anthropic.claude-sonnet-4-6"
model_sonnet_5="bedrock/us.anthropic.claude-sonnet-5"
agent_model="${HARBOR_AGENT_MODEL:-$model_sonnet_5}"
judge_model="${JUDGE_MODEL:-$model_sonnet_5}"
concurrency="${HARBOR_CONCURRENCY:-16}"
tasks_path="${HARBOR_TASKS_PATH:-scripts/benchmark/harbor/tasks}"
harbor_bin="${HARBOR_BIN:-$repo_root/.venv/bin/harbor}"
aws_bin="${AWS_BIN:-$(command -v aws || true)}"

case "$agent_model" in
    haiku-4.5) agent_model="$model_haiku_45" ;;
    sonnet-4.6) agent_model="$model_sonnet_46" ;;
    sonnet-5) agent_model="$model_sonnet_5" ;;
esac

if [[ -z "$aws_bin" && -x /usr/local/bin/aws ]]; then
    aws_bin=/usr/local/bin/aws
fi
if [[ -z "$aws_bin" ]]; then
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
    eval "$("$aws_bin" configure export-credentials \
        --profile "$AWS_PROFILE" \
        --format env)"
    "$aws_bin" sts get-caller-identity \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" >/dev/null
    unset AWS_PROFILE AWS_DEFAULT_PROFILE AWS_CREDENTIAL_EXPIRATION
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

#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../.." && pwd)"
cd "$repo_root"

profile="${HARBOR_AWS_PROFILE:-aind_octo}"
region="${AWS_REGION:-us-west-2}"
model_sonnet_5="bedrock/us.anthropic.claude-sonnet-5"
model_gpt_56_luna="bedrock/openai.gpt-5.6-luna"
judge_model="${JUDGE_MODEL:-$model_sonnet_5}"
concurrency="${HARBOR_CONCURRENCY:-16}"
tasks_path="${HARBOR_TASKS_PATH:-scripts/benchmark/harbor/tasks}"
harbor_bin="${HARBOR_BIN:-$repo_root/.venv/bin/harbor}"
aws_bin="${AWS_BIN:-$(command -v aws || true)}"

if [[ -n "${HARBOR_AGENT_MODEL:-}" ]]; then
    agent_models=("$HARBOR_AGENT_MODEL")
else
    agent_models=("$model_sonnet_5" "$model_gpt_56_luna")
fi

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

for agent_model in "${agent_models[@]}"; do
    case "$agent_model" in
        gpt-5.6-luna) agent_model="$model_gpt_56_luna" ;;
        sonnet-5) agent_model="$model_sonnet_5" ;;
    esac

    printf 'Running Harbor benchmark with agent model: %s\n' "$agent_model"
    "$harbor_bin" run \
        -p "$tasks_path" \
        -a claude-code \
        -m "$agent_model" \
        --ae CLAUDE_CODE_USE_BEDROCK=1 \
        "${agent_auth_args[@]}" \
        --ae "AWS_REGION=$AWS_REGION" \
        --env docker \
        --n-concurrent "$concurrency" \
        "$@"
done

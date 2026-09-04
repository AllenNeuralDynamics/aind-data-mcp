#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../.." && pwd)"
cd "$repo_root"

profile="${HARBOR_AWS_PROFILE:-aind_octo}"
region="${AWS_REGION:-us-west-2}"
model_sonnet_5="anthropic/claude-sonnet-5"
model_gpt_56_luna="gpt-5.6-luna"
codex_auth_path="${CODEX_AUTH_JSON_PATH:-$HOME/.codex/auth.json}"
claude_oauth_token_file="${CLAUDE_CODE_OAUTH_TOKEN_FILE:-}"
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

if [[ ! -x "$harbor_bin" ]]; then
    harbor_bin="$(command -v harbor || true)"
fi
if [[ -z "$harbor_bin" ]]; then
    printf 'error: Harbor is not installed; run: pip install -e ".[benchmark]"\n' >&2
    exit 1
fi

if [[ "$judge_model" == bedrock/* ]]; then
    printf '%s\n' \
        'error: JUDGE_MODEL still selects Bedrock.' \
        'Unset JUDGE_MODEL or set it to anthropic/claude-sonnet-5.' >&2
    exit 1
fi

claude_oauth_token="${CLAUDE_CODE_OAUTH_TOKEN:-}"
if [[ -n "$claude_oauth_token_file" ]]; then
    if [[ ! -r "$claude_oauth_token_file" ]]; then
        printf 'error: Claude OAuth token file not readable: %s\n' \
            "$claude_oauth_token_file" >&2
        exit 1
    fi
    claude_oauth_token="$(tr -d '[:space:]' < "$claude_oauth_token_file")"
fi

if [[ -z "$claude_oauth_token" && "${ANTHROPIC_API_KEY:-}" == sk-ant-oat* ]]; then
    claude_oauth_token="$ANTHROPIC_API_KEY"
fi
if [[ -z "$claude_oauth_token" ]]; then
    printf '%s\n' \
        'error: Claude Code OAuth token is required for the Sonnet run.' \
        'Run `claude setup-token` with a Claude subscription, then set' \
        'CLAUDE_CODE_OAUTH_TOKEN or CLAUDE_CODE_OAUTH_TOKEN_FILE.' >&2
    exit 1
fi
if [[ "$claude_oauth_token" != sk-ant-oat* ]]; then
    printf '%s\n' \
        'error: CLAUDE_CODE_OAUTH_TOKEN is not a Claude subscription OAuth token.' \
        'Expected a token beginning with sk-ant-oat; do not use an API key here.' >&2
    exit 1
fi

export AWS_REGION="$region"
export JUDGE_MODEL="$judge_model"
export ANTHROPIC_API_KEY="$claude_oauth_token"

unset CLAUDE_CODE_USE_BEDROCK AWS_BEARER_TOKEN_BEDROCK

if [[ -z "$aws_bin" && -x /usr/local/bin/aws ]]; then
    aws_bin=/usr/local/bin/aws
fi
if [[ -z "$aws_bin" ]]; then
    printf 'error: aws CLI is required for the S3-backed benchmark cache\n' >&2
    exit 1
fi

export AWS_PROFILE="$profile"
eval "$("$aws_bin" configure export-credentials \
    --profile "$AWS_PROFILE" \
    --format env)"
"$aws_bin" sts get-caller-identity \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" >/dev/null
unset AWS_PROFILE AWS_DEFAULT_PROFILE AWS_CREDENTIAL_EXPIRATION
declare -a aws_auth_args=(
    --ae "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID"
    --ae "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY"
    --ae "AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN"
)

for agent_model in "${agent_models[@]}"; do
    agent_name=claude-code
    declare -a model_agent_env_args

    case "$agent_model" in
        gpt-5.6-luna)
            agent_model="$model_gpt_56_luna"
            agent_name=codex
            if [[ ! -f "$codex_auth_path" ]]; then
                printf 'error: Codex auth file not found: %s\n' "$codex_auth_path" >&2
                exit 1
            fi
            model_agent_env_args=(
                --ae "CODEX_AUTH_JSON_PATH=$codex_auth_path"
            )
            ;;
        sonnet-5) agent_model="$model_sonnet_5" ;;
        *)
            model_agent_env_args=()
            ;;
    esac

    if [[ "$agent_name" == claude-code ]]; then
        model_agent_env_args=(
            --ae CLAUDE_FORCE_OAUTH=1
            --ae "CLAUDE_CODE_OAUTH_TOKEN=$claude_oauth_token"
            "${aws_auth_args[@]}"
            --ae "AWS_REGION=$AWS_REGION"
        )
    fi

    printf 'Running Harbor benchmark with %s agent and %s model\n' \
        "$agent_name" "$agent_model"
    "$harbor_bin" run \
        -p "$tasks_path" \
        -a "$agent_name" \
        -m "$agent_model" \
        "${model_agent_env_args[@]}" \
        --env docker \
        --n-concurrent "$concurrency" \
        "$@"
done

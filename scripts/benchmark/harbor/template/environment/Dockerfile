# Agent container ("main" service).
#
# Harbor installs the selected CLI agent (Claude Code, Codex, etc.) into this
# image at runtime, so it only needs a general-purpose base with Python, Node,
# curl and git available.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

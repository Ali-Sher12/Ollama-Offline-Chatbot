#!/usr/bin/env bash
set -e

# Change directory to script folder
cd "$(dirname "$0")"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python3 main.py "$@"

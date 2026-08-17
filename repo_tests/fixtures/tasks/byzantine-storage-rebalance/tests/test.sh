#!/bin/bash
set -uo pipefail

# Check if we're in a valid working directory
if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    mkdir -p /logs/verifier
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

mkdir -p /logs/verifier

# pytest and pytest-json-ctrf are baked into tests/Dockerfile.
python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

# Produce reward file (REQUIRED). No `set -e`: a failing pytest must still
# reach this block, and Harbor grades from reward.txt rather than the exit code.
rc=$?
if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi

#!/usr/bin/env bash
set -euo pipefail

# Verify dependencies exist before running the main program
command -v docker >/dev/null 2>&1
command -v python3 >/dev/null 2>&1

python3 main.py
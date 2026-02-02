#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
. .venv/bin/activate
./.venv/bin/python -u src/broker/shioaji_recorder.py

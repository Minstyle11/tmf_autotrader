#!/bin/bash
set -euo pipefail
python3 src/ops/require_bibles_v1.py
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/scripts/m3_mainline_runner_v1.sh" "$@"

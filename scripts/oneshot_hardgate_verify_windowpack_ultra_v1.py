#!/usr/bin/env python3
"""
Compatibility wrapper (v1 entrypoint)
- Some docs/prompts may reference: scripts/oneshot_hardgate_verify_windowpack_ultra_v1.py
- Canonical implementation lives at: scripts/oneshot_hardgate_verify_ultra.py
This wrapper forwards argv to keep new/old packs 100% stable.
"""
import os, sys, runpy
from pathlib import Path

HERE = Path(__file__).resolve()
TARGET = HERE.parent / "oneshot_hardgate_verify_ultra.py"

if not TARGET.exists():
    print(f"[FATAL] missing target: {TARGET}", file=sys.stderr)
    sys.exit(2)

# Execute target as __main__ with same argv[0] semantics
sys.argv[0] = str(TARGET)
runpy.run_path(str(TARGET), run_name="__main__")

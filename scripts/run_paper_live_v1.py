#!/usr/bin/env python3
from __future__ import annotations

# Stable scripts entrypoint for paper-live runner.
# Delegates to src.oms.run_paper_live_v1 (single source of truth).

from src.oms.run_paper_live_v1 import main

if __name__ == "__main__":
    main()

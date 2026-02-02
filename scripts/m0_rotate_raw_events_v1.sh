#!/usr/bin/env bash
set -euo pipefail

PROJ="$HOME/tmf_autotrader"
RAW_DIR="$PROJ/runtime/data"
ARCH_DIR="$RAW_DIR/archive"

KEEP_N="${KEEP_N:-200}"          # keep newest N jsonl in place
DRYRUN="${DRYRUN:-0}"

# allow flag
if [[ "${1:-}" == "--dry-run" ]]; then DRYRUN=1; fi

python3 - <<'PY'
import os, re, gzip, shutil
from pathlib import Path
from datetime import datetime

raw_dir = Path(os.environ.get("RAW_DIR", str(Path.home() / "tmf_autotrader/runtime/data")))
arch_dir = Path(os.environ.get("ARCH_DIR", str(raw_dir / "archive")))
keep_n = int(os.environ.get("KEEP_N", "200"))
dryrun = int(os.environ.get("DRYRUN", "0"))

pat = re.compile(r"raw_events_(\d{8})_(\d{6})\.jsonl$")
files = []
for p in raw_dir.glob("raw_events_*.jsonl"):
    m = pat.match(p.name)
    if not m:
        continue
    ts = m.group(1) + m.group(2)
    try:
        dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
    except Exception:
        continue
    files.append((dt, p))

files.sort(key=lambda x: x[0], reverse=True)

print(f"=== [ROTATE] raw_dir={raw_dir} keep_n={keep_n} dryrun={dryrun} ===")
print(f"[ROTATE] total_jsonl={len(files)}")

to_archive = files[keep_n:]
print(f"[ROTATE] archive_candidates={len(to_archive)}")

moved = 0
for dt, p in to_archive:
    day = dt.strftime("%Y-%m-%d")
    dst_dir = arch_dir / day
    dst_gz = dst_dir / (p.name + ".gz")
    if dst_gz.exists():
        # already archived
        continue

    print(f"[ROTATE] {p.name} -> {dst_gz.relative_to(raw_dir.parent)}")
    if dryrun:
        continue

    dst_dir.mkdir(parents=True, exist_ok=True)

    # stream gzip then remove source
    with p.open("rb") as f_in, gzip.open(dst_gz, "wb", compresslevel=6) as f_out:
        shutil.copyfileobj(f_in, f_out)

    p.unlink(missing_ok=True)
    moved += 1

print(f"[ROTATE][OK] archived={moved} (dryrun={dryrun})")
PY

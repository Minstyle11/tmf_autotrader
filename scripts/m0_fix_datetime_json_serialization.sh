#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

python3 - <<'PY'
from pathlib import Path
p = Path("src/broker/shioaji_recorder.py")
s = p.read_text(encoding="utf-8")

# Replace write_jsonl with a safe version (idempotent patch)
import re

safe_block = r'''
def _json_default(o):
    # Final safety net for json.dumps
    try:
        import datetime, base64
        if isinstance(o, (datetime.datetime, datetime.date, datetime.time)):
            return o.isoformat()
        if isinstance(o, (bytes, bytearray)):
            return base64.b64encode(bytes(o)).decode("ascii")
    except Exception:
        pass
    return str(o)

def _to_jsonable(x):
    # Deep conversion to JSON-safe types
    import datetime
    if x is None or isinstance(x, (str, int, float, bool)):
        return x
    if isinstance(x, (datetime.datetime, datetime.date, datetime.time)):
        return x.isoformat()
    if isinstance(x, (list, tuple)):
        return [_to_jsonable(i) for i in x]
    if isinstance(x, dict):
        out = {}
        for k,v in x.items():
            out[str(k)] = _to_jsonable(v)
        return out
    # extension types / unknown objects
    return str(x)

def write_jsonl(path: Path, rec: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    # ensure fully jsonable
    rec = _to_jsonable(rec)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=_json_default) + "\\n")
'''.strip("\n")

# Find existing write_jsonl function and replace the whole definition
pat = r"def write_jsonl\(path: Path, rec: dict\):\n(?:.*\n)+?\n"
m = re.search(pat, s)
if not m:
    raise SystemExit("[FATAL] cannot locate write_jsonl() to patch")

s2 = s[:m.start()] + safe_block + "\n\n" + s[m.end():]
p.write_text(s2, encoding="utf-8")
print("[OK] patched write_jsonl() with deep json-safe conversion")
PY

echo "=== [RUN] recorder smoke 10s (should NOT throw datetime JSON error) ==="
. .venv/bin/activate
MAX_SECONDS=10 python -u src/broker/shioaji_recorder.py || true

echo
echo "=== [CHECK] latest raw_events file last 5 lines ==="
LATEST="$(ls -1t runtime/data/raw_events_*.jsonl 2>/dev/null | head -n 1 || true)"
echo "[INFO] latest=$LATEST"
tail -n 5 "$LATEST" || true

echo
echo "=== [OK] serialization fix applied ==="

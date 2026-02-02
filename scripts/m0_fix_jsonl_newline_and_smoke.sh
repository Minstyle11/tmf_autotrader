#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

python3 - <<'PY'
from pathlib import Path
import re
p = Path("src/broker/shioaji_recorder.py")
s = p.read_text(encoding="utf-8")

# Ensure the file write uses real newline byte, not literal "\\n"
# We replace any occurrences of +"\\n" with +"\n" inside write_jsonl
# and also ensure f.write ends with "\n"
s2 = s

# Patch: replace escaped newline literals in write_jsonl block if any
s2 = s2.replace(' + "\\\\n")', ' + "\\n")')   # if someone accidentally double-escaped
s2 = s2.replace(' + "\\\\n"', ' + "\\n"')     # broader
s2 = s2.replace(" + '\\\\n'", " + '\\n'")

# Strong patch: find the exact f.write(json.dumps... ) line and force "\n"
pat = r"f\.write\(\s*json\.dumps\((.*?)\)\s*\+\s*([\"'])(?:\\\\n|\\n)([\"'])\s*\)"
m = re.search(pat, s2)
if m:
    # rebuild with explicit "\n"
    inner = m.group(1)
    s2 = re.sub(pat, r"f.write(json.dumps(\1) + \"\\n\")", s2, count=1)

# If still not found, do a simpler targeted replace for common patterns
s2 = s2.replace('f.write(json.dumps(rec, ensure_ascii=False, default=_json_default) + "\\\\n")',
                'f.write(json.dumps(rec, ensure_ascii=False, default=_json_default) + "\\n")')
s2 = s2.replace('f.write(json.dumps(rec, ensure_ascii=False, default=_json_default) + "\\n")',
                'f.write(json.dumps(rec, ensure_ascii=False, default=_json_default) + "\\n")')

p.write_text(s2, encoding="utf-8")
print("[OK] patched recorder to write real newline bytes")
PY

echo "=== [RUN] recorder smoke 10s (new file) ==="
. .venv/bin/activate
MAX_SECONDS=10 python -u src/broker/shioaji_recorder.py || true

echo
echo "=== [VERIFY] latest raw_events newline bytes ==="
LATEST="$(ls -1t runtime/data/raw_events_*.jsonl 2>/dev/null | head -n 1)"
python3 - <<'PY'
import sys
p=sys.argv[1]
b=open(p,"rb").read()
print("LATEST:", p)
print("BYTES:", len(b))
print("count(\\n byte):", b.count(b"\n"))
print("count(literal \\\\n):", b.count(b"\\n"))
print("HEAD 1:", open(p,"r",encoding="utf-8",errors="replace").readline().rstrip("\n")[:200])
PY "$LATEST"

echo
echo "=== [PY JSONL PARSE] count ok/bad lines ==="
python3 - <<'PY'
import json, sys
p=sys.argv[1]
ok=bad=0
first=None
with open(p,"r",encoding="utf-8",errors="replace") as f:
    for i,line in enumerate(f,1):
        s=line.rstrip("\n")
        if not s: 
            continue
        try:
            json.loads(s); ok+=1
        except Exception as e:
            bad+=1
            if first is None:
                first=(i,repr(e),s[:300])
print("[INFO] ok_lines=%d bad_lines=%d"%(ok,bad))
if first:
    print("=== [FIRST BAD] line=%d err=%s ==="%(first[0],first[1]))
    print(first[2])
PY "$LATEST"

echo
echo "=== [OK] newline fix smoke done ==="

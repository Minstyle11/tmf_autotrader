#!/bin/bash
set -euo pipefail
python3 src/ops/require_bibles_v1.py

echo "=== [0/7] pm_refresh_board ==="
bash scripts/pm_refresh_board_canonical.sh
bash scripts/verify_pm_refresh_board_v1.sh

cd "$HOME/tmf_autotrader"

echo "=== [M3 MAINLINE v1] start $(date -Iseconds) ==="

REQ=(
  "scripts/m3_regression_spec_os_v1.sh"
  "scripts/m3_regression_reject_policy_v1.sh"
  "scripts/m3_regression_reconcile_os_v1.sh"
  "scripts/m3_regression_audit_replay_os_v1.sh"
  "scripts/m3_regression_latency_backpressure_os_v1.sh"
  "scripts/mk_windowpack_ultra.sh"
)
for f in "${REQ[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "[FATAL] missing required file: $f"
    exit 2
  fi
done

echo "=== [1/7] m3_regression_spec_os_v1 ==="
bash scripts/m3_regression_spec_os_v1.sh

echo "=== [2/7] m3_regression_reject_policy_v1 ==="
bash scripts/m3_regression_reject_policy_v1.sh

echo "=== [3/7] m3_regression_reconcile_os_v1 ==="
bash scripts/m3_regression_reconcile_os_v1.sh

echo "=== [4/7] m3_regression_audit_replay_os_v1 ==="
bash scripts/m3_regression_audit_replay_os_v1.sh

echo "=== [5/7] m3_regression_latency_backpressure_os_v1 ==="
bash scripts/m3_regression_latency_backpressure_os_v1.sh

echo "=== [6/7] mk_windowpack_ultra ==="
echo "=== [X/6] m3_regression_taifex_split_v1 ==="
bash scripts/m3_regression_taifex_split_v1.sh
echo "=== [X/8] m3_regression_paper_live_smoke_v1 ==="
bash scripts/m3_regression_paper_live_smoke_v1.sh
bash scripts/mk_windowpack_ultra.sh

# HardGate newest zip in runtime/handoff/latest
NEW_ZIP="$(ls -1t runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_*.zip | head -n 1 || true)"
if [[ -z "$NEW_ZIP" ]]; then
  echo "[FATAL] cannot find TMF_AutoTrader_WindowPack_ULTRA_*.zip in runtime/handoff/latest"
  exit 2
fi
echo "[INFO] newest_zip=$NEW_ZIP"

python3 - <<'PY'
import hashlib, re, subprocess, tempfile
from pathlib import Path

zip_path = Path(sorted(Path("runtime/handoff/latest").glob("TMF_AutoTrader_WindowPack_ULTRA_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)[0]).resolve()
sidecar = zip_path.with_suffix(zip_path.suffix + ".sha256.txt")
assert sidecar.exists(), f"missing sidecar: {sidecar}"

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

expected = sidecar.read_text(encoding="utf-8", errors="replace").strip().split()[0]
actual = sha256_file(zip_path)
print("[CHECK] zip_sha256_expected =", expected)
print("[CHECK] zip_sha256_actual   =", actual)
assert expected == actual, "zip sha256 mismatch"

td = Path(tempfile.mkdtemp(prefix="tmf_autotrader_m3_mainline_hardgate_"))
subprocess.check_call(["unzip","-q",str(zip_path),"-d",str(td)])

mfs = list(td.rglob("MANIFEST_SHA256_ALL_FILES.txt"))
assert len(mfs)==1, f"expected 1 manifest; got {len(mfs)}: {mfs}"
mf = mfs[0]
root = mf.parent
print("[OK] unpack_root =", root)

bad = []
rx = re.compile(r"^([0-9a-f]{64})\s+(.*)$")
for line in mf.read_text(encoding="utf-8", errors="replace").splitlines():
    line=line.strip()
    if not line:
        continue
    m = rx.match(line)
    if not m:
        bad.append(("bad_line", line))
        continue
    h, rel = m.group(1), m.group(2)
    p = root / rel
    if not p.exists():
        bad.append(("missing", rel))
        continue
    hh = sha256_file(p)
    if hh != h:
        bad.append(("sha_mismatch", rel))

if bad:
    print("[FAIL] manifest verify issues:", len(bad))
    for x in bad[:30]:
        print(" ", x)
    raise SystemExit(2)

print("[PASS] M3 MAINLINE hardgate OK:", zip_path)
PY

echo "=== [M3 MAINLINE v1] PASS $(date -Iseconds) ==="

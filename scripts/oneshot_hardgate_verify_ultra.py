#!/usr/bin/env python3
# Ultra OneShot HardGate verifier shim
# Purpose: keep legacy entrypoint path stable:
#   python3 scripts/oneshot_hardgate_verify_ultra.py <zip> <sha256_sidecar>
# Implementation: delegate to the maintained shell SOP.
import os, sys, subprocess
from pathlib import Path

def die(msg: str, rc: int = 2):
    print(f"[FATAL] {msg}", file=sys.stderr)
    raise SystemExit(rc)

def main():
    repo = Path(__file__).resolve().parents[1]
    sh = repo / "scripts" / "ops_new_window_oneshot_hardgate_v1.sh"
    if not sh.exists():
        die(f"missing delegate script: {sh}")
    zip_path = sys.argv[1] if len(sys.argv) >= 2 else ""
    sha_sidecar = sys.argv[2] if len(sys.argv) >= 3 else ""
    if not zip_path:
        die("usage: python3 scripts/oneshot_hardgate_verify_ultra.py <zip_path> <zip_sha256_sidecar_txt>")
    # Preserve caller cwd env; ensure we run from repo root for relative paths inside SOP.
    env = os.environ.copy()
    cmd = ["bash", str(sh), zip_path]
    if sha_sidecar:
        cmd.append(sha_sidecar)
    print(f"[INFO] delegate -> {sh.name}")
    r = subprocess.run(cmd, cwd=str(repo), env=env)
    raise SystemExit(r.returncode)

if __name__ == "__main__":
    main()

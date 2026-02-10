#!/usr/bin/env python3
import sys, hashlib
from pathlib import Path

REQUIRED = [
    "docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md",
    "docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md.sha256.txt",
    "docs/bibles/TMF_AUTOTRADER_CONSTITUTION_BIBLE_v1.md",
    "docs/bibles/TMF_AUTOTRADER_CONSTITUTION_BIBLE_v1.md.sha256.txt",
]

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def verify_sidecar(md_path: Path, sidecar: Path) -> None:
    txt = sidecar.read_text(encoding="utf-8", errors="replace").strip()
    expected = txt.split()[0] if txt else ""
    if len(expected) != 64:
        raise RuntimeError(f"bad sidecar format: {sidecar} => {txt[:120]}")
    actual = sha256_file(md_path)
    if actual != expected:
        raise RuntimeError(f"sha256 mismatch: {md_path} expected={expected} actual={actual}")

def main() -> int:
    missing = [p for p in REQUIRED if not Path(p).exists()]
    if missing:
        print("[FATAL] required bibles missing:")
        for p in missing:
            print(" -", p)
        return 2

    verify_sidecar(Path("docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md"),
                   Path("docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md.sha256.txt"))
    verify_sidecar(Path("docs/bibles/TMF_AUTOTRADER_CONSTITUTION_BIBLE_v1.md"),
                   Path("docs/bibles/TMF_AUTOTRADER_CONSTITUTION_BIBLE_v1.md.sha256.txt"))

    print("[OK] required bibles present + sha256 sidecar OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())

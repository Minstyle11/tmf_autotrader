import os, sys, re
from dotenv import load_dotenv
import shioaji as sj

def main():
    # load token env
    load_dotenv("configs/secrets/shioaji.env")
    api_key = (os.getenv("SHIOAJI_API_KEY","") or os.getenv("API_KEY","")).strip()
    secret_key = (os.getenv("SHIOAJI_SECRET_KEY","") or os.getenv("SECRET_KEY","")).strip()
    if not api_key or not secret_key:
        print("[FATAL] Missing SHIOAJI_API_KEY/SHIOAJI_SECRET_KEY in configs/secrets/shioaji.env", file=sys.stderr)
        sys.exit(2)

    api = sj.Shioaji()
    print("[INFO] logging in ...")
    api.login(api_key=api_key, secret_key=secret_key, subscribe_trade=True)

    futs = api.Contracts.Futures

    # Futures is dict-like: group -> contracts mapping
    try:
        groups = list(futs.keys())
    except Exception:
        # fallback: attribute introspection
        groups = [g for g in dir(futs) if g.isupper() and not g.startswith("_")]

    print(f"=== FUTURES GROUPS (count={len(groups)}) ===")
    for g in groups:
        print(g)

    patt = re.compile(r"(MTX|TMF|TXF|MXF|MITX|TX|R1|R2)", re.I)

    print("\n=== MATCHING CONTRACT KEYS (top hits) ===")
    hits = []
    for g in groups:
        try:
            m = futs[g]
        except Exception:
            try:
                m = getattr(futs, g)
            except Exception:
                continue
        try:
            keys = list(m.keys())
        except Exception:
            continue
        # score keys that look relevant
        rel = [k for k in keys if patt.search(str(k))]
        for k in rel[:60]:
            hits.append((g, str(k)))
    # de-dup while keeping order
    seen=set()
    uniq=[]
    for g,k in hits:
        if (g,k) in seen:
            continue
        seen.add((g,k))
        uniq.append((g,k))

    for g,k in uniq[:120]:
        print(f"{g} -> {k}")

    print("\n=== SUGGESTED CONTINUOUS (R1/R2) CANDIDATES ===")
    for g,k in uniq:
        if k.upper().endswith("R1") or k.upper().endswith("R2"):
            print(f"{g} -> {k}")

    print("\n[OK] inspection done. logout.")
    try:
        api.logout()
    except Exception:
        pass

if __name__ == "__main__":
    main()

import os, sys, time, re
from dotenv import load_dotenv
import shioaji as sj

def die(msg, code=2):
    print(f"[FATAL] {msg}", file=sys.stderr)
    sys.exit(code)

def main():
    load_dotenv("configs/secrets/shioaji.env")
    api_key = (os.getenv("SHIOAJI_API_KEY","") or os.getenv("API_KEY","")).strip()
    secret_key = (os.getenv("SHIOAJI_SECRET_KEY","") or os.getenv("SECRET_KEY","")).strip()
    if not api_key or not secret_key:
        die("Missing SHIOAJI_API_KEY/SHIOAJI_SECRET_KEY in configs/secrets/shioaji.env")

    api = sj.Shioaji()
    print("[INFO] login (contracts_timeout=15000ms) ...")
    api.login(api_key=api_key, secret_key=secret_key, contracts_timeout=15000, subscribe_trade=True)

    futs = api.Contracts.Futures
    targets = ["TXF", "MXF", "TMF", "MTX", "TX", "TMF"]  # include common names; we'll probe which exist as groups

    print("\n=== PROBE GROUPS ===")
    available = []
    for g in targets:
        try:
            grp = futs[g]
            keys = list(grp.keys())
            available.append(g)
            print(f"[OK] group {g}: contracts={len(keys)}")
        except Exception as e:
            print(f"[MISS] group {g}: {e}")

    if not available:
        print("[FATAL] none of TXF/MXF/TMF groups accessible; check contracts download or account permission.")
        try: api.logout()
        except Exception: pass
        sys.exit(3)

    patt_r = re.compile(r"(R1|R2)$", re.I)

    for g in available:
        grp = futs[g]
        keys = list(grp.keys())
        keys_sorted = sorted([str(k) for k in keys])

        print(f"\n=== GROUP {g} KEYS (top 80 sorted) ===")
        for k in keys_sorted[:80]:
            print(k)

        rkeys = [k for k in keys_sorted if patt_r.search(k)]
        print(f"\n=== GROUP {g} CONTINUOUS CANDIDATES (R1/R2) ===")
        if rkeys:
            for k in rkeys:
                c = grp[k]
                name = getattr(c, "name", "")
                dm = getattr(c, "delivery_month", "")
                sym = getattr(c, "symbol", "")
                print(f"{k} | symbol={sym} | delivery={dm} | name={name}")
        else:
            print("(none)")

        # show a few contract details (latest-looking ones at end)
        print(f"\n=== GROUP {g} SAMPLE DETAILS (last 10 sorted keys) ===")
        for k in keys_sorted[-10:]:
            c = grp[k]
            name = getattr(c, "name", "")
            dm = getattr(c, "delivery_month", "")
            sym = getattr(c, "symbol", "")
            exch = getattr(c, "exchange", "")
            print(f"{k} | symbol={sym} | exch={exch} | delivery={dm} | name={name}")

    print("\n[OK] inspection done; logout.")
    try:
        api.logout()
    except Exception:
        pass

if __name__ == "__main__":
    main()

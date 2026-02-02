import os, sys, time, re
from dotenv import load_dotenv
import shioaji as sj

def die(msg, code=2):
    print(f"[FATAL] {msg}", file=sys.stderr)
    sys.exit(code)

def wait_contracts(api, max_wait=20):
    # Official: Contracts download is non-blocking; use Contracts.status or contracts_timeout.
    # We'll poll status best-effort.
    for i in range(max_wait):
        st = getattr(api.Contracts, "status", None)
        # status could be dict-like; if not available, just break after a short delay.
        if st is None:
            time.sleep(1)
            continue
        try:
            # If any status value is False, still downloading
            vals = list(st.values()) if hasattr(st, "values") else [bool(st)]
            if all(bool(v) for v in vals) and len(vals) > 0:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False

def main():
    load_dotenv("configs/secrets/shioaji.env")
    api_key = (os.getenv("SHIOAJI_API_KEY","") or os.getenv("API_KEY","")).strip()
    secret_key = (os.getenv("SHIOAJI_SECRET_KEY","") or os.getenv("SECRET_KEY","")).strip()
    if not api_key or not secret_key:
        die("Missing SHIOAJI_API_KEY/SHIOAJI_SECRET_KEY in configs/secrets/shioaji.env")

    api = sj.Shioaji()
    print("[INFO] login with contracts_timeout=15000ms ...")
    api.login(api_key=api_key, secret_key=secret_key, contracts_timeout=15000)

    # Extra safety: wait status; if still not ready, force fetch_contracts
    ready = wait_contracts(api, max_wait=15)
    print(f"[INFO] Contracts.status ready? {ready}")

    # If Futures still empty, force fetch_contracts(contract_download=True)
    futs = api.Contracts.Futures
    def futures_count():
        try:
            return len(list(futs.keys()))
        except Exception:
            return 0

    gcount = futures_count()
    print(f"=== FUTURES GROUPS COUNT (pre-fetch) = {gcount} ===")

    if gcount == 0:
        print("[INFO] forcing api.fetch_contracts(contract_download=True) ...")
        try:
            api.fetch_contracts(contract_download=True)
        except Exception as e:
            print(f"[WARN] fetch_contracts raised: {e}")
        time.sleep(2)

    gcount = futures_count()
    print(f"=== FUTURES GROUPS COUNT (post-fetch) = {gcount} ===")

    # Print groups
    try:
        groups = list(futs.keys())
    except Exception:
        groups = []
    if groups:
        print("=== FUTURES GROUPS (top 60) ===")
        for g in groups[:60]:
            print(g)

    # Search contracts by name/category/symbol for TX / mini / micro
    # We don't assume exact category for MTX/TMF. We'll scan all futures.
    patt = re.compile(r"(台股|臺股|台指|臺指|小型|微型|TXF|TX|MTX|TMF|MXF|TMF)", re.I)

    hits = []
    # futs supports: futs["TXFA3"] and futs.TXF.TXF202301 etc. We'll iterate via codes if possible.
    # The flat dict of all futures codes is accessible by iterating futs (dict-like) in many builds.
    try:
        # futs is dict-like mapping code->Contract
        for code in list(futs.keys()):
            try:
                c = futs[code]
            except Exception:
                continue
            name = getattr(c, "name", "")
            symbol = getattr(c, "symbol", "")
            cat = getattr(c, "category", "")
            if patt.search(f"{code} {symbol} {name} {cat}"):
                hits.append((cat, code, symbol, name, getattr(c, "delivery_month", ""), getattr(c, "update_date", "")))
    except Exception as e:
        print(f"[WARN] cannot iterate futs as dict: {e}")

    # sort: prioritize likely index futures (category contains TXF/MXF/TMF) then by code
    def score(x):
        cat=x[0] or ""
        pri = 0
        if "TXF" in cat: pri = 0
        elif "MXF" in cat or "MX" in cat: pri = 1
        elif "TMF" in cat or "TM" in cat: pri = 2
        else: pri = 9
        return (pri, cat, x[1])
    hits_sorted = sorted(hits, key=score)

    print("\n=== MATCH HITS (top 120) ===")
    for cat, code, symbol, name, m, ud in hits_sorted[:120]:
        print(f"{cat:>4} | {code:>8} | {symbol:>12} | {m:>6} | {ud:>10} | {name}")

    print("\n[OK] done; logout.")
    try:
        api.logout()
    except Exception:
        pass

if __name__ == "__main__":
    main()

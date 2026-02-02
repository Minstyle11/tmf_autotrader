from __future__ import annotations
from pathlib import Path
from src.oms.paper_oms_v1 import PaperOMS

def main():
    db = Path("runtime/data/tmf_autotrader_v1.sqlite3")
    oms = PaperOMS(db)

    # Open long: MARKET BUY 2 @ 20000
    o1 = oms.submit_order(symbol="TMF", side="BUY", qty=2, order_type="MARKET")
    fills1 = oms.match(o1, market_price=20000.0, reason="demo_open")
    print("[demo] open fills =", len(fills1))

    # Close long: LIMIT SELL 2 @ 20005, matched at 20005
    o2 = oms.submit_order(symbol="TMF", side="SELL", qty=2, order_type="LIMIT", price=20005.0)
    fills2 = oms.match(o2, market_price=20005.0, reason="demo_close")
    print("[demo] close fills =", len(fills2))

    print("[demo] DONE. Check DB tables: orders/fills/trades")

if __name__ == "__main__":
    main()

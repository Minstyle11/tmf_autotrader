from __future__ import annotations
import json, sqlite3, uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from .models_v1 import Order, Fill, Trade, Position

# Conservative defaults (can be moved to config later)
MULTIPLIER_BY_SYMBOL = {"TMF": 10.0, "MXF": 50.0, "TXF": 200.0}
TAX_RATE_EQUITY_FUTURES = 0.00002  # per side

FEE_PER_SIDE_BY_SYMBOL = {
    "TMF": 8.0,   # exchange+clearing per side (from your demo: 4.8+3.2)
    "MXF": 0.0,
    "TXF": 0.0,
}

def _now_ms() -> str:
    return datetime.now().isoformat(timespec="milliseconds")

def _j(x) -> str:
    return json.dumps(x, ensure_ascii=False, default=str)

class PaperOMS:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.pos: Dict[str, Position] = {}
        self.open_trade: Dict[str, Trade] = {}  # symbol -> Trade

    # --- DB helpers ---
    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path))
        return con

    def _ins_order(self, o: Order):
        con = self._con()
        try:
            con.execute(
                "INSERT INTO orders(ts, broker_order_id, symbol, side, qty, price, order_type, status, meta_json) VALUES (?,?,?,?,?,?,?,?,?)",
                (o.ts, o.order_id, o.symbol, o.side, float(o.qty), None if o.price is None else float(o.price),
                 o.order_type, o.status, _j(o.meta)),
            )
            con.commit()
        finally:
            con.close()

    def _upd_order_status(self, order_id: str, status: str, filled_qty: float):
        con = self._con()
        try:
            # v1_1: merge meta_json (preserve stop_price / market_metrics / other fields)
            row = con.execute("SELECT meta_json FROM orders WHERE broker_order_id=?", (order_id,)).fetchone()
            base = {}
            if row and row[0]:
                try:
                    base = json.loads(row[0]) if isinstance(row[0], str) else {}
                except Exception:
                    base = {}
            if not isinstance(base, dict):
                base = {}
            base["filled_qty"] = float(filled_qty)
            con.execute(
                "UPDATE orders SET status=?, meta_json=? WHERE broker_order_id=?",
                (status, _j(base), order_id),
            )
            con.commit()
        finally:
            con.close()

    def _ins_fill(self, f: Fill):
        con = self._con()
        try:
            con.execute(
                "INSERT INTO fills(ts, broker_order_id, symbol, side, qty, price, fee, tax, meta_json) VALUES (?,?,?,?,?,?,?,?,?)",
                (f.ts, f.order_id, f.symbol, f.side, float(f.qty), float(f.price),
                 float(f.fee_ntd), float(f.tax_ntd), _j(f.meta)),
            )
            con.commit()
        finally:
            con.close()

    def _ins_trade(self, t: Trade):
        con = self._con()
        try:
            con.execute(
                "INSERT INTO trades(open_ts, close_ts, symbol, side, qty, entry, exit, pnl, pnl_pct, reason_open, reason_close, meta_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (t.open_ts, t.close_ts, t.symbol, t.side, float(t.qty), float(t.entry),
                 None if t.exit is None else float(t.exit),
                 None if t.pnl_ntd is None else float(t.pnl_ntd),
                 None if t.pnl_pct is None else float(t.pnl_pct),
                 t.reason_open, t.reason_close, _j(t.meta)),
            )
            con.commit()
        finally:
            con.close()

    def _upd_trade_close(self, symbol: str, close_ts: str, exit_px: float, pnl_ntd: float, pnl_pct: float, reason_close: str):
        con = self._con()
        try:
            con.execute(
                "UPDATE trades SET close_ts=?, exit=?, pnl=?, pnl_pct=?, reason_close=? WHERE symbol=? AND close_ts IS NULL ORDER BY id DESC LIMIT 1",
                (close_ts, float(exit_px), float(pnl_ntd), float(pnl_pct), reason_close, symbol),
            )
            con.commit()
        finally:
            con.close()

    # --- Cost helpers (per-side) ---
    def _per_side_cost(self, symbol: str, price: float, qty: float) -> tuple[float,float]:
        mult = MULTIPLIER_BY_SYMBOL.get(symbol, 1.0)
        notional = float(price) * float(mult) * float(qty)
        tax = notional * TAX_RATE_EQUITY_FUTURES
        fee = float(FEE_PER_SIDE_BY_SYMBOL.get(symbol, 0.0)) * float(qty)
        return fee, tax

    # --- Public API ---
    def place_order(self, *, symbol: str, side: str, qty: float, order_type: str, price=None, meta=None):
        """Compatibility alias for callers expecting place_order()."""
        return self.submit_order(symbol=symbol, side=side, qty=qty, order_type=order_type, price=price, meta=meta)


    def submit_order(self, *, symbol: str, side: str, qty: float, order_type: str, price: Optional[float]=None, meta: Optional[Dict[str,Any]]=None) -> Order:
        oid = uuid.uuid4().hex
        o = Order(
            order_id=oid,
            ts=_now_ms(),
            symbol=symbol,
            side=side,  # BUY/SELL
            qty=float(qty),
            order_type=order_type,  # MARKET/LIMIT
            price=None if price is None else float(price),
            status="NEW",
            meta=meta or {},
        )
        self._ins_order(o)
        return o

    def match(self, order: Order, *, market_price: float, liquidity_qty: Optional[float]=None, reason: str="match") -> list[Fill]:
        """Return fills (may be empty). Very conservative matching.
        - MARKET: fill immediately at market_price
        - LIMIT: BUY fills if market_price <= limit; SELL fills if market_price >= limit
        - liquidity_qty: max qty fill this call (supports partial fill)
        """
        px = float(market_price)
        remaining = float(order.qty - order.filled_qty)
        if remaining <= 0:
            return []

        ok = False
        if order.order_type == "MARKET":
            ok = True
        elif order.order_type == "LIMIT":
            if order.price is None:
                order.status = "REJECTED"
                self._upd_order_status(order.order_id, order.status, order.filled_qty)
                return []
            if order.side == "BUY" and px <= float(order.price):
                ok = True
            if order.side == "SELL" and px >= float(order.price):
                ok = True

        if not ok:
            return []

        fill_qty = remaining if liquidity_qty is None else min(remaining, float(liquidity_qty))
        if fill_qty <= 0:
            return []

        fee, tax = self._per_side_cost(order.symbol, px, fill_qty)
        fid = uuid.uuid4().hex
        f = Fill(
            fill_id=fid,
            ts=_now_ms(),
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            qty=float(fill_qty),
            price=px,
            fee_ntd=float(fee),
            tax_ntd=float(tax),
            meta={"reason": reason, "order_meta": (order.meta or {})},
        )
        self._ins_fill(f)

        order.filled_qty += fill_qty
        if order.filled_qty + 1e-9 >= order.qty:
            order.status = "FILLED"
        else:
            order.status = "PARTIALLY_FILLED"
        self._upd_order_status(order.order_id, order.status, order.filled_qty)

        # Position / Trade book (single-position per symbol v1)
        self._apply_fill_to_position_and_trade(f)

        return [f]

    def _apply_fill_to_position_and_trade(self, f: Fill):
        sym = f.symbol
        mult = MULTIPLIER_BY_SYMBOL.get(sym, 1.0)
        pos = self.pos.get(sym) or Position(symbol=sym)
        self.pos[sym] = pos

        side = f.side  # BUY/SELL
        signed_qty = f.qty if side == "BUY" else -f.qty

        # If no position -> open
        if pos.qty == 0.0:
            pos.qty = abs(signed_qty)
            pos.side = "LONG" if signed_qty > 0 else "SHORT"
            pos.avg_price = f.price
            pos.open_ts = f.ts

            t = Trade(
                trade_id=uuid.uuid4().hex,
                open_ts=f.ts,
                close_ts=None,
                symbol=sym,
                side=pos.side,
                qty=pos.qty,
                entry=pos.avg_price,
                reason_open="fill_open",
                meta={"multiplier": mult, "order_meta": (f.meta.get("order_meta") if isinstance(f.meta, dict) else {})},
            )
            self.open_trade[sym] = t
            self._ins_trade(t)
            return

        # Same direction add -> avg
        same_dir = (pos.side == "LONG" and signed_qty > 0) or (pos.side == "SHORT" and signed_qty < 0)
        if same_dir:
            new_qty = pos.qty + abs(signed_qty)
            pos.avg_price = (pos.avg_price * pos.qty + f.price * abs(signed_qty)) / new_qty
            pos.qty = new_qty
            # NOTE: for v1 we keep one trade row; not splitting entries
            return

        # Opposite direction -> reduce/close (v1: support full close; if over-close, flip and open new)
        reduce_qty = abs(signed_qty)
        if reduce_qty < pos.qty - 1e-9:
            # partial close: compute pnl on closed part but keep trade open (store in meta only v1)
            # We keep it simple for v1: do not emit trade close until flat.
            pos.qty = pos.qty - reduce_qty
            return

        # close to flat (or flip)
        closed_qty = pos.qty
        entry = pos.avg_price
        exit_px = f.price
        sign = 1.0 if pos.side == "LONG" else -1.0
        pnl_ntd = (exit_px - entry) * sign * closed_qty * mult
        pnl_pct = 0.0 if entry <= 0 else (pnl_ntd / (entry * closed_qty * mult))

        close_ts = f.ts
        reason_close = "fill_close"
        try:
            if isinstance(f.meta, dict) and f.meta.get("reason"):
                reason_close = str(f.meta.get("reason"))
        except Exception:
            pass
        self._upd_trade_close(sym, close_ts, exit_px, pnl_ntd, pnl_pct, reason_close)

        # If flip (reduce_qty > old qty), open new position with leftover
        leftover = reduce_qty - closed_qty
        pos.qty = 0.0
        pos.side = None
        pos.avg_price = 0.0
        pos.open_ts = None
        self.open_trade.pop(sym, None)

        if leftover > 1e-9:
            # open new position in opposite direction
            new_side = "LONG" if signed_qty > 0 else "SHORT"
            pos.qty = leftover
            pos.side = new_side
            pos.avg_price = f.price
            pos.open_ts = f.ts
            t = Trade(
                trade_id=uuid.uuid4().hex,
                open_ts=f.ts,
                close_ts=None,
                symbol=sym,
                side=new_side,
                qty=pos.qty,
                entry=pos.avg_price,
                reason_open="fill_flip_open",
                meta={"multiplier": mult, "order_meta": (f.meta.get("order_meta") if isinstance(f.meta, dict) else {})},
            )
            self.open_trade[sym] = t
            self._ins_trade(t)

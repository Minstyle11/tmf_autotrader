from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# NOTE: Python 3.9.6 compatible

@dataclass(frozen=True)
class MarketMetrics:
    bid: float
    ask: float
    spread_points: float
    atr_points: Optional[float]
    liquidity_score: float
    source: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bid": float(self.bid),
            "ask": float(self.ask),
            "spread_points": float(self.spread_points),
            "atr_points": (None if self.atr_points is None else float(self.atr_points)),
            "liquidity_score": float(self.liquidity_score),
            "source": dict(self.source or {}),
        }


def _loads(s: Any) -> Dict[str, Any]:
    if not s:
        return {}
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s) if isinstance(s, str) else {}
    except Exception:
        return {}


def _pick_latest_event_by_code(
    con: sqlite3.Connection,
    *,
    kind: str,
    code: str,
    scan_limit: int = 500,
) -> Optional[Tuple[int, str, Dict[str, Any]]]:
    """
    events payload_json is stored as TEXT; we conservatively scan the last N rows for this kind
    and match payload['code'] == code.
    Returns: (event_id, ts, payload_dict) or None
    """
    rows = con.execute(
        "SELECT id, ts, payload_json FROM events WHERE kind=? ORDER BY id DESC LIMIT ?",
        (kind, int(scan_limit)),
    ).fetchall()
    for r in rows:
        eid = int(r[0])
        ts = str(r[1])
        payload = _loads(r[2])
        if str(payload.get("code", "")) == str(code):
            return (eid, ts, payload)
    return None


def _compute_liquidity_score(payload: Dict[str, Any]) -> float:
    """
    Simple, conservative liquidity proxy from bid/ask top levels.
    We keep it scale-free for now: sum of first 5 level volumes (bid+ask).
    """
    bv = payload.get("bid_volume") or []
    av = payload.get("ask_volume") or []
    try:
        bv5 = [float(x) for x in list(bv)[:5]]
        av5 = [float(x) for x in list(av)[:5]]
        return float(sum(bv5) + sum(av5))
    except Exception:
        return 0.0


def _atr_from_bars_1m(
    con: sqlite3.Connection,
    *,
    asset_class: str,
    symbol: str,
    n: int = 20,
) -> Optional[float]:
    """
    ATR in 'points' computed from bars_1m.
    Uses classic True Range:
      TR = max(h-l, abs(h-prev_c), abs(l-prev_c))
    ATR = SMA(TR, n) over last n bars (requires n+1 closes).
    """
    rows = con.execute(
        "SELECT ts_min, o, h, l, c FROM bars_1m WHERE asset_class=? AND symbol=? ORDER BY ts_min DESC LIMIT ?",
        (asset_class, symbol, int(n) + 1),
    ).fetchall()
    if not rows or len(rows) < 2:
        return None

    # rows are DESC; reverse to chronological
    rows = list(reversed(rows))

    trs: List[float] = []
    prev_c = None
    for i, r in enumerate(rows):
        try:
            h = float(r[2]); l = float(r[3]); c = float(r[4])
        except Exception:
            continue
        if prev_c is None:
            prev_c = c
            continue
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(float(tr))
        prev_c = c

    if not trs:
        return None

    # Use last n TRs (already at most n because we limited n+1 bars)
    take = trs[-int(n):]
    return float(sum(take) / float(len(take))) if take else None


def get_market_metrics_from_db(
    *,
    db_path: str,
    fop_code: str,
    bars_symbol_for_atr: Optional[str] = None,
    atr_n: int = 20,
) -> Dict[str, Any]:
    """
    Fetch latest bidask_fop_v1 for `fop_code` and compute:
      - bid/ask from level 1 prices
      - spread_points = ask - bid
      - liquidity_score from top-5 volumes
      - atr_points from bars_1m (FOP, symbol=bars_symbol_for_atr or fop_code)
    Returns a dict suitable to be embedded into order meta as meta['market_metrics'].
    """
    con = sqlite3.connect(db_path)
    try:
        ev = _pick_latest_event_by_code(con, kind="bidask_fop_v1", code=fop_code)
        if not ev:
            return {}

        event_id, ts, payload = ev
        bid_prices = payload.get("bid_price") or []
        ask_prices = payload.get("ask_price") or []

        bid = float(bid_prices[0]) if len(bid_prices) >= 1 else None
        ask = float(ask_prices[0]) if len(ask_prices) >= 1 else None


        if bid is None or ask is None:
            return {}

        spread_points = None
        if bid is not None and ask is not None:
            spread_points = float(ask - bid)

        liq = _compute_liquidity_score(payload)

        bars_sym = str(bars_symbol_for_atr or fop_code)
        atr = _atr_from_bars_1m(con, asset_class="FOP", symbol=bars_sym, n=int(atr_n))

        mm = MarketMetrics(
            bid=float(bid) if bid is not None else 0.0,
            ask=float(ask) if ask is not None else 0.0,
            spread_points=float(spread_points) if spread_points is not None else 0.0,
            atr_points=atr,
            liquidity_score=float(liq),
            source={
                "bidask_event_id": int(event_id),
                "bidask_ts": ts,
                "fop_code": str(fop_code),
                "atr_symbol": bars_sym,
                "atr_n": int(atr_n),
            },
        )
        return mm.to_dict()
    finally:
        con.close()

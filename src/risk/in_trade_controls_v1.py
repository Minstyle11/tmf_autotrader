from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from src.oms.paper_oms_v1 import PaperOMS


@dataclass(frozen=True)
class InTradeConfigV1:
    # If open trade has been open longer than this -> force close.
    time_stop_seconds: float = 300.0  # 5 minutes default (conservative for demo)
    # Use stop_price from trade.meta.order_meta.stop_price if present.
    strict_require_stop: int = 1


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _extract_stop_price(open_trade_meta: Dict[str, Any]) -> Optional[float]:
    """
    We store order_meta inside trade.meta['order_meta'] (copied from order meta at fill).
    Expected: order_meta may contain stop_price.
    """
    try:
        om = open_trade_meta.get("order_meta") or {}
        sp = om.get("stop_price")
        return None if sp is None else float(sp)
    except Exception:
        return None


def run_intrade_once(
    *,
    oms: PaperOMS,
    symbol: str,
    market_price: float,
    cfg: Optional[InTradeConfigV1] = None,
) -> Dict[str, Any]:
    """
    Check open position/trade for symbol and force-close if:
      - stop-loss hit (based on stop_price in trade.meta.order_meta)
      - time-stop exceeded
    Close mechanism: submit opposite MARKET order and match immediately.
    """
    cfg = cfg or InTradeConfigV1()
    pos = oms.pos.get(symbol)
    if not pos or pos.qty <= 0:
        return {"ok": True, "action": "NO_POSITION"}

    t = oms.open_trade.get(symbol)
    if not t:
        return {"ok": True, "action": "NO_OPEN_TRADE"}

    # Time-stop
    open_dt = _parse_iso(str(t.open_ts))
    if open_dt is not None and cfg.time_stop_seconds is not None and cfg.time_stop_seconds >= 0:
        age = (datetime.now() - open_dt).total_seconds()
        if age >= float(cfg.time_stop_seconds):
            side_close = "SELL" if pos.side == "LONG" else "BUY"
            o = oms.submit_order(
                symbol=symbol,
                side=side_close,
                qty=float(pos.qty),
                order_type="MARKET",
                price=None,
                meta={"reason": "risk_time_stop"},
            )
            fills = oms.match(o, market_price=float(market_price), liquidity_qty=float(pos.qty), reason="risk_time_stop")
            return {"ok": True, "action": "CLOSE_TIME_STOP", "fills": len(fills)}

    # Stop-loss
    sp = _extract_stop_price(t.meta or {})
    if cfg.strict_require_stop == 1 and sp is None:
        return {"ok": False, "action": "STOP_MISSING", "err": "strict_require_stop=1 but stop_price missing in trade.meta.order_meta"}

    if sp is not None:
        hit = False
        if pos.side == "LONG" and float(market_price) <= float(sp):
            hit = True
        if pos.side == "SHORT" and float(market_price) >= float(sp):
            hit = True
        if hit:
            side_close = "SELL" if pos.side == "LONG" else "BUY"
            o = oms.submit_order(
                symbol=symbol,
                side=side_close,
                qty=float(pos.qty),
                order_type="MARKET",
                price=None,
                meta={"reason": "risk_stop"},
            )
            fills = oms.match(o, market_price=float(market_price), liquidity_qty=float(pos.qty), reason="risk_stop")
            return {"ok": True, "action": "CLOSE_STOP", "fills": len(fills), "stop_price": sp}

    return {"ok": True, "action": "HOLD"}

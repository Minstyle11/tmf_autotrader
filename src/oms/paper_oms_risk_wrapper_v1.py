from __future__ import annotations
import json
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Optional, Dict, Any

from src.risk.risk_engine_v1 import RiskEngineV1, RiskVerdict


class PaperOMSRiskWrapperV1:
    """
    Wrap existing Paper OMS and enforce pre-trade risk gates BEFORE calling OMS.
    If rejected:
      - write an order row with status=REJECTED
      - return a small dict describing the rejection
    """

    def __init__(self, *, paper_oms, risk: RiskEngineV1, db_path: str):
        self.oms = paper_oms
        self.risk = risk
        self.db_path = db_path

    def _now(self) -> str:
        return datetime.now().isoformat(timespec="milliseconds")

    def _insert_rejected_order(self, *, symbol: str, side: str, qty: float, price: Optional[float], order_type: str, verdict: RiskVerdict, meta: Optional[Dict[str, Any]] = None):
        import sqlite3
        con = sqlite3.connect(self.db_path)
        try:
            broker_order_id = uuid.uuid4().hex
            ts = self._now()
            base = meta if isinstance(meta, dict) else {}
            base = dict(base)
            base["risk_verdict"] = {"ok": verdict.ok, "code": verdict.code, "reason": verdict.reason, "details": verdict.details}

            con.execute(
                "INSERT INTO orders(ts, broker_order_id, symbol, side, qty, price, order_type, status, meta_json) VALUES(?,?,?,?,?,?,?,?,?)",
                (ts, broker_order_id, symbol, side, float(qty), (float(price) if price is not None else None), order_type, "REJECTED", json.dumps(base, ensure_ascii=False)),
            )
            con.commit()
            return broker_order_id
        finally:
            con.close()

    def place_order(self, *, symbol: str, side: str, qty: float, order_type: str, price: Optional[float] = None, meta: Optional[Dict[str, Any]] = None):
        meta = meta or {}
        entry_price = float(price) if (price is not None) else float(meta.get("ref_price", 0.0) or 0.0)

        verdict = self.risk.check_pre_trade(symbol=symbol, side=side, qty=qty, entry_price=entry_price, meta=meta)
        if not verdict.ok:
            oid = self._insert_rejected_order(symbol=symbol, side=side, qty=qty, price=price, order_type=order_type, verdict=verdict, meta=meta)
            return {"ok": False, "status": "REJECTED", "broker_order_id": oid, "risk": {"code": verdict.code, "reason": verdict.reason, "details": verdict.details}}

        # persist PASS verdict into order meta for audit
        meta_ok = dict(meta) if isinstance(meta, dict) else {}
        if "risk_verdict" not in meta_ok:
            meta_ok["risk_verdict"] = {
                "ok": True,
                "code": verdict.code,
                "reason": verdict.reason,
                # keep details (may include per_trade_risk_ntd/cfg); ok for now
                "details": verdict.details,
            }

        # pass-through to underlying OMS
        return self.oms.place_order(symbol=symbol, side=side, qty=qty, order_type=order_type, price=price, meta=meta_ok)

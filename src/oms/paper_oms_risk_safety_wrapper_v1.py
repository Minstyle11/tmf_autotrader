from __future__ import annotations
from dataclasses import asdict
from typing import Any, Dict, Optional, Union

from src.oms.paper_oms_v1 import PaperOMS
from src.risk.risk_engine_v1 import RiskEngineV1
from src.safety.system_safety_v1 import SystemSafetyEngineV1


class PaperOMSRiskSafetyWrapperV1:
    """
    v1 wrapper order: SAFETY first (disconnect/session/expiry guards) -> RISK -> place to OMS.
    Returns:
      - dict for REJECTED with code/reason/details
      - Order object for accepted (pass-through from PaperOMS)
    """
    def __init__(self, *, paper_oms: PaperOMS, risk: RiskEngineV1, safety: SystemSafetyEngineV1, db_path: str):
        self.paper_oms = paper_oms
        self.risk = risk
        self.safety = safety
        self.db_path = str(db_path)


    def _now(self) -> str:
        # milliseconds for better ordering in logs
        from datetime import datetime
        return datetime.now().isoformat(timespec="milliseconds")

    def _insert_rejected_order(
        self,
        *,
        symbol: str,
        side: str,
        qty: float,
        price,
        order_type: str,
        meta,
        safety_verdict=None,
        risk_verdict=None,
    ) -> str:
        """
        v18 audit/replay requirement:
          - every REJECT must be persisted into orders with status=REJECTED
          - include safety_verdict / risk_verdict into meta_json for post-mortem
        """
        import json, uuid, sqlite3

        con = sqlite3.connect(self.db_path)
        try:
            broker_order_id = uuid.uuid4().hex
            ts = self._now()

            base = meta if isinstance(meta, dict) else {}
            base = dict(base)

            if safety_verdict is not None:
                base["safety_verdict"] = {
                    "ok": bool(getattr(safety_verdict, "ok", False)),
                    "code": getattr(safety_verdict, "code", None),
                    "reason": getattr(safety_verdict, "reason", None),
                    "details": getattr(safety_verdict, "details", None),
                }
            if risk_verdict is not None:
                base["risk_verdict"] = {
                    "ok": bool(getattr(risk_verdict, "ok", False)),
                    "code": getattr(risk_verdict, "code", None),
                    "reason": getattr(risk_verdict, "reason", None),
                    "details": getattr(risk_verdict, "details", None),
                }

            con.execute(
                "INSERT INTO orders(ts, broker_order_id, symbol, side, qty, price, order_type, status, meta_json) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    ts,
                    broker_order_id,
                    symbol,
                    side,
                    float(qty),
                    (float(price) if price is not None else None),
                    order_type,
                    "REJECTED",
                    json.dumps(base, ensure_ascii=False),
                ),
            )
            con.commit()
            return broker_order_id
        finally:
            con.close()
    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        qty: float,
        order_type: str,
        price: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], Any]:
        meta = meta or {}

        # 1) system safety
        sv = self.safety.check_pre_trade(meta=meta)
        if not sv.ok:
            oid = self._insert_rejected_order(
                symbol=symbol,
                side=side,
                qty=float(qty),
                price=price,
                order_type=order_type,
                meta=meta,
                safety_verdict=sv,
                risk_verdict=None,
            )
            return {
                "ok": False,
                "status": "REJECTED",
                "broker_order_id": oid,
                "safety": {"code": sv.code, "reason": sv.reason, "details": sv.details},
            }

        # 2) risk pre-trade
        entry_price = float(meta.get("ref_price", 0.0)) if meta.get("ref_price") is not None else 0.0
        rv = self.risk.check_pre_trade(symbol=symbol, side=side, qty=float(qty), entry_price=float(entry_price), meta=meta)
        if not rv.ok:
            oid = self._insert_rejected_order(
                symbol=symbol,
                side=side,
                qty=float(qty),
                price=price,
                order_type=order_type,
                meta=meta,
                safety_verdict=sv,
                risk_verdict=rv,
            )
            return {
                "ok": False,
                "status": "REJECTED",
                "broker_order_id": oid,
                "risk": {"code": rv.code, "reason": rv.reason, "details": rv.details},
            }

        # 3) accept -> submit to paper OMS
        # 3) accept -> submit to paper OMS (persist PASS verdicts into meta for audit)
        meta_ok = dict(meta) if isinstance(meta, dict) else {}
        if "safety_verdict" not in meta_ok:
            meta_ok["safety_verdict"] = {"ok": True, "code": sv.code, "reason": sv.reason, "details": sv.details}
        if "risk_verdict" not in meta_ok:
            meta_ok["risk_verdict"] = {"ok": True, "code": rv.code, "reason": rv.reason, "details": rv.details}

        return self.paper_oms.place_order(symbol=symbol, side=side, qty=float(qty), order_type=order_type, price=price, meta=meta_ok)

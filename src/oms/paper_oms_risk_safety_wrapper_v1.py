from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.oms.paper_oms_v1 import PaperOMS
from src.risk.risk_engine_v1 import RiskEngineV1
from src.safety.system_safety_v1 import SystemSafetyEngineV1
from execution.taifex_preflight_v1 import check_taifex_preflight
from execution.tw_market_calendar_v1 import market_open_verdict

from execution.reject_taxonomy import load_policy, decision_from_verdict
from src.execution.order_result_types import is_rejected_order



def _ensure_intent_envelope(meta: dict) -> dict:
    # Best-effort intent envelope enrichment for auditability; never raises.
    try:
        if not isinstance(meta, dict):
            return meta
        intent = meta.get('intent')
        if not isinstance(intent, dict):
            intent = {}

        def pick(*keys):
            for k in keys:
                v = meta.get(k)
                if v is not None:
                    return v
            return None

        corr = pick('correlation_id', 'corr_id') or intent.get('correlation_id')
        caus = pick('causation_id', 'cause_id') or intent.get('causation_id')
        if not corr:
            import uuid
            corr = str(uuid.uuid4())

        intent.setdefault('correlation_id', corr)
        if caus:
            intent.setdefault('causation_id', caus)

        prov = {
            'strategy_id': pick('strategy_id', 'strategy', 'strat_id') or intent.get('strategy_id'),
            'signal_id':   pick('signal_id', 'signal', 'sig_id') or intent.get('signal_id'),
            'runner':      pick('runner', 'runner_id') or intent.get('runner'),
            'source_file': pick('source_file', 'src_file', 'source') or intent.get('source_file'),
        }
        for k, v in prov.items():
            if v is not None and k not in intent:
                intent[k] = v

        stop = pick('stop', 'stop_spec', 'stop_cfg', 'stop_config', 'stop_loss')
        if stop is None:
            stop = intent.get('stop')
        if stop is not None and 'stop' not in intent:
            intent['stop'] = stop

        meta['intent'] = intent
        return meta
    except Exception:
        return meta


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
        self._reject_policy = None  # lazy-loaded


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

            verdict = None
            decision = None
            action = None
            reject_decision = base.get('reject_decision') if isinstance(base, dict) else None
            if isinstance(reject_decision, dict):
                verdict = reject_decision.get('code')
                decision = reject_decision.get('domain')
                action = reject_decision.get('action')
            else:
                # fallback best-effort
                if risk_verdict is not None:
                    verdict = getattr(risk_verdict, 'code', None)
                    decision = 'RISK'
                    action = 'REJECT'
                elif safety_verdict is not None:
                    verdict = getattr(safety_verdict, 'code', None)
                    decision = 'SAFETY'
                    action = 'REJECT'

            con.execute(
                "INSERT INTO orders(ts, broker_order_id, symbol, side, qty, price, order_type, status, verdict, decision, action, meta_json) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    ts,
                    broker_order_id,
                    symbol,
                    side,
                    float(qty),
                    (float(price) if price is not None else None),
                    order_type,
                    "REJECTED",
                    verdict,
                    decision,
                    action,
                    json.dumps(base, ensure_ascii=False),
                ),
            )
            con.commit()
            return broker_order_id
        finally:
            con.close()

    def _load_reject_policy(self) -> Dict[str, Any]:
        if self._reject_policy is not None:
            return self._reject_policy
        # repo root is 3 levels above this file: tmf_autotrader/src/oms/...
        repo = Path(__file__).resolve().parents[2]
        pol_path = repo / "execution" / "reject_policy.yaml"
        self._reject_policy = load_policy(str(pol_path))
        return self._reject_policy

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
        try:
            sv = self.safety.check_pre_trade(meta=meta)
        except AttributeError:
            # Compat: some safety engines expose check(meta=...) or check(meta)
            try:
                sv = self.safety.check(meta=meta)
            except TypeError:
                sv = self.safety.check(meta)

        if not sv.ok:

            pol = self._load_reject_policy()
            dec = decision_from_verdict({"ok": bool(getattr(sv,"ok",False)), "code": getattr(sv,"code",None), "reason": getattr(sv,"reason",None), "details": getattr(sv,"details",{})}, policy=pol)
            # persist decision into meta for v18 audit
            try:
                meta = dict(meta) if isinstance(meta, dict) else {}
                meta = _ensure_intent_envelope(meta)
                meta.setdefault("reject_decision", {"ok": dec.ok, "code": dec.code, "domain": dec.domain, "severity": dec.severity, "action": dec.action, "reason": dec.reason, "details": dec.details})
            except Exception:
                pass
            # execute safety actions (COOLDOWN/KILL) via SystemSafetyEngineV1 state
            try:
                if dec.action == "COOLDOWN":
                    cd_sec = int(meta.get("cooldown_seconds", 60)) if isinstance(meta, dict) else 60
                    self.safety.request_cooldown(seconds=cd_sec, code=dec.code, reason=dec.reason, details=dec.details)
                elif dec.action == "KILL":
                    self.safety.request_kill(code=dec.code, reason=dec.reason, details=dec.details)
            except Exception:
                pass
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


        # 1.4) Market calendar gate (TWSE/TAIFEX holidays/weekends/session gaps) (v18.1-C)
        mv = market_open_verdict(meta=meta)
        if not mv.ok:
            pol = self._load_reject_policy()
            dec = decision_from_verdict({"ok": False, "code": mv.code, "reason": mv.reason, "details": mv.details}, policy=pol)
            try:
                meta = dict(meta) if isinstance(meta, dict) else {}
                meta = _ensure_intent_envelope(meta)
                meta.setdefault("reject_decision", {"ok": dec.ok, "code": dec.code, "domain": dec.domain, "severity": dec.severity, "action": dec.action, "reason": dec.reason, "details": dec.details})
                meta.setdefault("market_calendar_verdict", {"ok": mv.ok, "code": mv.code, "reason": mv.reason, "details": mv.details})
            except Exception:
                pass
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
                "safety": {"code": mv.code, "reason": mv.reason, "details": mv.details},
            }

        # 1.5) TAIFEX preflight hard constraints (v18.1-B)

        pv = check_taifex_preflight(symbol=symbol, side=side, qty=float(qty), order_type=order_type, price=price, meta=meta)

        # v18 audit: always persist preflight verdict into meta once SAFETY passed.
        # This ensures Risk REJECTs still carry preflight_verdict for post-mortem.
        try:
            meta = dict(meta) if isinstance(meta, dict) else {}
            meta.setdefault("preflight_verdict", {"ok": bool(pv.ok), "code": pv.code, "reason": pv.reason, "details": pv.details})
        except Exception:
            pass
        if not pv.ok:
            pol = self._load_reject_policy()
            dec = decision_from_verdict({"ok": False, "code": pv.code, "reason": pv.reason, "details": pv.details}, policy=pol)

            # persist decision + preflight verdict into meta for v18 audit
            try:
                meta = dict(meta) if isinstance(meta, dict) else {}
                meta = _ensure_intent_envelope(meta)
                meta.setdefault("reject_decision", {"ok": dec.ok, "code": dec.code, "domain": dec.domain, "severity": dec.severity, "action": dec.action, "reason": dec.reason, "details": dec.details})
                meta.setdefault("preflight_verdict", {"ok": pv.ok, "code": pv.code, "reason": pv.reason, "details": pv.details})
            except Exception:
                pass

            # policy-driven SPLIT (TAIFEX market qty limit)
            if str(dec.action).upper() == "SPLIT" and str(pv.code) == "EXEC_TAIFEX_MKT_QTY_LIMIT":
                import math
                lim = float((pv.details or {}).get("limit", 0) or 0)
                if lim <= 0:
                    # fallback to TAIFEX documented limits (day=10, after-hours=5)
                    sess = str((pv.details or {}).get("session_hint", "") or "").upper()
                    lim = 5.0 if sess in {"NIGHT","AFTER_HOURS","AH"} else 10.0


                parent_id = f"SPLIT_{self._now()}"
                results = []
                remaining = float(qty)

                # adaptive split: must satisfy both TAIFEX limit and RiskEngine per-order qty limit
                i = 0
                hard_max_children = 2000  # safety bound
                while remaining > 0 and i < hard_max_children:
                    step = lim if remaining > lim else remaining

                    meta_child = dict(meta) if isinstance(meta, dict) else {}
                    meta_child.setdefault("split_parent_id", parent_id)
                    meta_child.setdefault("split_index", i)
                    meta_child.setdefault("split_limit", lim)

                    # Attempt submit through full wrapper gates
                    res = self.place_order(symbol=symbol, side=side, qty=float(step), order_type=order_type, price=price, meta=meta_child)
                    results.append(res)

                    # If rejected due to Risk qty cap, adapt lim downward and retry WITHOUT consuming remaining
                    if isinstance(res, dict) and (not bool(res.get("ok", True))) and str(res.get("status","")) == "REJECTED":
                        r = res.get("risk") if isinstance(res.get("risk"), dict) else {}
                        if str(r.get("code","")) == "RISK_QTY_LIMIT":
                            try:
                                mx = float((r.get("details") or {}).get("max_qty_per_order", 0) or 0)
                            except Exception:
                                mx = 0.0
                            if mx > 0 and mx < lim:
                                lim = mx  # tighten split size
                                # drop this failed attempt record? keep for audit; but do not progress
                                continue
                        # other rejections -> stop
                        return {
                            "ok": False,
                            "status": "REJECTED",
                            "exec": {"code": pv.code, "reason": pv.reason, "details": {"policy_action": dec.action, "limit": lim, "split_parent_id": parent_id, "children": results}},
                        }

                    # success path: consume remaining and advance index
                    remaining -= float(step)
                    i += 1

                # finalize
                if remaining > 0:
                    return {
                        "ok": False,
                        "status": "REJECTED",
                        "exec": {"code": "EXEC_SPLIT_LOOP_GUARD", "reason": "split loop exceeded safety bound; refusing to continue", "details": {"split_parent_id": parent_id, "children": results, "limit": lim}},
                    }

                # fill split_total for all children meta (best-effort; children may be dict or order objects)
                n = i
                # v18 audit: INSERT split parent row (orders)
                # Record the split event itself as a parent row for audit/replay.
                # Children orders are inserted separately by the normal success-path insert logic.
                try:
                    import sqlite3, json
                    con = sqlite3.connect(self.db_path)
                    try:
                        row = con.execute("SELECT 1 FROM orders WHERE broker_order_id=? LIMIT 1", (parent_id,)).fetchone()
                        if row is None:
                            ts = self._now()
                            meta_parent = dict(meta) if isinstance(meta, dict) else {}
                            meta_parent = _ensure_intent_envelope(meta_parent)
                            meta_parent.setdefault("split_parent_id", parent_id)
                            meta_parent.setdefault("split_limit", float(lim))
                            meta_parent.setdefault("split_requested_qty", float(qty))
                            meta_parent.setdefault("split_children", results)
                            con.execute(
                                "INSERT INTO orders(ts, broker_order_id, symbol, side, qty, price, order_type, status, verdict, decision, action, meta_json) "
                                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                                (
                                    ts,
                                    parent_id,
                                    symbol,
                                    side,
                                    float(qty),
                                    (float(price) if price is not None else None),
                                    order_type,
                                    "SPLIT_SUBMITTED",
                                    str(pv.code),
                                    str(dec.domain),
                                    str(dec.action),
                                    json.dumps(meta_parent, ensure_ascii=False),
                                ),
                            )
                            con.commit()
                    finally:
                        con.close()
                except Exception:
                    # Audit must not break execution path
                    pass

                return {
                    "ok": True,
                    "status": "SPLIT_SUBMITTED",
                    "exec": {"code": "OK_SPLIT", "reason": f"split market order into {n} children (limit={lim})", "details": {"split_parent_id": parent_id, "children": results, "limit": lim}},
                }

            # default: reject and persist as REJECTED
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
                "exec": {"code": pv.code, "reason": pv.reason, "details": pv.details, "policy_action": dec.action},
            }


        # 2) risk pre-trade
        entry_price = float(meta.get("ref_price", 0.0)) if meta.get("ref_price") is not None else 0.0
        try:
            rv = self.risk.check_pre_trade(symbol=symbol, side=side, qty=float(qty), entry_price=float(entry_price), meta=meta)
        except TypeError:
            # Compat: older risk engines may not accept entry_price= kw.
            # Try positional first, then try price= kw as a common alternative.
            try:
                rv = self.risk.check_pre_trade(symbol, side, float(qty), float(entry_price), meta)
            except TypeError:
                rv = self.risk.check_pre_trade(symbol=symbol, side=side, qty=float(qty), price=float(entry_price), meta=meta)
        if not rv.ok:

            pol = self._load_reject_policy()
            dec = decision_from_verdict({"ok": bool(getattr(rv,"ok",False)), "code": getattr(rv,"code",None), "reason": getattr(rv,"reason",None), "details": getattr(rv,"details",{})}, policy=pol)
            # persist decision into meta for v18 audit
            try:
                meta = dict(meta) if isinstance(meta, dict) else {}
                meta = _ensure_intent_envelope(meta)
                meta.setdefault("reject_decision", {"ok": dec.ok, "code": dec.code, "domain": dec.domain, "severity": dec.severity, "action": dec.action, "reason": dec.reason, "details": dec.details})
            except Exception:
                pass
            # execute safety actions (COOLDOWN/KILL) via SystemSafetyEngineV1 state
            try:
                if dec.action == "COOLDOWN":
                    cd_sec = int(meta.get("cooldown_seconds", 60)) if isinstance(meta, dict) else 60
                    self.safety.request_cooldown(seconds=cd_sec, code=dec.code, reason=dec.reason, details=dec.details)
                elif dec.action == "KILL":
                    self.safety.request_kill(code=dec.code, reason=dec.reason, details=dec.details)
            except Exception:
                pass
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
                "safety": {"code": sv.code, "reason": sv.reason, "details": sv.details},
                "risk": {"code": rv.code, "reason": rv.reason, "details": rv.details},
            }

        # 3) accept -> submit to paper OMS
        # 3) accept -> submit to paper OMS (persist PASS verdicts into meta for audit)
        meta_ok = dict(meta) if isinstance(meta, dict) else {}
        meta_ok = _ensure_intent_envelope(meta_ok)
        if "safety_verdict" not in meta_ok:
            meta_ok["safety_verdict"] = {"ok": True, "code": sv.code, "reason": sv.reason, "details": sv.details}
        if "risk_verdict" not in meta_ok:
            meta_ok["risk_verdict"] = {"ok": True, "code": rv.code, "reason": rv.reason, "details": rv.details}

        if "preflight_verdict" not in meta_ok:
            meta_ok["preflight_verdict"] = {"ok": True, "code": "OK", "reason": "taifex preflight pass", "details": {}}

        order = self.paper_oms.place_order(symbol=symbol, side=side, qty=float(qty), order_type=order_type, price=price, meta=meta_ok)

        # v18: persist allow decision into orders(verdict/decision/action) for audit/statistics
        try:
            # NOTE: decision_from_verdict returns an object (not dict). Use getattr() for safety.
            pol = self._load_reject_policy()
            ok_dec = decision_from_verdict({
                'ok': True,
                'code': 'OK',
                'reason': 'pre-trade pass',
                'details': {},
            }, policy=pol)

            # Paper OMS may return dict/object with different id field names.
            broker_order_id = getattr(order, 'broker_order_id', None)
            if broker_order_id is None:
                broker_order_id = getattr(order, 'order_id', None)
            if broker_order_id is None and isinstance(order, dict):
                broker_order_id = order.get('broker_order_id') or order.get('order_id')
            if broker_order_id is None and isinstance(order, dict):
                broker_order_id = order.get('broker_order_id') or order.get('order_id') or order.get('id')

            if broker_order_id:
                import sqlite3, json
                con = sqlite3.connect(self.db_path)
                try:
                    # v18 audit: if this broker_order_id does NOT exist yet, INSERT a row now.
                    row = con.execute("SELECT 1 FROM orders WHERE broker_order_id=? LIMIT 1", (broker_order_id,)).fetchone()
                    if row is None:
                        ts = self._now()
                        # status best-effort from Paper OMS response
                        status = None
                        if isinstance(order, dict):
                            status = order.get("status")
                        if status is None:
                            status = getattr(order, "status", None)
                        if status is None:
                            status = "SUBMITTED"
                        con.execute(
                            "INSERT INTO orders(ts, broker_order_id, symbol, side, qty, price, order_type, status, verdict, decision, action, meta_json) "
                            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (
                                ts,
                                broker_order_id,
                                symbol,
                                side,
                                float(qty),
                                (float(price) if price is not None else None),
                                order_type,
                                status,
                                getattr(ok_dec, "code", None),
                                getattr(ok_dec, "domain", None),
                                getattr(ok_dec, "action", None),
                                json.dumps(meta_ok, ensure_ascii=False),
                            ),
                        )
                        con.commit()

                    # Keep existing UPDATE for backward compatibility (in case row was created elsewhere)
                    con.execute(
                        'UPDATE orders SET verdict=?, decision=?, action=? WHERE broker_order_id=?',
                        (
                            getattr(ok_dec, 'code', None),
                            getattr(ok_dec, 'domain', None),
                            getattr(ok_dec, 'action', None),
                            broker_order_id,
                        ),
                    )
                    con.commit()
                finally:
                    con.close()
        except Exception:
            # never break trading flow for audit
            pass

        return order

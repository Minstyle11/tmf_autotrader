# TMF AutoTrader — Learning Governance v1 (OFFICIAL-LOCKED compatible)
# Goals (v18.1):
# - drift / non-stationarity / online learning must be: controllable, rollbackable, freezable
# - minimal safe modes: Frozen / Shadow / Promote
# - Shadow produces intents + reports; MUST NOT affect orders
# - Promote only allowed during release window + canary + rollback-on-drift

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
import json, os
from datetime import datetime, timezone

RUNTIME_STATE = Path("runtime/state")
STATE_FILE = RUNTIME_STATE / "learning_governance_state.json"
SHADOW_INTENTS = Path("runtime/logs/learning_shadow_intents.jsonl")

class LearningMode(str, Enum):
    FROZEN = "FROZEN"   # no learning, no adaptive changes; safest default
    SHADOW = "SHADOW"   # learning produces suggestions/intents; DOES NOT place orders
    PROMOTE = "PROMOTE" # canary promote (still bounded) — must rollback if drift/risk triggers

@dataclass
class GovernanceState:
    mode: LearningMode = LearningMode.FROZEN
    # monotonic "generation" for rollback tracking (bump on promote)
    generation: int = 0
    # if drift triggers, we freeze and record last drift reason
    last_drift_code: str = ""
    last_drift_reason: str = ""
    updated_at: str = ""

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def load_state() -> GovernanceState:
    try:
        d = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return GovernanceState(
            mode=LearningMode(d.get("mode","FROZEN")),
            generation=int(d.get("generation",0)),
            last_drift_code=str(d.get("last_drift_code","")),
            last_drift_reason=str(d.get("last_drift_reason","")),
            updated_at=str(d.get("updated_at","")),
        )
    except Exception:
        return GovernanceState(updated_at=_now_iso())

def save_state(st: GovernanceState) -> None:
    RUNTIME_STATE.mkdir(parents=True, exist_ok=True)
    st.updated_at = _now_iso()
    STATE_FILE.write_text(json.dumps({
        "mode": st.mode.value,
        "generation": st.generation,
        "last_drift_code": st.last_drift_code,
        "last_drift_reason": st.last_drift_reason,
        "updated_at": st.updated_at,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def env_mode(default: LearningMode = LearningMode.FROZEN) -> LearningMode:
    v = (os.environ.get("TMF_LEARNING_MODE","") or "").strip().upper()
    if v in ("FROZEN","SHADOW","PROMOTE"):
        return LearningMode(v)
    return default

def canary_limits_from_env() -> Dict[str, Any]:
    # Promote mode must still be bounded
    return {
        "max_qty": float((os.environ.get("TMF_CANARY_MAX_QTY","2.0") or "2.0").strip()),
        "allow_strats": [x.strip() for x in (os.environ.get("TMF_CANARY_ALLOW_STRATS","") or "").split(",") if x.strip()],
        "allow_sides": [x.strip().upper() for x in (os.environ.get("TMF_CANARY_ALLOW_SIDES","BUY,SELL") or "BUY,SELL").split(",") if x.strip()],
    }

def shadow_log_intent(*, intent: Dict[str, Any]) -> None:
    SHADOW_INTENTS.parent.mkdir(parents=True, exist_ok=True)
    rec = dict(intent)
    rec.setdefault("ts", _now_iso())
    with SHADOW_INTENTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def enforce_promote_canary(*, strat_name: str, qty: float, side: str) -> Optional[str]:
    lim = canary_limits_from_env()
    if qty > float(lim["max_qty"]):
        return f"CANARY_QTY_EXCEED qty={qty} > max_qty={lim['max_qty']}"
    allow_strats = lim["allow_strats"]
    if allow_strats and (strat_name not in allow_strats):
        return f"CANARY_STRAT_NOT_ALLOWED strat={strat_name} allow={allow_strats}"
    allow_sides = lim["allow_sides"]
    if allow_sides and (side.upper() not in allow_sides):
        return f"CANARY_SIDE_NOT_ALLOWED side={side} allow={allow_sides}"
    return None

def freeze_on_drift(*, code: str, reason: str) -> GovernanceState:
    st = load_state()
    st.mode = LearningMode.FROZEN
    st.last_drift_code = code
    st.last_drift_reason = reason
    save_state(st)
    return st

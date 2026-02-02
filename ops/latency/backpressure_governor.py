from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class BackpressureConfigV1:
    """
    Conservative backpressure thresholds.
    """
    cooldown_seconds: int = 30
    kill_on_extreme: int = 1

    # extreme thresholds
    extreme_feed_age_ms: int = 5000
    extreme_broker_rtt_ms: int = 4000
    extreme_oms_queue_depth: int = 200

@dataclass
class BackpressureDecision:
    ok: bool
    action: str   # ALLOW | COOLDOWN | KILL
    code: str
    reason: str
    details: Dict[str, Any]

def decide(metrics: Dict[str, Any], cfg: BackpressureConfigV1) -> BackpressureDecision:
    """
    Minimal OS v1 governor:
      - if any metric crosses extreme threshold -> KILL (if enabled)
      - else if any metric nonzero & high-ish (caller can decide) -> COOLDOWN
      - else -> ALLOW
    """
    feed_age = int(metrics.get("feed_age_ms", 0))
    rtt = int(metrics.get("broker_rtt_ms", 0))
    qd = int(metrics.get("oms_queue_depth", 0))

    extreme = (
        feed_age >= cfg.extreme_feed_age_ms
        or rtt >= cfg.extreme_broker_rtt_ms
        or qd >= cfg.extreme_oms_queue_depth
    )
    if extreme and cfg.kill_on_extreme:
        return BackpressureDecision(
            ok=False,
            action="KILL",
            code="BP_EXTREME",
            reason="extreme latency/backpressure detected",
            details={"feed_age_ms": feed_age, "broker_rtt_ms": rtt, "oms_queue_depth": qd},
        )

    # mild: any one is non-trivial (OS: simple rule; will refine later)
    mild = (feed_age > 0) or (rtt > 0) or (qd > 0)
    if mild:
        return BackpressureDecision(
            ok=False,
            action="COOLDOWN",
            code="BP_COOLDOWN",
            reason="backpressure cooldown",
            details={"cooldown_seconds": int(cfg.cooldown_seconds), "feed_age_ms": feed_age, "broker_rtt_ms": rtt, "oms_queue_depth": qd},
        )

    return BackpressureDecision(ok=True, action="ALLOW", code="OK", reason="no backpressure", details={"feed_age_ms": feed_age, "broker_rtt_ms": rtt, "oms_queue_depth": qd})

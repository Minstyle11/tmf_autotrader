from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class BackpressureConfigV1:
    """
    Backpressure governor (M3 OS#1 minimal skeleton):
    - cooldown_seconds: when mild degradation detected, enter cooldown
    - kill_on_extreme: if extreme, request KILL (later wired to kill-switch / auto-remediation)
    """
    cooldown_seconds: int = 30
    kill_on_extreme: int = 1
    # thresholds (aligned with LatencyBudgetV1 defaults)
    max_feed_age_ms: int = 1500
    max_broker_rtt_ms: int = 1200
    max_oms_queue_depth: int = 50
@dataclass(frozen=True)
class BackpressureDecisionV1:
    ok: bool
    action: str   # "ALLOW" | "COOLDOWN" | "KILL"
    code: str     # "OK" | "BP_COOLDOWN" | "BP_EXTREME"
    reason: str
    details: Dict[str, Any]


def decide(metrics: Dict[str, Any], cfg: BackpressureConfigV1) -> BackpressureDecisionV1:
    """
    NOTE: This is an intentionally conservative MVP:
    - Any nonzero degradation -> COOLDOWN
    - Extreme staleness -> KILL (if enabled)

    Later we will replace this with:
    - EWMA / quantile thresholds
    - hysteresis + min-hold time
    - integration with recorder + PaperOMS wrapper
    """
    feed_age_ms = int(metrics.get("feed_age_ms", 0) or 0)
    broker_rtt_ms = int(metrics.get("broker_rtt_ms", 0) or 0)
    oms_q = int(metrics.get("oms_queue_depth", 0) or 0)

    details = {"feed_age_ms": feed_age_ms, "broker_rtt_ms": broker_rtt_ms, "oms_queue_depth": oms_q, "cfg": cfg.__dict__}

    # extreme condition (MVP): very stale feed implies system is blind
    if cfg.kill_on_extreme and feed_age_ms >= 5000:
        return BackpressureDecisionV1(
            ok=False, action="KILL", code="BP_EXTREME",
            reason="extreme feed staleness -> kill requested", details=details
        )

    # mild degradation condition (MVP): exceeds thresholds -> cooldown
    if cfg.cooldown_seconds > 0 and (
        feed_age_ms >= int(getattr(cfg, 'max_feed_age_ms', 1500))
        or broker_rtt_ms >= int(getattr(cfg, 'max_broker_rtt_ms', 1200))
        or oms_q >= int(getattr(cfg, 'max_oms_queue_depth', 50))
    ):
        return BackpressureDecisionV1(
            ok=False, action="COOLDOWN", code="BP_COOLDOWN",
            reason="mild degradation -> cooldown", details=details
        )

    return BackpressureDecisionV1(
        ok=True, action="ALLOW", code="OK",
        reason="no backpressure detected", details=details
    )

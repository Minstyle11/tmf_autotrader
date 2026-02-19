from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class LatencyBudgetV1:
    """
    Latency budget gate (M3 OS#1):
    - feed_age_ms: staleness of market data feed (derived from latest bidask/tick event ts vs now)
    - broker_rtt_ms: round trip time for broker order submit/ack (if available)
    - oms_queue_depth: internal pending queue depth (if applicable)

    check() returns a small verdict dict:
      {"ok": bool, "code": str, "reason": str, "details": {...}}
    """
    max_feed_age_ms: int = 1500
    max_broker_rtt_ms: int = 1200
    max_oms_queue_depth: int = 50

    def check(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        feed_age_ms = int(metrics.get("feed_age_ms", 0) or 0)
        broker_rtt_ms = int(metrics.get("broker_rtt_ms", 0) or 0)
        oms_q = int(metrics.get("oms_queue_depth", 0) or 0)

        details = {
            "feed_age_ms": feed_age_ms,
            "broker_rtt_ms": broker_rtt_ms,
            "oms_queue_depth": oms_q,
            "budget": {
                "max_feed_age_ms": self.max_feed_age_ms,
                "max_broker_rtt_ms": self.max_broker_rtt_ms,
                "max_oms_queue_depth": self.max_oms_queue_depth,
            },
        }

        if feed_age_ms > self.max_feed_age_ms:
            return {"ok": False, "code": "LAT_FEED_TOO_OLD", "reason": "market data feed is too old", "details": details}
        if broker_rtt_ms > self.max_broker_rtt_ms:
            return {"ok": False, "code": "LAT_BROKER_RTT_TOO_HIGH", "reason": "broker RTT too high", "details": details}
        if oms_q > self.max_oms_queue_depth:
            return {"ok": False, "code": "LAT_OMS_QUEUE_TOO_DEEP", "reason": "OMS queue depth too deep", "details": details}

        return {"ok": True, "code": "OK", "reason": "within latency budget", "details": details}

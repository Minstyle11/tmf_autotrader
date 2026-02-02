from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class LatencyBudgetV1:
    """
    Conservative latency budget model (OS v1).
    All units are milliseconds unless specified.
    """
    max_feed_age_ms: int = 1500          # feed quote age
    max_broker_rtt_ms: int = 1200        # broker round-trip / ack
    max_oms_queue_depth: int = 50        # pending orders in-flight

    def check(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return verdict dict:
          {ok: bool, code: str, reason: str, details: {...}}
        """
        feed_age = int(metrics.get("feed_age_ms", 0))
        rtt = int(metrics.get("broker_rtt_ms", 0))
        qd = int(metrics.get("oms_queue_depth", 0))

        if feed_age > self.max_feed_age_ms:
            return {"ok": False, "code": "LAT_FEED_TOO_OLD", "reason": "feed age exceeds budget", "details": {"feed_age_ms": feed_age, "max_feed_age_ms": self.max_feed_age_ms}}
        if rtt > self.max_broker_rtt_ms:
            return {"ok": False, "code": "LAT_BROKER_RTT_TOO_HIGH", "reason": "broker rtt exceeds budget", "details": {"broker_rtt_ms": rtt, "max_broker_rtt_ms": self.max_broker_rtt_ms}}
        if qd > self.max_oms_queue_depth:
            return {"ok": False, "code": "LAT_OMS_QUEUE_TOO_DEEP", "reason": "oms queue depth exceeds budget", "details": {"oms_queue_depth": qd, "max_oms_queue_depth": self.max_oms_queue_depth}}

        return {"ok": True, "code": "OK", "reason": "within latency budgets", "details": {"feed_age_ms": feed_age, "broker_rtt_ms": rtt, "oms_queue_depth": qd}}

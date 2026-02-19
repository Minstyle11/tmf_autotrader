from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# NOTE: Python 3.9.6 compatible
# v18 intent:
#  - Normalize reject reasons across risk/safety/execution layers
#  - Provide stable taxonomy + policy mapping (REJECT/RETRY/COOLDOWN/KILL)
#  - Must be deterministic + auditable (inputs -> decision)

@dataclass(frozen=True)
class RejectDecision:
    ok: bool
    code: str
    domain: str
    severity: str
    action: str
    reason: str
    details: Dict[str, Any]

def _domain_from_code(code: str) -> str:
    c = (code or "").upper()
    if c.startswith("RISK_"):
        return "RISK"
    if c.startswith("SAFETY_"):
        return "SAFETY"
    if c.startswith("EXEC_"):
        return "EXEC"
    if c.startswith("BROKER_"):
        return "BROKER"
    return "UNKNOWN"

def _severity_default(domain: str, code: str) -> str:
    # Conservative defaults; can be overridden via policy file
    if domain in ("SAFETY",):
        return "HIGH"
    if domain in ("RISK",):
        return "MED"
    if domain in ("BROKER",):
        return "MED"
    if domain in ("EXEC",):
        return "MED"
    return "LOW"

def load_policy(path: str) -> Dict[str, Any]:
    """
    v18 requires YAML; to keep repo dependency-free we store JSON-compatible YAML.
    (YAML is a superset of JSON; the file may be .yaml but content is valid JSON.)
    """
    p = Path(path)
    obj = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("reject_policy root must be object")
    return obj

def decide_action(code: str, *, policy: Dict[str, Any]) -> Tuple[str, str]:
    """
    Returns (action, severity)
    action ∈ {REJECT, RETRY, COOLDOWN, KILL}
    """
    c = (code or "").upper()
    domain = _domain_from_code(c)

    by_code = (policy.get("by_code") or {})
    if isinstance(by_code, dict) and c in by_code:
        row = by_code[c] or {}
        return (str(row.get("action", "REJECT")).upper(), str(row.get("severity", _severity_default(domain, c))).upper())

    # prefix rules (e.g. SAFETY_* -> COOLDOWN)
    by_prefix = (policy.get("by_prefix") or {})
    if isinstance(by_prefix, dict):
        for pref, row in by_prefix.items():
            if c.startswith(str(pref).upper()):
                row = row or {}
                return (str(row.get("action", "REJECT")).upper(), str(row.get("severity", _severity_default(domain, c))).upper())

    # domain fallback
    by_domain = (policy.get("by_domain") or {})
    if isinstance(by_domain, dict) and domain in by_domain:
        row = by_domain[domain] or {}
        return (str(row.get("action", "REJECT")).upper(), str(row.get("severity", _severity_default(domain, c))).upper())

    return ("REJECT", _severity_default(domain, c))

def _unwrap_verdict_v1(verdict):
    v = verdict
    # unwrap common wrapper shapes deterministically
    if isinstance(v, dict):
        if isinstance(v.get("risk"), dict):
            v = v.get("risk")
        if isinstance(v, dict) and isinstance(v.get("safety"), dict):
            v = v.get("safety")
    return v


def decision_from_verdict(
    verdict: Any,
    *,
    policy: Dict[str, Any],
    reason_fallback: str = "",
    details_fallback: Optional[Dict[str, Any]] = None,
) -> RejectDecision:
    """
    Accepts:
      - {"ok":bool, "code":str, "reason":str, "details":dict}   (RiskVerdict-like)
      - {"risk": {"code":..., ...}} / {"safety": {"code":..., ...}} wrappers
      - plain dict with "status":"REJECTED" + nested reason
    """
    details_fallback = details_fallback or {}

    # unwrap common shapes
    v = _unwrap_verdict_v1(verdict)

    ok = True
    code = "OK"
    reason = "OK"
    details: Dict[str, Any] = {}

    if isinstance(v, dict):
        if "ok" in v:
            ok = bool(v.get("ok"))
        if "code" in v:
            code = str(v.get("code") or ("OK" if ok else "UNKNOWN"))
        if "reason" in v:
            reason = str(v.get("reason") or reason_fallback or "")
        if "details" in v and isinstance(v.get("details"), dict):
            details = dict(v.get("details") or {})
        elif "detail" in v and isinstance(v.get("detail"), dict):
            details = dict(v.get("detail") or {})
    else:
        ok = bool(v is True)
        code = "OK" if ok else "UNKNOWN"
        reason = reason_fallback or ""

    if ok:
        return RejectDecision(True, "OK", "OK", "LOW", "ALLOW", "pass", {"verdict": verdict})

    domain = _domain_from_code(code)
    action, severity = decide_action(code, policy=policy)

    return RejectDecision(False, code, domain, severity, action, reason, {"details": details, "verdict": verdict})

"""
TMF AutoTrader — Statistical Gate v1 (DSR / PBO / RealityCheck)  [OFFICIAL-LOCKED compatible]
Minimal dependency-free implementation.
"""
from dataclasses import dataclass
from statistics import NormalDist
from typing import Any, Dict, Mapping, Optional, Sequence, List
import math, random

ND = NormalDist()

@dataclass(frozen=True)
class StatGateResult:
    ok: bool
    code: str
    reason: str
    details: Dict[str, Any]

def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / max(1, len(xs))

def _stdev(xs: Sequence[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    m = _mean(xs)
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return math.sqrt(v)

def sharpe_ratio(returns: Sequence[float], *, eps: float = 1e-12) -> float:
    sd = _stdev(returns)
    if sd <= eps:
        return 0.0
    return _mean(returns) / sd

def _expected_max_gaussian(n_trials: int) -> float:
    n = max(1, int(n_trials))
    gamma = 0.5772156649015329
    a = min(max(1.0 - 1.0 / n, 1e-12), 1 - 1e-12)
    b = min(max(1.0 - 1.0 / (n * math.e), 1e-12), 1 - 1e-12)
    return (1.0 - gamma) * ND.inv_cdf(a) + gamma * ND.inv_cdf(b)

def deflated_sharpe_ratio(
    returns: Sequence[float],
    *,
    n_trials: int = 1,
    sr_threshold: float = 0.0,
    ann_factor: Optional[float] = None,
) -> float:
    r = list(returns)
    T = len(r)
    if T < 3:
        return 0.0
    sr = sharpe_ratio(r)
    if ann_factor is not None and ann_factor > 0:
        sr *= math.sqrt(float(ann_factor))
    sr0 = _expected_max_gaussian(max(1, int(n_trials)))
    baseline = max(float(sr_threshold), 0.0)
    se = math.sqrt((1.0 + (sr ** 2) / 2.0) / max(1.0, float(T - 1)))
    if se <= 1e-12:
        return 0.0
    z = (sr - max(baseline, sr0)) / se
    return ND.cdf(z)

def reality_check_pvalue(
    strat_returns: Mapping[str, Sequence[float]],
    *,
    block: int = 10,
    n_boot: int = 1000,
    seed: int = 7,
) -> float:
    names = list(strat_returns.keys())
    if not names:
        return 1.0
    m = min(len(strat_returns[n]) for n in names)
    if m < 5:
        return 1.0
    X = {n: list(strat_returns[n])[:m] for n in names}
    obs = max(_mean(X[n]) for n in names)

    rng = random.Random(seed)
    block = max(1, int(block))
    n_boot = max(200, int(n_boot))

    def sample_indices() -> List[int]:
        idx: List[int] = []
        while len(idx) < m:
            start = rng.randrange(0, m)
            for j in range(block):
                if len(idx) >= m:
                    break
                idx.append((start + j) % m)
        return idx

    ge = 0
    for _ in range(n_boot):
        idx = sample_indices()
        boot = max(_mean([X[n][i] for i in idx]) for n in names)
        if boot >= obs:
            ge += 1
    return (ge + 1) / (n_boot + 1)

def pbo_cscv(
    strat_returns: Mapping[str, Sequence[float]],
    *,
    n_slices: int = 8,
) -> float:
    names = list(strat_returns.keys())
    if len(names) < 2:
        return 1.0
    S = int(n_slices)
    if S < 4 or S % 2 != 0:
        raise ValueError("n_slices must be even and >=4")
    m = min(len(strat_returns[n]) for n in names)
    if m < S * 5:
        return 1.0

    slice_len = m // S
    slices = [(i * slice_len, (i + 1) * slice_len) for i in range(S)]

    def seg(rs: Sequence[float], sidx: int) -> Sequence[float]:
        a, b = slices[sidx]
        return rs[a:b]

    import itertools
    half = S // 2
    all_idx = list(range(S))
    combs = list(itertools.combinations(all_idx, half))

    overfit = 0
    total = 0
    for IS in combs:
        IS_set = set(IS)
        OOS = [i for i in all_idx if i not in IS_set]

        is_sr = {}
        oos_sr = {}
        for n in names:
            r = list(strat_returns[n])[: slice_len * S]
            is_r = []
            oos_r = []
            for i in IS:
                is_r.extend(seg(r, i))
            for i in OOS:
                oos_r.extend(seg(r, i))
            is_sr[n] = sharpe_ratio(is_r)
            oos_sr[n] = sharpe_ratio(oos_r)

        best = max(names, key=lambda k: is_sr[k])
        oos_sorted = sorted(oos_sr.values())
        median = oos_sorted[len(oos_sorted)//2]
        total += 1
        if oos_sr[best] < median:
            overfit += 1

    return overfit / max(1, total)

def run_stat_gate_v1(
    strat_returns: Mapping[str, Sequence[float]],
    *,
    pbo_max: float = 0.10,
    dsr_min: float = 0.95,
    n_trials: int = 1,
    ann_factor: Optional[float] = None,
) -> StatGateResult:
    names = list(strat_returns.keys())
    if not names:
        return StatGateResult(False, "STAT_EMPTY", "no strategies provided", {})
    best = max(names, key=lambda k: sharpe_ratio(strat_returns[k]))
    dsr = deflated_sharpe_ratio(strat_returns[best], n_trials=n_trials, ann_factor=ann_factor)
    pbo = pbo_cscv(strat_returns)
    rc_p = reality_check_pvalue(strat_returns)
    ok = (pbo <= pbo_max) and (dsr >= dsr_min) and (rc_p <= 0.05)
    code = "STAT_GATE_PASS" if ok else "STAT_GATE_FAIL"
    reason = f"best={best} dsr={dsr:.4f} pbo={pbo:.4f} rc_p={rc_p:.4f}"
    return StatGateResult(ok, code, reason, {"best": best, "dsr": dsr, "pbo": pbo, "rc_p": rc_p})

if __name__ == "__main__":
    rng = random.Random(42)
    T = 2000
    s1 = [rng.gauss(0.0002, 0.01) for _ in range(T)]
    s2 = [rng.gauss(0.0, 0.01) for _ in range(T)]
    s3 = [rng.gauss(0.0, 0.01) for _ in range(T)]
    out = run_stat_gate_v1({"s1": s1, "s2": s2, "s3": s3}, n_trials=20, ann_factor=252)
    print("[SMOKE]", out)

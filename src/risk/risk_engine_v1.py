from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any, Tuple



def _base_symbol(sym: str) -> str:
    s = str(sym or "")
    for b in ("TMF","TXF","MXF"):
        if s.startswith(b):
            return b
    return s

@dataclass(frozen=True)
class RiskConfigV1:
    # --- core gates ---
    strict_require_stop: int = 1  # 1 = require stop_price in order meta (recommended)
    per_trade_max_loss_ntd: float = 1500.0
    daily_max_loss_ntd: float = 5000.0
    consecutive_losses_limit: int = 3
    cooldown_minutes_after_consecutive_losses: int = 30

    # --- market-quality gates (optional; set strict=1 to require metrics) ---
    strict_require_market_metrics: int = 0
    max_spread_points: float = 3.0
    max_volatility_atr_points: float = 120.0
    min_liquidity_score: float = 0.0

    # --- symbol / sizing gates ---
    max_qty_per_order: float = 2.0
    allow_symbols: Tuple[str, ...] = ("TMF", "TXF", "MXF")

    # point value (NTD per 1 point per contract)
    # TMF micro taiex ~= 10 NTD/point/contract; TXF usually 200; MXF usually 50.
    # Keep configurable; defaults chosen for TW index futures conventions.
    point_value_by_symbol: Dict[str, float] = None

    def __post_init__(self):
        if self.point_value_by_symbol is None:
            object.__setattr__(self, "point_value_by_symbol", {"TMF": 10.0, "TXF": 200.0, "MXF": 50.0})


@dataclass(frozen=True)
class RiskVerdict:
    ok: bool
    code: str
    reason: str
    details: Dict[str, Any]


class RiskEngineV1:
    def __init__(self, *, db_path: str, cfg: Optional[RiskConfigV1] = None):
        self.db_path = db_path
        self.cfg = cfg or RiskConfigV1()

    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _today_prefix(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _get_today_realized_pnl(self, con: sqlite3.Connection) -> float:
        # trades.pnl is assumed NTD (based on OMS demo)
        day = self._today_prefix()
        row = con.execute(
            "SELECT COALESCE(SUM(pnl),0) AS s FROM trades WHERE close_ts IS NOT NULL AND close_ts LIKE ?",
            (day + "%",),
        ).fetchone()
        return float(row["s"] if row else 0.0)

    def _get_consecutive_losses(self, con: sqlite3.Connection, limit_scan: int = 50) -> int:
        rows = con.execute(
            "SELECT pnl FROM trades WHERE close_ts IS NOT NULL ORDER BY id DESC LIMIT ?",
            (limit_scan,),
        ).fetchall()
        n = 0
        for r in rows:
            pnl = r["pnl"]
            if pnl is None:
                break
            if float(pnl) < 0:
                n += 1
            else:
                break
        return n

    def _get_last_loss_ts(self, con: sqlite3.Connection) -> Optional[str]:
        row = con.execute(
            "SELECT close_ts FROM trades WHERE close_ts IS NOT NULL AND pnl < 0 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return str(row["close_ts"]) if row else None

    def _minutes_since(self, ts_iso: str) -> Optional[float]:
        try:
            dt = datetime.fromisoformat(ts_iso)
            return (datetime.now() - dt).total_seconds() / 60.0
        except Exception:
            return None

    def check_pre_trade(
        self,
        *,
        symbol: str,
        side: str,
        qty: float,
        entry_price: float,
        meta: Optional[Dict[str, Any]] = None,
    ) -> RiskVerdict:
        meta = meta or {}
        cfg = self.cfg

        # --- allowlist ---
        # --- allowlist ---
        # allow_symbols are treated as PREFIXES for rolling/continuous futures symbols (e.g., TMFB6, TMFR1)
        if not any(str(symbol).startswith(pref) for pref in cfg.allow_symbols):
            return RiskVerdict(False, "RISK_SYMBOL_NOT_ALLOWED", f"symbol not allowed: {symbol}", {"symbol": symbol, "allow_prefixes": list(cfg.allow_symbols)})

        # --- qty ---
        if qty <= 0 or qty > cfg.max_qty_per_order:
            return RiskVerdict(
                False,
                "RISK_QTY_LIMIT",
                f"qty invalid/too large: {qty} > {cfg.max_qty_per_order}",
                {"qty": qty, "max_qty_per_order": cfg.max_qty_per_order},
            )

        side_u = str(side).upper()
        if side_u not in ("BUY", "SELL"):
            return RiskVerdict(False, "RISK_SIDE_INVALID", f"invalid side: {side}", {"side": side})

        # --- derive entry_price for MARKET / reduce-only closes ---
        # For MARKET orders, price may be None/0. Use meta.ref_price first; else use market_metrics bid/ask conservatively.
        if entry_price <= 0:
            try:
                rp = (meta.get('ref_price') if isinstance(meta, dict) else None)
                if rp is not None and float(rp) > 0:
                    entry_price = float(rp)
                else:
                    mm0 = (meta.get('market_metrics') if isinstance(meta, dict) else None) or {}
                    bid = mm0.get('bid')
                    ask = mm0.get('ask')
                    if bid is not None and ask is not None:
                        # conservative: BUY uses ask, SELL uses bid
                        entry_price = float(ask) if side_u == 'BUY' else float(bid)
            except Exception:
                pass

        if entry_price <= 0:
            return RiskVerdict(False, "RISK_PRICE_INVALID", f"invalid entry_price: {entry_price}", {"entry_price": entry_price})

        # --- require stop_price for meaningful per-trade risk bounding ---
        stop_price = meta.get("stop_price")
        # IMPORTANT: never block position-reducing / closing orders.
        # Use meta hints to mark close-only intent (reduce_only / intent=CLOSE/EXIT).
        reduce_only = bool(meta.get("reduce_only") or meta.get("close_only") or (str(meta.get("intent","")) in ("CLOSE","EXIT")))
        if cfg.strict_require_stop == 1 and (stop_price is None) and (not reduce_only):
            return RiskVerdict(
                False,
                "RISK_STOP_REQUIRED",
                "strict_require_stop=1 but meta.stop_price missing",
                {"strict_require_stop": cfg.strict_require_stop},
            )
# --- compute per-trade worst loss (NTD) if stop exists ---
        per_trade_risk_ntd = None
        pv = float(cfg.point_value_by_symbol.get(_base_symbol(symbol), 0.0))
        if stop_price is not None:
            try:
                stop_price = float(stop_price)
                if stop_price <= 0:
                    raise ValueError("stop_price <= 0")
                # LONG (BUY): loss if price goes down to stop
                # SHORT (SELL): loss if price goes up to stop
                if side_u == "BUY":
                    loss_points = max(0.0, entry_price - stop_price)
                else:
                    loss_points = max(0.0, stop_price - entry_price)
                per_trade_risk_ntd = loss_points * float(qty) * pv
            except Exception as e:
                return RiskVerdict(False, "RISK_STOP_INVALID", f"invalid stop_price: {meta.get('stop_price')}", {"err": str(e)})

            if per_trade_risk_ntd is not None and per_trade_risk_ntd > cfg.per_trade_max_loss_ntd:
                return RiskVerdict(
                    False,
                    "RISK_PER_TRADE_MAX_LOSS",
                    f"per-trade risk too high: {per_trade_risk_ntd:.2f} > {cfg.per_trade_max_loss_ntd:.2f}",
                    {"per_trade_risk_ntd": per_trade_risk_ntd, "per_trade_max_loss_ntd": cfg.per_trade_max_loss_ntd},
                )

        
        # --- market-quality gates (optional; driven by meta) ---
        # Allow either meta.market_metrics dict or top-level meta keys.
        mm = meta.get("market_metrics") or {}
        if cfg.strict_require_market_metrics == 1 and not mm:
            return RiskVerdict(
                False,
                "RISK_MARKET_METRICS_REQUIRED",
                "strict_require_market_metrics=1 but meta.market_metrics missing/empty",
                {"strict_require_market_metrics": cfg.strict_require_market_metrics},
            )

        spread = mm.get("spread_points", meta.get("spread_points"))
        atr = mm.get("atr_points", meta.get("atr_points"))
        liq = mm.get("liquidity_score", meta.get("liquidity_score"))

        try:
            if spread is not None and float(spread) > float(cfg.max_spread_points):
                return RiskVerdict(
                    False,
                    "RISK_SPREAD_TOO_WIDE",
                    f"spread too wide: {float(spread):.4g} > {float(cfg.max_spread_points):.4g} (points)",
                    {"spread_points": float(spread), "max_spread_points": float(cfg.max_spread_points)},
                )
        except Exception as e:
            return RiskVerdict(False, "RISK_SPREAD_INVALID", "invalid spread_points", {"err": str(e), "spread_points": spread})

        try:
            if atr is not None and float(atr) > float(cfg.max_volatility_atr_points):
                return RiskVerdict(
                    False,
                    "RISK_VOL_TOO_HIGH",
                    f"volatility too high (ATR): {float(atr):.4g} > {float(cfg.max_volatility_atr_points):.4g} (points)",
                    {"atr_points": float(atr), "max_volatility_atr_points": float(cfg.max_volatility_atr_points)},
                )
        except Exception as e:
            return RiskVerdict(False, "RISK_ATR_INVALID", "invalid atr_points", {"err": str(e), "atr_points": atr})

        try:
            if liq is not None and float(liq) < float(cfg.min_liquidity_score):
                return RiskVerdict(
                    False,
                    "RISK_LIQUIDITY_LOW",
                    f"liquidity too low: {float(liq):.4g} < {float(cfg.min_liquidity_score):.4g}",
                    {"liquidity_score": float(liq), "min_liquidity_score": float(cfg.min_liquidity_score)},
                )
        except Exception as e:
            return RiskVerdict(False, "RISK_LIQUIDITY_INVALID", "invalid liquidity_score", {"err": str(e), "liquidity_score": liq})


        # --- DB-based gates: daily loss + consecutive losses + cooldown ---
        con = self._con()
        try:
            today_pnl = self._get_today_realized_pnl(con)
            if today_pnl <= -abs(cfg.daily_max_loss_ntd):
                return RiskVerdict(
                    False,
                    "RISK_DAILY_MAX_LOSS",
                    f"daily max loss hit: {today_pnl:.2f} <= -{abs(cfg.daily_max_loss_ntd):.2f}",
                    {"today_realized_pnl_ntd": today_pnl, "daily_max_loss_ntd": cfg.daily_max_loss_ntd},
                )

            consec = self._get_consecutive_losses(con)
            if consec >= cfg.consecutive_losses_limit:
                last_loss_ts = self._get_last_loss_ts(con)
                mins = self._minutes_since(last_loss_ts) if last_loss_ts else None
                if mins is None or mins < cfg.cooldown_minutes_after_consecutive_losses:
                    return RiskVerdict(
                        False,
                        "RISK_CONSEC_LOSS_COOLDOWN",
                        f"consecutive losses={consec} (limit={cfg.consecutive_losses_limit}), cooldown active",
                        {
                            "consecutive_losses": consec,
                            "limit": cfg.consecutive_losses_limit,
                            "cooldown_minutes": cfg.cooldown_minutes_after_consecutive_losses,
                            "minutes_since_last_loss": mins,
                            "last_loss_ts": last_loss_ts,
                        },
                    )
        finally:
            con.close()

        # PASS
        return RiskVerdict(
            True,
            "OK",
            "pre-trade gates pass",
            {
                "symbol": symbol,
                "side": side_u,
                "qty": qty,
                "entry_price": entry_price,
                "per_trade_risk_ntd": per_trade_risk_ntd,
                "cfg": asdict(cfg),
            },
        )

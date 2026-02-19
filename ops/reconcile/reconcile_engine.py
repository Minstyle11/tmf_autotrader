from __future__ import annotations

import sqlite3
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple


# NOTE: Python 3.9.6 compatible


@dataclass(frozen=True)
class ReconcileResult:
    ok: bool
    code: str
    reason: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _table_cols(con: sqlite3.Connection, table: str) -> List[str]:
    rows = con.execute(f"PRAGMA table_info({table})").fetchall()
    return [str(r[1]) for r in rows]


def _has_table(con: sqlite3.Connection, table: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,)
    ).fetchone()
    return bool(row)


def reconcile_db(db_path: str) -> ReconcileResult:
    """
    Conservative reconcile for PaperOMS-style sqlite (v18-aligned):
      - tables existence
      - orphan fills: prefer fills.broker_order_id -> orders.broker_order_id (PaperOMS key)
        fallback to fills.order_id -> orders.id if such columns exist
      - orphan trades: if trades has broker_order_id/order_id, apply same key logic
      - invariant: FILLED orders should have >=1 fill (using same key logic)
      - basic counts summary + columns
    Returns ReconcileResult with machine-readable codes.
    """
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        need = ["orders", "fills", "trades"]
        missing_tables = [t for t in need if not _has_table(con, t)]
        if missing_tables:
            return ReconcileResult(
                False,
                "RECON_MISSING_TABLES",
                "missing required tables",
                {"missing_tables": missing_tables},
            )

        orders_cols = _table_cols(con, "orders")
        fills_cols = _table_cols(con, "fills")
        trades_cols = _table_cols(con, "trades")

        details = {
            "db_path": db_path,
            "counts": {},
            "columns": {"orders": orders_cols, "fills": fills_cols, "trades": trades_cols},
            "orphan_fills": None,
            "orphan_trades": None,
            "filled_orders_with_zero_fills": None,
        }

        # counts (best-effort)
        for t in ("orders", "fills", "trades"):
            try:
                r = con.execute(f"SELECT COUNT(1) AS c FROM {t}").fetchone()
                details["counts"][t] = int(r["c"]) if r and "c" in r.keys() else None
            except Exception:
                details["counts"][t] = None

        # pick join key for fills->orders
        ok_key = fk_key = None
        if ("broker_order_id" in orders_cols) and ("broker_order_id" in fills_cols):
            ok_key, fk_key = "broker_order_id", "broker_order_id"
        elif ("id" in orders_cols) and ("order_id" in fills_cols):
            ok_key, fk_key = "id", "order_id"

        # orphan fills
        if ok_key and fk_key:
            row = con.execute(
                f"""
                SELECT COUNT(1) AS c
                FROM fills f
                LEFT JOIN orders o ON f.{fk_key} = o.{ok_key}
                WHERE o.{ok_key} IS NULL
                """
            ).fetchone()
            orphan_fills = int(row["c"]) if row else 0
            details["orphan_fills"] = orphan_fills
            if orphan_fills > 0:
                return ReconcileResult(
                    False,
                    "RECON_ORPHAN_FILLS",
                    "fills reference missing orders",
                    details,
                )
        else:
            details["orphan_fills"] = None

        # orphan trades (only if joinable)
        tok = tfk = None
        if ("broker_order_id" in orders_cols) and ("broker_order_id" in trades_cols):
            tok, tfk = "broker_order_id", "broker_order_id"
        elif ("id" in orders_cols) and ("order_id" in trades_cols):
            tok, tfk = "id", "order_id"

        if tok and tfk:
            row = con.execute(
                f"""
                SELECT COUNT(1) AS c
                FROM trades t
                LEFT JOIN orders o ON t.{tfk} = o.{tok}
                WHERE o.{tok} IS NULL
                """
            ).fetchone()
            orphan_trades = int(row["c"]) if row else 0
            details["orphan_trades"] = orphan_trades
            if orphan_trades > 0:
                return ReconcileResult(
                    False,
                    "RECON_ORPHAN_TRADES",
                    "trades reference missing orders",
                    details,
                )
        else:
            details["orphan_trades"] = None

        # invariant: FILLED orders should have >=1 fill (same key logic)
        if ("status" in orders_cols) and ok_key and fk_key:
            row = con.execute(
                f"""
                SELECT COUNT(1) AS c FROM (
                    SELECT o.{ok_key} AS k
                    FROM orders o
                    LEFT JOIN fills f ON f.{fk_key} = o.{ok_key}
                    WHERE o.status='FILLED'
                    GROUP BY o.{ok_key}
                    HAVING COUNT(f.id)=0
                )
                """
            ).fetchone()
            filled_no_fill = int(row["c"]) if row else 0
            details["filled_orders_with_zero_fills"] = filled_no_fill
            if filled_no_fill > 0:
                return ReconcileResult(
                    False,
                    "RECON_FILLED_WITHOUT_FILLS",
                    "orders marked FILLED but no fills found",
                    details,
                )
        else:
            details["filled_orders_with_zero_fills"] = None

        return ReconcileResult(True, "OK", "reconcile pass", details)
    finally:
        con.close()

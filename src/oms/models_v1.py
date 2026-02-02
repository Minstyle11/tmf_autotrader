from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal
from datetime import datetime

Side = Literal["BUY","SELL"]
OrderType = Literal["MARKET","LIMIT"]
OrderStatus = Literal["NEW","PARTIALLY_FILLED","FILLED","CANCELLED","REJECTED"]

@dataclass
class Order:
    order_id: str
    ts: str
    symbol: str
    side: Side
    qty: float
    order_type: OrderType
    price: Optional[float] = None
    status: OrderStatus = "NEW"
    filled_qty: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Fill:
    fill_id: str
    ts: str
    order_id: str
    symbol: str
    side: Side
    qty: float
    price: float
    fee_ntd: float
    tax_ntd: float
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Trade:
    trade_id: str
    open_ts: str
    close_ts: Optional[str]
    symbol: str
    side: Literal["LONG","SHORT"]
    qty: float
    entry: float
    exit: Optional[float] = None
    pnl_ntd: Optional[float] = None
    pnl_pct: Optional[float] = None
    reason_open: Optional[str] = None
    reason_close: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Position:
    symbol: str
    side: Optional[Literal["LONG","SHORT"]] = None
    qty: float = 0.0
    avg_price: float = 0.0
    open_ts: Optional[str] = None

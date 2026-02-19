#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from src.market.taifex_calendar_v1 import market_closed_now_taipei

v = market_closed_now_taipei(datetime.now())
print(f"code={v.code}")
print(f"closed={int(v.closed)}")
print(f"reason={v.reason}")
print(f"next_open_day={v.next_open_day}")
if v.closed:
    print("=== [MARKET_CLOSED] gate OK ===")
else:
    print("=== [MARKET_OPEN] ===")
print("[程序完成]")

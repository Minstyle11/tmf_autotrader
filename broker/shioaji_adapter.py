from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .shioaji_callbacks import make_order_callback

@dataclass(frozen=True)
class ShioajiAdapterConfig:
    raw_events_dir: str = "runtime/raw_events"
    enable_order_callback: bool = True

class ShioajiAdapter:
    def __init__(self, api: Any, *, config: Optional[ShioajiAdapterConfig] = None):
        self.api = api
        self.config = config or ShioajiAdapterConfig()

    def install_callbacks(self) -> None:
        if not getattr(self.config, "enable_order_callback", True):
            return
        out_dir = Path(self.config.raw_events_dir)
        cb = make_order_callback(out_dir=out_dir)
        self.api.set_order_callback(cb)

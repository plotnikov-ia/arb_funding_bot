import numpy as np
from dataclasses import dataclass

@dataclass(slots=True)
class BBO:
    ts: int
    book_update_id: int
    bid_price_1: float
    bid_qty_1: float
    ask_price_1: float
    ask_qty_1: float
    
    @property
    def mid_price(self) -> float:
        return (self.bid_price_1 + self.ask_price_1) / 2
    
    def __str__(self) -> str:
        spread = self.ask_price_1 - self.bid_price_1
        mid = (self.ask_price_1 + self.bid_price_1) / 2

        def f(x) -> str:
            return "—" if not np.isfinite(x) else f"{x:.10g}"

        return (
            f"BBO(ts={int(self.ts)} "
            f"bid={f(self.bid_price_1)}@{f(self.bid_qty_1)} "
            f"ask={f(self.ask_price_1)}@{f(self.ask_qty_1)} "
            f"spr={f(spread)} mid={f(mid)})"
        )
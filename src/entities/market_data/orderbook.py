import numpy as np
from dataclasses import dataclass

@dataclass(slots=True)
class Orderbook:
    ts: float
    bid_price_list: np.ndarray
    bid_qty_list: np.ndarray
    ask_price_list: np.ndarray
    ask_qty_list: np.ndarray
    
    @property
    def mid_price(self) -> float:
        return (self.bid_price_list[0] + self.ask_price_list[0]) / 2
    
    @property
    def wmid_price(self) -> float:
        imb = (self.bid_price_list[0] / (self.bid_price_list[0] + self.ask_price_list[0]))
        wmid_price = imb * self.ask_price_list[0] + (1 - imb) * self.bid_price_list[0]
        return wmid_price
    
    @property
    def vwap_price(self) -> float:
        vwap = (
            (self.bid_price_list[0] * self.bid_qty_list[0]) +
            (self.bid_price_list[1] * self.bid_qty_list[1]) +
            (self.ask_price_list[0] * self.ask_qty_list[0]) +
            (self.ask_price_list[1] * self.ask_qty_list[1])
        ) / (
            self.bid_qty_list[0] +
            self.bid_qty_list[1] +
            self.ask_qty_list[0] +
            self.ask_qty_list[1]
        )
        return vwap
    
    def __str__(self) -> str:
        bp = np.asarray(self.bid_price_list, dtype=float)
        bq = np.asarray(self.bid_qty_list, dtype=float)
        ap = np.asarray(self.ask_price_list, dtype=float)
        aq = np.asarray(self.ask_qty_list, dtype=float)

        best_bid = bp[0] if bp.size else np.nan
        best_ask = ap[0] if ap.size else np.nan
        bid_q0 = bq[0] if bq.size else np.nan
        ask_q0 = aq[0] if aq.size else np.nan

        spread = best_ask - best_bid
        mid = (best_ask + best_bid) / 2

        def f(x) -> str:
            return "—" if not np.isfinite(x) else f"{x:.10g}"

        return (
            f"Orderbook(ts={int(self.ts)} "
            f"bid={f(best_bid)}@{f(bid_q0)} "
            f"ask={f(best_ask)}@{f(ask_q0)} "
            f"spr={f(spread)} mid={f(mid)})"
        )
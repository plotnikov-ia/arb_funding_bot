from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

@dataclass
class BlockchainState:
    ts: Optional[int] = None
    amount_usdc: Optional[float] = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AccountState:
    exchange: str

    ts: Optional[int] = None

    equity: Optional[float] = None

    quote_position: Optional[float] = None
    base_position: Optional[float] = None

    entry_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None

    leverage: Optional[float] = None
    liquidation_price: Optional[float] = None

    initial_margin_requirement: Optional[float] = None
    maintenance_margin_requirement: Optional[float] = None
    
    margin_usage: Optional[float] = 0
    margin_ratio: Optional[float] = 1e+6

    quote_position_spot: Optional[float] = None
    locked_quote_position_spot: float = 0.0

    def __str__(self) -> str:
        def fmt(x):
            return round(x, 5) if x is not None else None

        return (
            f"=== Account State ===\n"
            f"Exchange:             {self.exchange}\n"
            f"Timestamp:            {self.ts}\n"
            f"\n"
            f"Quote position:               {fmt(self.quote_position)}\n"
            f"Quote position spot:          {fmt(self.quote_position_spot)}\n"
            f"Quote position locked spot:   {fmt(self.locked_quote_position_spot)}\n"
            f"Base position:         {fmt(self.base_position)}\n"
            f"\n"
            f"Entry price:           {fmt(self.entry_price)}\n"
            f"Unrealized PnL:        {fmt(self.unrealized_pnl)}\n"
            f"Equity:                {fmt(self.equity)}\n"
            f"\n"
            f"Leverage:              {self.leverage}\n"
            f"Liquidation price:     {fmt(self.liquidation_price)}\n"
            f"\n"
            f"Initial margin:        {fmt(self.initial_margin_requirement)}\n"
            f"Maintenance margin:    {fmt(self.maintenance_margin_requirement)}\n"
            f"\n"
            f"Margin ration:         {fmt(self.margin_ratio)}\n"
            f"Margin usage:         {fmt(self.margin_usage)}\n"
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
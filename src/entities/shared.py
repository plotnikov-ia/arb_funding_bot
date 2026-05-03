from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class Rebalance:
    to_exchange: str
    amount_usdc: float
    wip: bool
    on_blockchain: bool
    timestamp_create: int
    timestamp_sent_to_blockchain: Optional[int] = None
    timestamp_sent_to_exchange: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LimitOrder:
    client_id: str
    asset: str
    is_long: bool
    price: float
    qty: float
    timestamp_sent_order: int
    timestamp_sent_modify: int
    timestamp_sent_cancel: int
    pending_posting: bool
    pending_modify: bool
    pending_cancellation: bool
    
    
def __repr__(self):
    return (
        f"LimitOrder("
        f"client_id={self.client_id}, "
        f"asset={self.asset}, "
        f"is_long={self.is_long}, "
        f"price={self.price}, "
        f"qty={self.qty}, "
        f"timestamp_sent_order={self.timestamp_sent_order}, "
        f"timestamp_sent_modify={self.timestamp_sent_modify}, "
        f"timestamp_sent_cancel={self.timestamp_sent_cancel}, "
        f"pending_posting={self.pending_posting}, "
        f"pending_modify={self.pending_modify}, "
        f"pending_cancellation={self.pending_cancellation}"
        f")"
    )
    
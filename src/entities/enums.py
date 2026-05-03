from enum import Enum


class RiskMode(Enum):
    NORMAL = "normal"
    REBALANCE = "rebalance"
    MAKER_DELEVERAGE = "maker_deleverage"
    TAKER_DELEVERAGE = "taker_deleverage"
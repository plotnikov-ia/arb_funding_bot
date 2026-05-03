import os
import time
from dotenv import load_dotenv


from src.entities import AccountState, BlockchainState, Rebalance, RiskMode
from src.alerting import send_alert
from src.logging import LOG_ENABLED, log_event

load_dotenv()

LEVERAGE_BINANCE = float(os.getenv("LEVERAGE_BINANCE"))
LEVERAGE_HYPER = float(os.getenv("LEVERAGE_HYPER"))

IMF_BINANCE = float(os.getenv("IMF_BINANCE"))
IMF_HYPER = float(os.getenv("IMF_HYPER"))

MMF_BINANCE = float(os.getenv("MMF_BINANCE"))
MMF_HYPER = float(os.getenv("MMF_HYPER"))

MARGIN_USAGE_ENTRY_TH = float(os.getenv("MARGIN_USAGE_ENTRY_TH"))

MARGIN_RATIO_TARGET = float(os.getenv("MARGIN_RATIO_TARGET"))
MARGIN_RATIO_REBALANCE_TH = float(os.getenv("MARGIN_RATIO_REBALANCE_TH"))
MARGIN_RATIO_MAKER_DELEVERAGE_TH = float(os.getenv("MARGIN_RATIO_MAKER_DELEVERAGE_TH"))
MARGIN_RATIO_TAKER_DELEVERAGE_TH = float(os.getenv("MARGIN_RATIO_TAKER_DELEVERAGE_TH"))


class RiskManager:
    def __init__(self) -> None:
        self.allowed_long_binance = False
        self.allowed_short_binance = False
        
        self.deal_size = 0.1
        
        self.risk_mode = RiskMode.NORMAL
        self.active_rebalance = None
            
    def update(
        self, 
        state_binance: AccountState,
        state_hyper: AccountState,
        state_blockchain: BlockchainState,
        mid_price: float
    ):  
        self.update_risk(state_binance=state_binance, state_hyper=state_hyper, state_blockchain=state_blockchain, mid_price=mid_price)
        
        if self.risk_mode == RiskMode.NORMAL:
            self.compute_position_target(state_binance=state_binance, state_hyper=state_hyper, mid_price=mid_price)
        
    def update_risk(
        self,
        state_binance: AccountState,
        state_hyper: AccountState,
        state_blockchain: BlockchainState,
        mid_price: float
    ):
        state_binance.margin_ratio = self.calc_margin_ratio(
            mid_price=mid_price, base_position=state_binance.base_position, quote_position=state_binance.quote_position, 
            unrealized_pnl=state_binance.unrealized_pnl, MMF_pct=(MMF_BINANCE * 100)
        )
            
        state_hyper.margin_ratio = self.calc_margin_ratio(
            mid_price=mid_price, base_position=state_hyper.base_position, quote_position=state_hyper.quote_position, 
            unrealized_pnl=state_hyper.unrealized_pnl, MMF_pct=(MMF_HYPER * 100)
        )
        
        if state_binance.margin_ratio > MARGIN_RATIO_REBALANCE_TH and state_hyper.margin_ratio > MARGIN_RATIO_REBALANCE_TH:
            self.risk_mode = RiskMode.NORMAL
            return
        
        if state_binance.margin_ratio < MARGIN_RATIO_REBALANCE_TH or state_hyper.margin_ratio < MARGIN_RATIO_REBALANCE_TH:
            self.risk_mode = RiskMode.REBALANCE
            self.prepare_rebalance(state_binance=state_binance, state_hyper=state_hyper, state_blockchain=state_blockchain, mid_price=mid_price)
        
        if state_binance.margin_ratio < MARGIN_RATIO_MAKER_DELEVERAGE_TH:
            send_alert(alert_type="critical", json_data={"binance": f"margin ratio = {state_binance.margin_ratio:.2f}", "action": "MAKER_DELEVERAGE mode is on"})
            self.risk_mode = RiskMode.MAKER_DELEVERAGE
        
        if state_hyper.margin_ratio < MARGIN_RATIO_MAKER_DELEVERAGE_TH:
            send_alert(alert_type="critical", json_data={"hyper": f"margin ratio = {state_hyper.margin_ratio:.2f}", "action": "MAKER_DELEVERAGE mode is on"})
            self.risk_mode = RiskMode.MAKER_DELEVERAGE
        
        if state_binance.margin_ratio < MARGIN_RATIO_TAKER_DELEVERAGE_TH:
            send_alert(alert_type="critical", json_data={"binance": f"margin ratio = {state_binance.margin_ratio:.2f}", "action": "TAKER_DELEVERAGE mode is on"})
            self.risk_mode = RiskMode.TAKER_DELEVERAGE
        
        if state_hyper.margin_ratio < MARGIN_RATIO_TAKER_DELEVERAGE_TH:
            send_alert(alert_type="critical", json_data={"hyper": f"margin ratio = {state_hyper.margin_ratio:.2f}", "action": "TAKER_DELEVERAGE mode is on"})
            self.risk_mode = RiskMode.TAKER_DELEVERAGE
            
    def prepare_rebalance(
        self,
        state_binance: AccountState,
        state_hyper: AccountState,
        state_blockchain: BlockchainState,
        mid_price: float
    ):
        if self.active_rebalance:
            return
        
        if state_binance.margin_ratio < MARGIN_RATIO_REBALANCE_TH:
            send_alert(alert_type="warning", json_data={"binance": f"margin ratio = {state_binance.margin_ratio:.2f}", "action": "REBALANCE mode is on"})
            
            transfer_amount = self.calculateTopUpForMarginRatio(
                mid_price=mid_price, base_position=state_binance.base_position, quote_position=state_binance.quote_position, unrealized_pnl=state_binance.unrealized_pnl, MMF_pct=(MMF_BINANCE * 100),
            )
            transfer_amount = int(transfer_amount)
            hypo_margin_ratio_hyper = self.calc_margin_ratio(
                mid_price=mid_price, base_position=state_hyper.base_position,  quote_position=state_hyper.quote_position - transfer_amount, unrealized_pnl=state_hyper.unrealized_pnl, MMF_pct=(MMF_HYPER * 100),
            )
            
            # добавить проверку на margin usage
            
            if hypo_margin_ratio_hyper > MARGIN_RATIO_TARGET and transfer_amount >= 10:
                self.active_rebalance = Rebalance(
                    to_exchange="binance",
                    amount_usdc=transfer_amount,
                    wip=False,
                    on_blockchain=False,
                    timestamp_create=int(time.time() * 1000),
                    timestamp_sent_to_blockchain=None,
                    timestamp_sent_to_exchange=None,
                )
                send_alert(alert_type="info", json_data=self.active_rebalance.to_dict())
            
        if state_hyper.margin_ratio < MARGIN_RATIO_REBALANCE_TH:
            send_alert(alert_type="warning", json_data={"hyper": f"margin ratio = {state_hyper.margin_ratio:.2f}", "action": "REBALANCE mode is on"})
            
            transfer_amount = self.calculateTopUpForMarginRatio(
                mid_price=mid_price, base_position=state_hyper.base_position, quote_position=state_hyper.quote_position, unrealized_pnl=state_hyper.unrealized_pnl, MMF_pct=(MMF_HYPER * 100),
            )
            transfer_amount = int(transfer_amount)
            hypo_margin_ratio_binance = self.calc_margin_ratio(
                mid_price=mid_price, base_position=state_binance.base_position,  quote_position=state_binance.quote_position - transfer_amount, unrealized_pnl=state_binance.unrealized_pnl, MMF_pct=(MMF_BINANCE * 100),
            )
            
            if hypo_margin_ratio_binance > MARGIN_RATIO_TARGET and transfer_amount >= 10:
                self.active_rebalance = Rebalance(
                    to_exchange="hyper",
                    amount_usdc=transfer_amount,
                    wip=False,
                    on_blockchain=False,
                    timestamp_create=int(time.time() * 1000),
                    timestamp_sent_to_blockchain=None,
                    timestamp_sent_to_exchange=None,
                )
                send_alert(alert_type="info", json_data=self.active_rebalance.to_dict())
        
        
        
    def compute_position_target(
        self,
        state_binance: AccountState,
        state_hyper: AccountState,
        mid_price: float
    ):
        effective_quote_positio = min(state_binance.quote_position, state_hyper.quote_position)
        min_strategy_leverate = min(state_binance.leverage, state_hyper.leverage)
        target_position_binance = (effective_quote_positio * min_strategy_leverate) / mid_price
        
        hypo_margin_ratio_binance = self.calc_margin_ratio(
            mid_price=mid_price, base_position=state_binance.base_position+self.deal_size, quote_position=state_binance.quote_position, 
            unrealized_pnl=state_binance.unrealized_pnl, MMF_pct=(MMF_BINANCE * 100)
        )
        hypo_margin_ratio_hyper = self.calc_margin_ratio(
            mid_price=mid_price, base_position=state_hyper.base_position-self.deal_size, quote_position=state_hyper.quote_position, 
            unrealized_pnl=state_hyper.unrealized_pnl, MMF_pct=(MMF_HYPER * 100)
        )
        
        hypo_margin_usage_binance = self.calc_margin_usage(
            mid_price=mid_price, base_position=state_binance.base_position+self.deal_size, quote_position=state_binance.quote_position, 
            unrealized_pnl=state_binance.unrealized_pnl, IMF_pct=(IMF_BINANCE * 100)
        )
        hypo_margin_usage_hyper = self.calc_margin_usage(
            mid_price=mid_price, base_position=state_hyper.base_position-self.deal_size, quote_position=state_hyper.quote_position, 
            unrealized_pnl=state_hyper.unrealized_pnl, IMF_pct=(IMF_HYPER * 100)
        )
        
        max_quote_position_binance = state_binance.quote_position * LEVERAGE_BINANCE
        max_quote_position_hyper = state_hyper.quote_position * LEVERAGE_HYPER
    
        effective_quote_position = min(max_quote_position_binance, max_quote_position_hyper)
        target_position_binance = (effective_quote_position) / mid_price
        
        position_condition = state_binance.base_position < target_position_binance
        margin_usage_condition = hypo_margin_usage_binance < MARGIN_USAGE_ENTRY_TH and hypo_margin_usage_hyper < MARGIN_USAGE_ENTRY_TH
        margin_ratio_condition = hypo_margin_ratio_binance > MARGIN_RATIO_TARGET and hypo_margin_ratio_hyper > MARGIN_RATIO_TARGET
        
        
        if position_condition and margin_usage_condition and margin_ratio_condition:
            self.allowed_long_binance = True
        else:
            self.allowed_long_binance = False    
            
        # ------ скрутить позицию ------
        # if state_binance.base_position > 0:
        #     self.allowed_short_binance = True
        # else:
        #     self.allowed_short_binance = False
        # ------------------------------
        
        
    
    def cacl_inventory(
        self,
        mid_price: float,
        quote_position: float,
        base_position: float,
        IMF: float
    ):
        max_leg_quote_position = (quote_position) * (100 / IMF)
        inventory = base_position / (max_leg_quote_position / mid_price)
        return inventory
    
    def calc_unrealized_pnl(
        self,
        mid_price: float,
        entry_price: float,
        base_position: float,
    ):
        unrealized_pnl = (mid_price - entry_price) * base_position
        return unrealized_pnl
    
    def calc_margin_usage(
        self,
        mid_price: float,
        base_position: float,
        quote_position: float,
        unrealized_pnl: float,
        IMF_pct: float
    ):
        notional = abs(base_position) * mid_price
        equity = quote_position + unrealized_pnl
        if equity <= 0:
            return 1e+6
    
        initial_perp_margin = (IMF_pct / 100) * notional
    
        margin_usage = initial_perp_margin / equity
        return margin_usage
    
    def calc_margin_ratio(
        self,
        mid_price: float,
        base_position: float,
        quote_position: float,
        unrealized_pnl: float,
        MMF_pct: float
    ) -> float:
        notional = abs(base_position) * mid_price
        equity = quote_position + unrealized_pnl
    
        if notional == 0:
            return 100
        
        maintenance_margin = (MMF_pct / 100) * notional
        margin_ratio = equity / maintenance_margin
        return margin_ratio
    
    def calculateTopUpForMarginRatio(
        self,
        mid_price,
        base_position,
        quote_position,
        unrealized_pnl,
        MMF_pct,
    ):
        equity = quote_position + unrealized_pnl
        
        if equity <= 0:
            return None  # уже ликвидация / unsafe
        
        position_size = abs(base_position)
        notional = position_size * mid_price
        
        if notional == 0:
            return 0  # нет позиции — не нужно пополнять
        
        maintenance_margin = (MMF_pct / 100) * notional        
        current_ratio = equity / maintenance_margin
        
        if current_ratio >= MARGIN_RATIO_TARGET:
            return 0
        
        required_equity = MARGIN_RATIO_TARGET * maintenance_margin
        topUp = required_equity - equity
        return max(topUp, 0)
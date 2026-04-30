import os
import time
import math
import asyncio
import numpy as np
from decimal import Decimal
from collections import deque


from src.stores import AccountDataStoreBinance, AccountDataStoreHyper, MarketDataStore
from src.managers import BinanceManager, HyperManager, OrderManager, RiskManager
from src.logging import LOG_ENABLED, log_event
from src.alerting import AlertTradingService


class Strategy:
    def __init__(
        self, 
        binance_manager: BinanceManager,
        hyper_manager: HyperManager,
    ) -> None:
        self.binance_manager = binance_manager
        self.hyper_manager = hyper_manager
        self.risk_manager = RiskManager()
        self.order_manager = OrderManager(binance_manager=binance_manager, hyper_manager=hyper_manager)
        self.alert_trading_service = AlertTradingService()
        
    
    async def step(
        self,
        stop_event,
        market_data_store: MarketDataStore,
        account_data_store_hyper: AccountDataStoreHyper,
        account_data_store_binance: AccountDataStoreBinance
    ) -> None:
        while not stop_event.is_set():
            await asyncio.sleep(0.5)
            
            self.order_manager.update(
                store_binance=account_data_store_binance, 
                store_hyper=account_data_store_hyper,
            )
            
            if market_data_store.bbo_binance is None \
                or market_data_store.orderbook_binance is None \
                or market_data_store.bbo_hyper is None \
                or market_data_store.orderbook_hyper is None:
                await asyncio.sleep(0.05)
                continue
            
            mid_price_binance = (market_data_store.orderbook_binance.ask_price_list[0] + market_data_store.orderbook_binance.bid_price_list[0]) / 2
            mid_price_hyper = (market_data_store.bbo_hyper.ask_price_1 + market_data_store.bbo_hyper.bid_price_1) / 2
            
            account_data_store_binance.update(mid_price=mid_price_binance)
            account_data_store_hyper.update(mid_price=mid_price_hyper)
            
            self.risk_manager.update(
                state_binance=account_data_store_binance.state, 
                state_hyper=account_data_store_hyper.state, 
                mid_price=mid_price_binance
            )
            
            one_bps = ((mid_price_binance + mid_price_hyper) / 2) * 1e-4
            spread_in_bps = (mid_price_binance - mid_price_hyper) / one_bps
            
            
            my_ask_price = market_data_store.orderbook_binance.ask_price_list[0] + 0.4
            my_bid_price = market_data_store.orderbook_binance.bid_price_list[0] - 0.4
            
            
            if self.risk_manager.allowed_long_binance:
                self.order_manager.create_limit_order_binance(
                    account_data_store_binance,
                    is_long=True,
                    qty=0.02,
                    price=my_bid_price,
                )
                
                self.order_manager.modify_limit_order_binance(
                    limit_order=account_data_store_binance.long_limit_order,
                    price=my_bid_price,
                    qty=account_data_store_binance.long_limit_order.qty
                )
            else:
                self.order_manager.cancel_limit_order_binance(
                    limit_order=account_data_store_binance.long_limit_order
                )
            
            
            
            # print(account_data_store_binance.state)
            # print()
            
            # print(account_data_store_hyper.state)
            # print()
            
            # print("="*50)
            
            self.alert_trading_service.update(state_binance=account_data_store_binance.state, state_hyper=account_data_store_hyper.state)
            
            # print(f"bbo_binance: {market_data_store.bbo_binance}")
            # print(f"bbo_hyper: {market_data_store.bbo_hyper}")
            # print(f"orderbook_binance: {market_data_store.orderbook_binance}")
            # print(f"orderbook_hyper: {market_data_store.orderbook_hyper}")
            # print()
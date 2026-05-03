import os
import asyncio
import time
from dotenv import load_dotenv


from src.entities import AccountState, BlockchainState, RiskMode
from src.entities.shared import Rebalance
from src.stores import AccountDataStoreBinance, AccountDataStoreHyper, MarketDataStore
from src.managers import BlockchainManager, BinanceManager, HyperManager, OrderManager, RiskManager
from src.logging import LOG_ENABLED, log_event
from src.alerting import AlertTradingService, send_alert


load_dotenv()

STRATEGY_FREQUENCY = float(os.getenv("STRATEGY_FREQUENCY"))


class Strategy:
    def __init__(
        self, 
        blockchain_manager: BlockchainManager,
        binance_manager: BinanceManager,
        hyper_manager: HyperManager,
    ) -> None:
        self.blockchain_manager = blockchain_manager
        self.binance_manager = binance_manager
        self.hyper_manager = hyper_manager
        self.risk_manager = RiskManager()
        self.order_manager = OrderManager(binance_manager=binance_manager, hyper_manager=hyper_manager)
        self.alert_trading_service = AlertTradingService()
        
        
    def rebalance(
        self, 
        state_binance: AccountState,
        state_hyper: AccountState,
        state_blockchain: BlockchainState,
    ):
        
        if self.risk_manager.active_rebalance is None:
            return

        if self.risk_manager.active_rebalance.wip:
            return
        
        self.risk_manager.active_rebalance.wip = True
            
        if self.risk_manager.active_rebalance.to_exchange == "binance":
            task = asyncio.create_task(self.rebalance_hyper_to_binance(state_binance, state_hyper, state_blockchain))
    
        if self.risk_manager.active_rebalance.to_exchange == "hyper":
            task = asyncio.create_task(self.rebalance_binance_to_hyper(state_binance, state_hyper, state_blockchain))
    
    async def rebalance_binance_to_hyper(
        self, 
        state_binance: AccountState,
        state_hyper: AccountState,
        state_blockchain: BlockchainState,
    ):
        
        if state_binance.quote_position_spot < self.risk_manager.active_rebalance.amount_usdc + 1:
            await self.binance_manager.transfer_perp_to_spot(asset="USDC", amount=self.risk_manager.active_rebalance.amount_usdc + 1)
            await asyncio.sleep(3)
        
        # вывести деньги с binance на arb wallet
        self.risk_manager.active_rebalance.timestamp_sent_to_blockchain = int(time.time() * 1000)
        send_alert(alert_type="warning", json_data={"action": f"send {self.risk_manager.active_rebalance.amount_usdc:.2f} from binance to operating wallet"})
        await self.binance_manager.withdraw(amount_in_usdc=self.risk_manager.active_rebalance.amount_usdc + 1)
        send_alert(alert_type="warning", json_data={"action": f"sent {self.risk_manager.active_rebalance.amount_usdc:.2f} from binance to operating wallet"})
        
        # дождаться поступления денег на arb wallet
        start = time.time()
        start_usdc_amount_blockchain = state_blockchain.amount_usdc
        while True:
            usdc_amount_blockchain = await self.blockchain_manager.get_usdc_amount()
            
            if usdc_amount_blockchain - start_usdc_amount_blockchain >= self.risk_manager.active_rebalance.amount_usdc - 1:
                self.risk_manager.active_rebalance.on_blockchain = True
                send_alert(alert_type="warning", json_data={"action": f"operating wallet received {self.risk_manager.active_rebalance.amount_usdc:.2f} from binance"})
                break
            
            if time.time() - start > 600:
                # error
                return
            
            await asyncio.sleep(5)
            
            
        quote_position_hyper_old = state_hyper.quote_position
        
        # перевести деньги c arb wallet на hyper
        send_alert(alert_type="warning", json_data={"action": f"send {self.risk_manager.active_rebalance.amount_usdc:.2f} from operating wallet to hyper"})
        self.risk_manager.timestamp_sent_to_exchange = time.time()
        await self.blockchain_manager.deposit_hyper(amount_in_usdc=self.risk_manager.active_rebalance.amount_usdc)
        send_alert(alert_type="warning", json_data={"action": f"sent {self.risk_manager.active_rebalance.amount_usdc:.2f} from operating wallet to hyper"})
        
        while True:
            if state_hyper.quote_position - quote_position_hyper_old >= self.risk_manager.active_rebalance.amount_usdc - 1:
                send_alert(alert_type="warning", json_data={"action": f"hyper received {self.risk_manager.active_rebalance.amount_usdc:.2f} from blockchain"})
                break
            
            if time.time() - self.risk_manager.timestamp_sent_to_exchange > 1200:
                # error
                return
            
            await asyncio.sleep(5)
            
        await asyncio.sleep(5)
        self.risk_manager.active_rebalance = None
        send_alert(alert_type="info", json_data={"action": f"rebalancing binance -> hyper was successful"})
    
    
    async def rebalance_hyper_to_binance(
        self, 
        state_binance: AccountState,
        state_hyper: AccountState,
        state_blockchain: BlockchainState,
    ):
        # вывести деньги с hyper на arb wallet
        self.risk_manager.active_rebalance.timestamp_sent_to_blockchain = int(time.time() * 1000)
        send_alert(alert_type="warning", json_data={"action": f"send {self.risk_manager.active_rebalance.amount_usdc:.2f} from hyper to operating wallet"})
        await self.hyper_manager.withdraw(amount_in_usdc=self.risk_manager.active_rebalance.amount_usdc + 1)
        send_alert(alert_type="warning", json_data={"action": f"sent {self.risk_manager.active_rebalance.amount_usdc:.2f} from hyper to operating wallet"})
        
        # дождаться поступления денег на arb wallet
        start = time.time()
        start_usdc_amount_blockchain = await self.blockchain_manager.get_usdc_amount()
        while True:
            usdc_amount_blockchain = await self.blockchain_manager.get_usdc_amount()
            
            if usdc_amount_blockchain - start_usdc_amount_blockchain >= self.risk_manager.active_rebalance.amount_usdc - 1:
                self.risk_manager.active_rebalance.on_blockchain = True
                send_alert(alert_type="warning", json_data={"action": f"operating wallet received {self.risk_manager.active_rebalance.amount_usdc:.2f} from hyper"})
                break
            
            if time.time() - start > 600:
                # error
                return
            
            await asyncio.sleep(5)
        
        # перевести деньги c arb wallet на hyper
        send_alert(alert_type="warning", json_data={"action": f"send {self.risk_manager.active_rebalance.amount_usdc:.2f} from operating wallet to binance"})
        await self.blockchain_manager.deposit_binance(amount_in_usdc=self.risk_manager.active_rebalance.amount_usdc)
        send_alert(alert_type="warning", json_data={"action": f"sent {self.risk_manager.active_rebalance.amount_usdc:.2f} from operating wallet to binance"})
    
    async def step(
        self,
        stop_event,
        market_data_store: MarketDataStore,
        state_blockchain: BlockchainState,
        store_binance: AccountDataStoreBinance,
        store_hyper: AccountDataStoreHyper,
    ) -> None:
        while not stop_event.is_set():
            await asyncio.sleep(STRATEGY_FREQUENCY)
            
            self.order_manager.update(store_binance=store_binance, store_hyper=store_hyper)
            
            self.blockchain_manager.update_state(state=state_blockchain)
            self.binance_manager.update_state(state=store_binance.state)
            self.hyper_manager.update_state(state=store_hyper.state)
            
            if market_data_store.bbo_binance is None \
                or market_data_store.orderbook_binance is None \
                or market_data_store.bbo_hyper is None \
                or market_data_store.orderbook_hyper is None:
                await asyncio.sleep(0.05)
                continue
            
            mid_price_binance = (market_data_store.orderbook_binance.ask_price_list[0] + market_data_store.orderbook_binance.bid_price_list[0]) / 2
            mid_price_hyper = (market_data_store.bbo_hyper.ask_price_1 + market_data_store.bbo_hyper.bid_price_1) / 2
            
            store_binance.update(mid_price=mid_price_binance)
            store_hyper.update(mid_price=mid_price_hyper)
            
            self.risk_manager.update(
                state_binance=store_binance.state, 
                state_hyper=store_hyper.state,
                state_blockchain=state_blockchain,
                mid_price=mid_price_binance,
            )
            
            one_bps = ((mid_price_binance + mid_price_hyper) / 2) * 1e-4
            spread_in_bps = (mid_price_binance - mid_price_hyper) / one_bps
            
            
            my_ask_price = market_data_store.orderbook_binance.ask_price_list[0] + 0.4
            my_bid_price = market_data_store.orderbook_binance.bid_price_list[0] - 0.4
            
            
            if self.risk_manager.risk_mode == RiskMode.REBALANCE:
                self.rebalance(state_binance=store_binance.state, state_hyper=store_hyper.state, state_blockchain=state_blockchain)
            
            
            if self.risk_manager.risk_mode == RiskMode.NORMAL:
                
                # ----- long -----
                if self.risk_manager.allowed_long_binance:
                    self.order_manager.create_limit_order_binance(
                        store_binance,
                        is_long=True,
                        qty=0.02,
                        price=my_bid_price,
                    )
                    
                    self.order_manager.modify_limit_order_binance(
                        limit_order=store_binance.long_limit_order,
                        price=my_bid_price,
                        qty=store_binance.long_limit_order.qty
                    )
                else:
                    self.order_manager.cancel_limit_order_binance(
                        limit_order=store_binance.long_limit_order
                    )
                
                # ----- short -----
                if self.risk_manager.allowed_short_binance:
                    self.order_manager.create_limit_order_binance(
                        store_binance,
                        is_long=False,
                        qty=0.02,
                        price=my_ask_price,
                    )
                    
                    self.order_manager.modify_limit_order_binance(
                        limit_order=store_binance.short_limit_order,
                        price=my_ask_price,
                        qty=store_binance.short_limit_order.qty
                    )
                else:
                    self.order_manager.cancel_limit_order_binance(
                        limit_order=store_binance.short_limit_order
                    )
            
            
            
            # print(account_data_store_binance.state)
            # print()
            
            # print(account_data_store_hyper.state)
            # print()
            
            # print("="*50)
            
            
            self.alert_trading_service.update(
                state_binance=store_binance.state, state_hyper=store_hyper.state, state_blockchain=state_blockchain
            )
            
            # print(f"bbo_binance: {market_data_store.bbo_binance}")
            # print(f"bbo_hyper: {market_data_store.bbo_hyper}")
            # print(f"orderbook_binance: {market_data_store.orderbook_binance}")
            # print(f"orderbook_hyper: {market_data_store.orderbook_hyper}")
            # print()
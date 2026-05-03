import time
import asyncio


from src.entities import LimitOrder
from src.stores import AccountDataStoreBinance, AccountDataStoreHyper
from src.managers import BinanceManager, HyperManager


class OrderManager:
    def __init__(
        self,
        binance_manager: BinanceManager, 
        hyper_manager: HyperManager
    ) -> None:
        self.binance_manager=binance_manager
        self.hyper_manager=hyper_manager
        
        self.ORDER_COOLDOWN_CREATE_MS = 100
        self.ORDER_COOLDOWN_MODIFY_MS = 100
        
        self.last_timestamp_long_order_create = 0
        self.last_timestamp_short_order_create = 0
        
        self.last_timestamp_long_order_modify = 0
        self.last_timestamp_short_order_modify = 0
        
        self.instructions_list = []
        
    def update(
        self,
        store_binance: AccountDataStoreBinance,
        store_hyper: AccountDataStoreHyper,
    ):
        self.hedge_update(store_binance=store_binance, store_hyper=store_hyper)
        self.callback_update(store_binance=store_binance, store_hyper=store_hyper)
        
        
    def hedge_update(
        self,
        store_binance: AccountDataStoreBinance,
        store_hyper: AccountDataStoreHyper,
    ):
        if len(store_binance.need_hedge_list) == 0:
            return
        
        for instructions in store_binance.need_hedge_list:
            self.create_taker_order_hyper(instructions=instructions)
        store_binance.need_hedge_list.clear()
        
        
    def callback_update(
        self,
        store_binance: AccountDataStoreBinance,
        store_hyper: AccountDataStoreHyper,
    ):
        if len(self.instructions_list) == 0:
            return
        
        for instructions in self.instructions_list:
            if instructions["action"] == "reset":
                
                if store_binance.long_limit_order:
                    if store_binance.long_limit_order.client_id == instructions["client_order_id"]:
                        store_binance.long_limit_order = None
                
                if store_binance.short_limit_order:
                    if store_binance.short_limit_order.client_id == instructions["client_order_id"]:
                        store_binance.short_limit_order = None
        
        self.instructions_list.clear()
        
        
    def create_taker_order_hyper(self, instructions):
        if instructions["exchange"] == "hyper":
            asyncio.create_task(
                self.hyper_manager.create_taker_order(
                    asset="ETH",
                    is_long=instructions["is_long"],
                    qty=instructions["qty"],
                    limit_price=instructions["price"] + 20 if instructions["is_long"] else instructions["price"] - 20,
                    id=instructions["client_order_id"]
                )
            )
    
    def create_limit_order_binance(
        self,
        store: AccountDataStoreBinance,
        is_long: bool,
        price: float,
        qty: float
    ):
        if is_long:
            if store.long_limit_order:
                return
            
            if int(time.time() * 1000) - self.last_timestamp_long_order_create < self.ORDER_COOLDOWN_CREATE_MS:
                return
            
            print("create long limit order")
            
            timestamp_sent = int(time.time() * 1000)
            limit_order = LimitOrder(
                client_id=str(timestamp_sent),
                asset="ETHUSDC",
                is_long=is_long,
                price=round(price, 2),
                qty=qty,
                timestamp_sent_order=timestamp_sent,
                timestamp_sent_modify=None,
                timestamp_sent_cancel=None,
                pending_posting=True,
                pending_modify=False,
                pending_cancellation=False,
            )
            store.long_limit_order = limit_order
            
            task = asyncio.create_task(
                self.binance_manager.create_limit_order(
                    client_order_id=limit_order.client_id,
                    asset=limit_order.asset,
                    is_long=limit_order.is_long,
                    qty=limit_order.qty,
                    price=limit_order.price,
                )
            )
            task.client_id = str(timestamp_sent)
            task.add_done_callback(self._handle_task_result)
            self.last_timestamp_long_order_create = int(time.time() * 1000)
            
        else:
            if store.short_limit_order:
                return
            
            timestamp_sent = int(time.time() * 1000)
            limit_order = LimitOrder(
                client_id=str(timestamp_sent),
                asset="ETHUSDC",
                is_long=is_long,
                price=round(price, 2),
                qty=qty,
                timestamp_sent_order=timestamp_sent,
                timestamp_sent_modify=None,
                timestamp_sent_cancel=None,
                pending_posting=True,
                pending_modify=False,
                pending_cancellation=False,
            )
            store.short_limit_order = limit_order
            
            task = asyncio.create_task(
                self.binance_manager.create_limit_order(
                    client_order_id=limit_order.client_id,
                    asset=limit_order.asset,
                    is_long=limit_order.is_long,
                    qty=limit_order.qty,
                    price=limit_order.price,
                )
            )
            task.client_id = str(timestamp_sent)
            task.add_done_callback(self._handle_task_result)
            
            
    def modify_limit_order_binance(
        self,
        limit_order: LimitOrder,
        price: float,
        qty: float
    ):
        if limit_order:
            if limit_order.pending_posting or limit_order.pending_modify or limit_order.pending_cancellation:
                return
            
            if int(time.time() * 1000) - self.last_timestamp_long_order_modify < self.ORDER_COOLDOWN_MODIFY_MS:
                return
            
            if abs(limit_order.price - round(price, 2)) < 0.1:
                return
            
            limit_order.price = round(price, 2)
            limit_order.qty = qty
            limit_order.pending_modify = True
            
            print("modify long limit order")
            
            task = asyncio.create_task(
                self.binance_manager.modify_order(
                    asset=limit_order.asset,
                    client_order_id=limit_order.client_id,
                    is_long=limit_order.is_long,
                    qty=limit_order.qty,
                    price=limit_order.price,
                )
            )
            task.client_id = limit_order.client_id
            task.add_done_callback(self._handle_task_result)
            self.last_timestamp_long_order_modify = int(time.time() * 1000)
            
    def cancel_limit_order_binance(
        self,
        limit_order: LimitOrder,
    ):
        if limit_order:
            if limit_order.pending_posting or limit_order.pending_cancellation:
                return
            
            limit_order.pending_cancellation = True
            
            task = asyncio.create_task(
                self.binance_manager.cancel_order(
                    asset=limit_order.asset,
                    client_order_id=limit_order.client_id
                )
            )
            task.client_id = limit_order.client_id
            task.add_done_callback(self._handle_task_result)
            
            
    def _handle_task_result(self, task):
        client_id = getattr(task, "client_id", None)
        try:
            res = task.result()
            
            if res == -5022:
                # ордер не приняли из-за пересечения orderbook
                self.instructions_list.append({
                    "client_order_id": client_id,
                    "action": "reset"
                })
                
            if res == -2019:
                # недостаточно маржи для открытия новой позиции (initial margin)
                self.instructions_list.append({
                    "client_order_id": client_id,
                    "action": "reset"
                })
                
            if res == -2013:
                # попытка модификации ордера которого уже не существует.
                self.instructions_list.append({
                    "client_order_id": client_id,
                    "action": "reset"
                })
            
        except Exception as e:
            print("Task failed:", e)
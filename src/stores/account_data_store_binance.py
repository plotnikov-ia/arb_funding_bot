import time

from src.entities import AccountState, LimitOrder

class AccountDataStoreBinance:
    def __init__(self, state) -> None:
        self.state: AccountState = state
        
        self.need_hedge_list = []
        
        self.long_limit_order: LimitOrder = None
        self.short_limit_order: LimitOrder = None
        
    def update(self, mid_price: float):
        self.state.ts = int(time.time() * 1000)
        if self.state.base_position != 0:
            self.state.unrealized_pnl = (mid_price - self.state.entry_price) * self.state.base_position
            self.state.equity = self.state.quote_position + self.state.unrealized_pnl
            
            notional = abs(self.state.base_position) * mid_price
            self.state.initial_margin_requirement = notional / self.state.leverage
            self.state.maintenance_margin_requirement = notional * 0.004
            
        else:
            self.state.initial_margin_requirement = 0
            self.state.maintenance_margin_requirement = 0
        
    def update_account(self, data):
        timestamp_event = int(data["E"])
        self.state.ts = timestamp_event
        
        if data["a"]["m"] == "DEPOSIT" or data["a"]["m"] == "WITHDRAW":
            for item in data["a"]["B"]:
                if item["a"] == "USDC":
                    self.state.quote_position = float(item["wb"])
                    self.state.equity = self.state.quote_position + self.state.unrealized_pnl
                    return
                    
        if data["a"]["m"] == "FUNDING_FEE":
            for item in data["a"]["B"]:
                if item["a"] == "USDC":
                    funding_payment = float(item["bc"])
                    return
                
        if data["a"]["m"] == "ORDER":
            # обновление аккаунта после фила
            for item in data["a"]["P"]:
                if item["s"] == "ETHUSDC":
                    self.state.base_position = float(item["pa"])
                    self.state.entry_price = float(item["ep"])
                    self.state.unrealized_pnl = float(item["up"])
                    
            for item in data["a"]["B"]:
                if item["a"] == "USDC":
                    self.state.quote_position = float(item["wb"])
                    self.state.equity = self.state.quote_position + self.state.unrealized_pnl
            
        
    def update_order(self, data):
        
        timestamp_event = int(data["E"])
        self.state.ts = timestamp_event
        
        if data["o"]["s"] != "ETHUSDC":
            return
        
        event = data["o"]["x"]
        status = data["o"]["X"]
        client_order_id = str(data["o"]["c"])
        order_id = data["o"]["i"]
        side = data["o"]["S"]   # BUY or SELL
        price = float(data["o"]["p"])
        qty = float(data["o"]["q"])
        
        if event == "NEW" and status == "NEW":            
            # ордер встал в стакан
            if self.long_limit_order:
                if self.long_limit_order.client_id == client_order_id:
                    self.long_limit_order.pending_posting = False
                    
                    print("new")
                    print(self.long_limit_order)
                    print()
                    
            if self.short_limit_order:
                if self.short_limit_order.client_id == client_order_id:
                    self.short_limit_order.pending_posting = False
                    
                    print("new")
                    print(self.short_limit_order)
                    print()
            
        if event == "AMENDMENT" and status == "NEW":
            # ордер был модифицирован
            if self.long_limit_order:
                if self.long_limit_order.client_id == client_order_id:
                    self.long_limit_order.pending_posting = False
                    self.long_limit_order.pending_modify = False
                 
                    print("modify")
                    print(self.long_limit_order)
                    print()
        
            if self.short_limit_order:
                if self.short_limit_order.client_id == client_order_id:
                    self.short_limit_order.pending_posting = False
                    self.short_limit_order.pending_modify = False
                 
                    print("modify")
                    print(self.short_limit_order)
                    print()
        
        if event == "CANCELED" and status == "CANCELED":
            # ордер был закрыт
            if self.long_limit_order:
                if self.long_limit_order.client_id == client_order_id:
                    self.long_limit_order = None
            
                    print("cancel")
                    print(self.long_limit_order)
                    print()

            if self.short_limit_order:
                if self.short_limit_order.client_id == client_order_id:
                    self.short_limit_order = None
            
                    print("cancel")
                    print(self.short_limit_order)
                    print()
        
        
        if event == "TRADE":
            side = data["o"]["S"]   # BUY or SELL
            price = float(data["o"]["p"])
            executed_now = float(data["o"]["l"])
            executed_all = float(data["o"]["z"])
            fee = float(data["o"]["n"])
            
            if status == "FILLED":
                # ордер полностью зафилили
                if self.long_limit_order:
                    if self.long_limit_order.client_id == client_order_id:
                        self.long_limit_order = None
                
                        print("filled")
                        print(self.long_limit_order)
                        print()

                if self.short_limit_order:
                    if self.short_limit_order.client_id == client_order_id:
                        self.short_limit_order = None
                
                        print("filled")
                        print(self.short_limit_order)
                        print()
            
            instructions = {
                "exchange": "hyper",
                "client_order_id": client_order_id,
                "is_long": False if side == "BUY" else True,
                "qty": executed_now,
                "price": price
                
            }
            self.need_hedge_list.append(instructions)
            
        
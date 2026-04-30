import time

from src.entities import AccountState

class AccountDataStoreHyper:
    def __init__(self, state) -> None:
        self.state: AccountState = state
        
        
    def update(self, mid_price: float):
        self.state.ts = int(time.time() * 1000)
        if self.state.base_position != 0:
            self.state.unrealized_pnl = (mid_price - self.state.entry_price) * self.state.base_position
            self.state.equity = self.state.quote_position + self.state.unrealized_pnl
            
            notional = abs(self.state.base_position) * mid_price
            self.state.initial_margin_requirement = notional / self.state.leverage
            self.state.maintenance_margin_requirement = notional * ((1 / 25) / 2) # 25 - max leverage
            
        else:
            self.state.initial_margin_requirement = 0
            self.state.maintenance_margin_requirement = 0
        
        
    def update_cash_flow(self, data):
        for cash_flow_item in data["data"]["nonFundingLedgerUpdates"]:
            timestamp = int(cash_flow_item["time"])
            self.state.ts = timestamp
            
            hash = cash_flow_item["hash"]
            
            if cash_flow_item["delta"]["type"] == "withdraw":
                usdc = float(cash_flow_item["delta"]["usdc"])
            
            if cash_flow_item["delta"]["type"] == "deposit":
                usdc = float(cash_flow_item["delta"]["usdc"]) 
                
    def update_spot_state(self, data):
        for asset_balance in data["data"]["spotState"]["balances"]:
            if asset_balance["coin"] == "USDC":
                
                self.state.equity = float(asset_balance["total"])
                self.state.quote_position = self.state.equity - self.state.unrealized_pnl
                break
        
    def update_perp_state(self, data):
        if len(data["data"]["clearinghouseState"]["assetPositions"]) == 0:
            self.state.ts = int(data["data"]["clearinghouseState"]["time"])
                
            self.state.base_position = 0.0
            
            self.state.entry_price = 0.0
            self.state.unrealized_pnl = 0.0
            
            self.state.liquidation_price = 0.0
            
            self.state.initial_margin_requirement = 0.0
            self.state.maintenance_margin_requirement = 0.0
            return
        
        for asset_position in data["data"]["clearinghouseState"]["assetPositions"]:
            if asset_position["position"]["coin"] == "ETH":
                
                self.state.ts = int(data["data"]["clearinghouseState"]["time"])
                
                self.state.base_position = float(asset_position["position"]["szi"])
                
                self.state.entry_price = float(asset_position["position"]["entryPx"])
                self.state.unrealized_pnl = float(asset_position["position"]["unrealizedPnl"])
                
                self.state.liquidation_price = float(asset_position["position"]["liquidationPx"])
                
                self.state.initial_margin_requirement = float(asset_position["position"]["marginUsed"])
                self.state.maintenance_margin_requirement = float(data["data"]["clearinghouseState"]["crossMaintenanceMarginUsed"])
                break
            
    def update_fills(self, data):
        pass
        
import os
import time
import asyncio
from eth_utils import keccak
from hyperliquid.utils.types import Cloid
from dotenv import load_dotenv


from src.entities import AccountState
from src.exchange_adapters.rest.hyper_api_client import HyperApiClient
from src.logging import LOG_ENABLED, log_event

load_dotenv()

LEVERAGE_HYPER = os.getenv("LEVERAGE_HYPER", "")
STATE_UPDATE_FREQUENCY_REST = float(os.getenv("STATE_UPDATE_FREQUENCY_REST"))


class HyperManager:
    def __init__(self, secrets):
        self.api_client = HyperApiClient(secrets=secrets)
        self.last_state_update_timestamp = 0
        
    async def init_state(
        self, 
        state: AccountState,
    ):
        state = await self.load_exchange_data(state)
        return state
        
    async def load_exchange_data(
        self, 
        state: AccountState,
    ):
        raw_spot_account_data = await self.api_client.get_spot_state()
        raw_perp_account_data = await self.api_client.get_perp_state()
        
        for item in raw_spot_account_data['balances']:
            if item["coin"] == "USDC":
                state.equity = float(item["total"])
                break
            
        state.ts = int(raw_perp_account_data["time"])
        
        if len(raw_perp_account_data["assetPositions"]) != 0:
            for item in raw_perp_account_data["assetPositions"]:
                if item["position"]["coin"] == "ETH":
                    
                    state.base_position = float(item["position"]["szi"])
                    state.entry_price = float(item["position"]["entryPx"])
                    state.unrealized_pnl = float(item["position"]["unrealizedPnl"])
                    
                    state.leverage = int(item["position"]["leverage"]["value"])
                    state.liquidation_price = float(item["position"]["liquidationPx"]) if item["position"]["liquidationPx"] is not None else None
                    
                    state.initial_margin_requirement = float(raw_perp_account_data["marginSummary"]["totalMarginUsed"])
                    state.maintenance_margin_requirement = float(raw_perp_account_data["crossMaintenanceMarginUsed"])
                    
                    state.quote_position = state.equity - state.unrealized_pnl
                    break
        else:
            state.quote_position = state.equity
            state.base_position = 0.0
            
            state.entry_price = 0.0
            state.unrealized_pnl = 0.0
            
            state.leverage = int(LEVERAGE_HYPER)
            state.liquidation_price = 0.0
            
            state.initial_margin_requirement = 0.0
            state.maintenance_margin_requirement = 0.0
            
        return state
    
    def update_state(
        self, 
        state: AccountState,
    ):
        now = time.time()
        if now - self.last_state_update_timestamp > STATE_UPDATE_FREQUENCY_REST:
            self.last_state_update_timestamp = now
            asyncio.create_task(self._update_state(state=state))
            
    async def _update_state(
        self, 
        state: AccountState,
    ):
        raw_spot_account_data = await self.api_client.get_spot_state()
        raw_perp_account_data = await self.api_client.get_perp_state()
        
        for item in raw_spot_account_data['balances']:
            if item["coin"] == "USDC":
                state.equity = float(item["total"])
                break
            
        state.ts = int(raw_perp_account_data["time"])
        
        if len(raw_perp_account_data["assetPositions"]) != 0:
            for item in raw_perp_account_data["assetPositions"]:
                if item["position"]["coin"] == "ETH":
                    
                    state.base_position = float(item["position"]["szi"])
                    state.entry_price = float(item["position"]["entryPx"])
                    state.unrealized_pnl = float(item["position"]["unrealizedPnl"])
                    
                    state.leverage = int(item["position"]["leverage"]["value"])
                    state.liquidation_price = float(item["position"]["liquidationPx"]) if item["position"]["liquidationPx"] is not None else None
                    
                    state.initial_margin_requirement = float(raw_perp_account_data["marginSummary"]["totalMarginUsed"])
                    state.maintenance_margin_requirement = float(raw_perp_account_data["crossMaintenanceMarginUsed"])
                    
                    state.quote_position = state.equity - state.unrealized_pnl
                    break
        else:
            state.quote_position = state.equity
            state.base_position = 0.0
            
            state.entry_price = 0.0
            state.unrealized_pnl = 0.0
            
            state.leverage = int(LEVERAGE_HYPER)
            state.liquidation_price = 0.0
            
            state.initial_margin_requirement = 0.0
            state.maintenance_margin_requirement = 0.0
        
    async def set_leverage(
        self,
        asset: str,
    ):
        await self.api_client.set_leverage(asset=asset, leverage=LEVERAGE_HYPER)
        
    async def create_taker_order(
        self,
        asset: str,
        is_long: bool,
        qty: float,
        limit_price: float,
        id: str = None
    ):  
        if id is None:
            raw = keccak(text=str(int(time.time() * 1000)))[:16]
            cloid = Cloid("0x" + raw.hex())
        else:
            raw = keccak(text=id)[:16]
            cloid = Cloid("0x" + raw.hex())
        
        limit_price = round(limit_price, 1)
        
        LOG_ENABLED and log_event("hyper_manager", action="send taker order")
        response = await self.api_client.create_taker_order(
            asset=asset,
            is_long=is_long,
            qty=qty,
            limit_price=limit_price,
            cloid=cloid
        )
        LOG_ENABLED and log_event("hyper_manager", action="sent taker order", message=str(response))
        
    async def withdraw(self, amount_in_usdc: float):
        await self.api_client.withdraw(amount=amount_in_usdc)
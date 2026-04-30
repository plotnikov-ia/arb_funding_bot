import os
import time
import asyncio
from eth_utils import keccak
from hyperliquid.utils.types import Cloid
from dotenv import load_dotenv

from src.logging import LOG_ENABLED, log_event
from src.exchange_adapters.rest.hyper_api_client import HyperApiClient

load_dotenv()

LEVERAGE_HYPER = os.getenv("LEVERAGE_HYPER", "")


class HyperManager:
    def __init__(self, secrets):
        self.api_client = HyperApiClient(secrets=secrets)
        
    async def init_state(self, state):
        state = await self.load_exchange_data(state)
        return state
        
    async def load_exchange_data(self, state):
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
        
    async def set_leverage(
        self,
        asset: str,
    ):
        await self.api_client.set_leverage(
            asset=asset,
            leverage=LEVERAGE_HYPER,
        )
        
    async def create_taker_order(
        self,
        asset: str,
        is_long: bool,
        qty: float,
        limit_price: float,
        cloid: str = None
    ):  
        if cloid is None:
            raw = keccak(text=str(int(time.time() * 1000)))[:16]
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
        
    async def deposit(self, amount_in_usdc: float):
        amount = int(amount_in_usdc * 1_000_000)  # USDC = 6 decimals
        await self.api_client.deposit(amount=amount)
        
    async def withdraw(self, amount_in_usdc: float):
        await self.api_client.withdraw(amount=amount_in_usdc)
        
        
            
    def __str__(self):
        return (
            f"=== Hyper Account State ===\n"
            f"Quote position (USDC): {self.quote_position:.2f}\n"
            f"Base position:         {self.base_position:.6f}\n"
            f"\n"
            f"Entry price:           {round(self.entry_price, 2) if self.entry_price else self.entry_price}\n"
            f"Unrealized PnL:        {self.unrealized_pnl:.2f}\n"
            f"Equity:                {self.equity:.2f}\n"
            f"\n"
            f"Leverage:              {self.leverage}x\n"
            f"Liquidation price:     {round(self.liquidation_price, 2) if self.liquidation_price else self.liquidation_price}\n"
            f"\n"
            f"Initial margin:        {self.initial_margin_requirement:.2f}\n"
            f"Maintenance margin:    {self.maintenance_margin_requirement:.2f}\n"
        )
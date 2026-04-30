import os
import time
import math
from dotenv import load_dotenv
from dataclasses import dataclass


from src.logging import LOG_ENABLED, log_event
from src.exchange_adapters.rest.binance_api_client import BinanceApiClient

load_dotenv()

LEVERAGE_BINANCE = os.getenv("LEVERAGE_BINANCE", "")


@dataclass
class PendingDeposit:
    id: int
    amount: float
    coin: str
    network: str
    status: int
    address: str
    addressTag: str
    txId: str
    insertTime: int
    transferType: int
    confirmTimes: str
    unlockConfirm: int


class BinanceManager:
    def __init__(self, secrets):
        self.api_client = BinanceApiClient(secrets=secrets)
        
        self.pending_deposit_list = []
        
    async def init_state(self, state):
        state = await self.load_exchange_data(state)
        return state
        
    async def load_exchange_data(self, state):
        raw_perp_account_info = await self.api_client.get_perp_account_data()
        raw_spot_account_info = await self.api_client.get_spot_account_data()
        raw_risk_info = await self.api_client.get_risk_info(asset="ETHUSDC")
        
        for item in raw_spot_account_info['balances']:
            if item["asset"] == "USDC":
                state.quote_position_spot = float(item["free"])
        
        for account_info in raw_perp_account_info['assets']:
            if account_info["asset"] == "USDC":
                state.quote_position = float(account_info["walletBalance"])
                state.initial_margin_requirement = float(account_info["initialMargin"])
                state.maintenance_margin_requirement = float(account_info["maintMargin"])
                break
            
        state.ts = int(raw_risk_info[0]["updateTime"])
                
        state.base_position = float(raw_risk_info[0]["positionAmt"])
        
        state.entry_price = float(raw_risk_info[0]["entryPrice"])
        state.unrealized_pnl = float(raw_risk_info[0]["unRealizedProfit"])
        
        state.leverage = float(raw_risk_info[0]["leverage"])
        state.liquidation_price = float(raw_risk_info[0]["liquidationPrice"])
                
        state.equity = state.quote_position + state.unrealized_pnl
        
        deposit_history = await self.api_client.get_deposit_history() 
                
        for item in deposit_history:
            if item["status"] != 1:
                state.locked_quote_position_spot += float(item["amount"])

                pending_deposit = PendingDeposit(
                    id=item["id"],
                    amount=float(item["amount"]),
                    coin=item["coin"],
                    network=item.get("network", "BASE"),
                    status=item.get("status", 6),
                    address=item.get("address", ""),
                    addressTag=item.get("addressTag", ""),
                    txId=item.get("txId", ""),
                    insertTime=item.get("insertTime", 0),
                    transferType=item.get("transferType", 0),
                    confirmTimes=item.get("confirmTimes", ""),
                    unlockConfirm=item.get("unlockConfirm", 0),
                )

                self.pending_deposit_list.append(pending_deposit)
                
        return state
        
        
    async def update_risk_info(self, asset):
        risk_info = await self.api_client.get_risk_info(asset=asset)
        return risk_info
                
    async def transfer_perp_to_spot(
        self,
        asset: str,
        amount: float,
    ):
        
        if self.assets_info is None:
            return None
        
        if self.assets_info[asset]["walletBalance"] < amount:
            return None
        
        data = await self.api_client.transfer_perp_to_spot(
            asset=asset,
            amount=amount
        )
        
    async def transfer_spot_to_perp(
        self,
        asset: str,
        amount: float,
        all: bool = False,
    ):
        if all:
            amount = self.quote_position
        
        if amount <= 1:
            return None
        
        amount = math.floor(amount)
        
        if self.quote_position is None or self.quote_position < amount:
            return None
        
        data = await self.api_client.transfer_spot_to_perp(
            asset=asset, amount=amount
        )
        
    async def set_leverage(
        self,
        asset: str,
    ):
        data = await self.api_client.set_leverage(asset=asset, leverage=LEVERAGE_BINANCE)
        

    async def create_limit_order(
        self,
        client_order_id: str,
        asset: str,
        is_long: bool,
        qty: float,
        price: float,
        time_in_force: str = "GTX",
    ):
        
        if client_order_id is None:
            client_order_id = str(int(time.time() * 1000))
        
        LOG_ENABLED and log_event("binance_manager", action="send limit order")
        response = await self.api_client.create_limit_order(
            client_order_id=client_order_id,
            asset=asset,
            is_long=is_long,
            qty=qty,
            price=price,
            time_in_force=time_in_force,
        )
        LOG_ENABLED and log_event("binance_manager", action="sent limit order", message=str(response))
        return response
        
    async def modify_order(
        self,
        asset: str,
        client_order_id: str,
        is_long: str,
        qty: float,
        price: float,
    ):
        LOG_ENABLED and log_event("binance_manager", action="send modify limit order")
        response = await self.api_client.modify_order(
            asset=asset,
            client_order_id=client_order_id,
            is_long=is_long,
            qty=qty,
            price=price,
        )
        LOG_ENABLED and log_event("binance_manager", action="sent modify limit order")
        
    async def cancel_order(
        self,
        asset: str,
        client_order_id: int,
    ):
        LOG_ENABLED and log_event("binance_manager", action="send cancel limit order")
        response = await self.api_client.cancel_order(
            asset=asset,
            client_order_id=client_order_id
        )
        LOG_ENABLED and log_event("binance_manager", action="sent cancel limit order")
        
    async def withdraw(
        self,
        amount: float,
    ):
        if self.assets_info is None:
            return None
        
        if self.assets_info["USDC"]["free"] < amount:
            print("insufficient funds for withdrawal")
            return
        
        data = await self.api_client.withdraw(amount=amount)
        
    async def deposit(
        self,
        amount: float,
    ):
        data = await self.api_client.deposit(
            amount=amount
        )
        
        
    def __str__(self):
        return (
            f"=== Binance Perp Account State ===\n"
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
        
        
                
        
import os
from web3 import Web3
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from dotenv import load_dotenv

from src.logging import LOG_ENABLED, log_event

load_dotenv()

HYPER_WALLET_ADDRESS = os.getenv("HYPER_WALLET_ADDRESS", "")
OPERATING_WALLET_ADDRESS = os.getenv("OPERATING_WALLET_ADDRESS", "")


class HyperApiClient:
    def __init__(self, secrets) -> None:
        self.secrets = secrets
        self.info_feed = Info(skip_ws=True)
        
        self.account = Account.from_key(self.secrets.get("HYPER_WALLET_PRIVATE_KEY"))
        self.exchange_feed = Exchange(self.account, constants.MAINNET_API_URL)
        
    async def get_perp_state(self):
        response = self.info_feed.user_state(address=HYPER_WALLET_ADDRESS)
        return response
    
    async def get_spot_state(self):
        response = self.info_feed.spot_user_state(address=HYPER_WALLET_ADDRESS)
        return response
    
    
    async def set_leverage(
        self,
        asset: str = "ETH",
        leverage: int = 20
    ):
        response = self.exchange_feed.update_leverage(
            leverage=int(leverage),
            name=asset, 
            is_cross=True,
        )
        return response
    
    async def create_taker_order(
        self,
        asset: str,
        is_long: bool,
        qty: float,
        limit_price: float,
        cloid
    ):  
        try:
            LOG_ENABLED and log_event("hyper_api_client", action="send taker order")
            response = self.exchange_feed.order(
                name=asset,
                is_buy=is_long,
                sz=qty,
                limit_px=limit_price,
                order_type={"limit": {"tif": "Ioc"}},
                cloid=cloid
            )
            return response
        except Exception as e:
            LOG_ENABLED and log_event("hyper_api_client", action="sent taker order", error=str(e))
            return
        
    async def withdraw(self, amount: float):
        
        wallet = Account.from_key(self.secrets.get("OPERATING_WALLET_PRIVATE_KEY"))
        account_address = wallet.address
        print(f"account_address: {account_address}")

        exchange = Exchange(wallet, constants.MAINNET_API_URL, account_address=account_address)

        # Важная проверка: agent wallets не могут выводить средства
        if exchange.account_address != exchange.wallet.address:
            raise RuntimeError("Withdraw нельзя делать через API/agent wallet. Нужен основной wallet.")

        result = exchange.withdraw_from_bridge(amount, OPERATING_WALLET_ADDRESS)
    
    
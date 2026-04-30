import os
from web3 import Web3
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from dotenv import load_dotenv

from src.logging import LOG_ENABLED, log_event

load_dotenv()

ARB_RPC = os.getenv("ARB_RPC", "")
USDC_ARB_ADDRESS = os.getenv("USDC_ARB_ADDRESS", "")

HYPER_WALLET_ADDRESS = os.getenv("HYPER_WALLET_ADDRESS", "")
HYPER_BRIDGE_CONTRACT_ADDRESS = os.getenv("HYPER_BRIDGE_CONTRACT_ADDRESS", "")

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
    
    
    async def deposit(self, amount: int):
        
        USDC = Web3.to_checksum_address(USDC_ARB_ADDRESS)
        BRIDGE = Web3.to_checksum_address(HYPER_BRIDGE_CONTRACT_ADDRESS)
        
        w3 = Web3(Web3.HTTPProvider(ARB_RPC))
        account = Account.from_key(self.secrets.get("OPERATING_WALLET_PRIVATE_KEY"))
        address = account.address
        
        ERC20_ABI = [
            {
                "name": "transfer",
                "type": "function",
                "stateMutability": "nonpayable",
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "amount", "type": "uint256"}
                ],
                "outputs": [{"name": "", "type": "bool"}],
            }
        ]

        usdc = w3.eth.contract(address=USDC, abi=ERC20_ABI)

        tx = usdc.functions.transfer(BRIDGE, amount).build_transaction({
            "from": address,
            "nonce": w3.eth.get_transaction_count(address),
            "gas": 100000,
            "gasPrice": w3.eth.gas_price,
            "chainId": 42161,
        })

        signed_tx = w3.eth.account.sign_transaction(tx, self.secrets.get("OPERATING_WALLET_PRIVATE_KEY"))
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash = w3.to_hex(tx_hash)
        
        
    async def withdraw(self, amount: float):
        
        wallet = Account.from_key(self.secrets.get("OPERATING_WALLET_PRIVATE_KEY"))
        account_address = wallet.address
        print(f"account_address: {account_address}")

        exchange = Exchange(wallet, constants.MAINNET_API_URL, account_address=account_address)

        # Важная проверка: agent wallets не могут выводить средства
        if exchange.account_address != exchange.wallet.address:
            raise RuntimeError("Withdraw нельзя делать через API/agent wallet. Нужен основной wallet.")

        result = exchange.withdraw_from_bridge(amount, OPERATING_WALLET_ADDRESS)
    
    
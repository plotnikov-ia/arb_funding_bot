import os
import time
import aiohttp
import orjson
import hmac
import hashlib
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from urllib.parse import urlencode

from src.logging import LOG_ENABLED, log_event

load_dotenv()

ARB_RPC = os.getenv("ARB_RPC", "")
USDC_ARB_ADDRESS = os.getenv("USDC_ARB_ADDRESS", "")

OPERATING_WALLET_ADDRESS = os.getenv("OPERATING_WALLET_ADDRESS", "")

HYPER_BRIDGE_CONTRACT_ADDRESS = os.getenv("HYPER_BRIDGE_CONTRACT_ADDRESS", "")

BINANCE_SPOT_BASE_URL = os.getenv("BINANCE_SPOT_BASE_URL", "")


class BlockchainApiClient:
    def __init__(self, secrets) -> None:
        self.secrets = secrets
        self.account = Account.from_key(self.secrets.get("HYPER_WALLET_PRIVATE_KEY"))
        
        
    def sign(self, query: str) -> str:
        return hmac.new(
            self.secrets.get("BINANCE_HMAC_API_SECRET").encode(),
            query.encode(),
            hashlib.sha256
        ).hexdigest()
        
    async def get_balance_data(self):
        w3 = Web3(Web3.HTTPProvider(ARB_RPC))
        address = Web3.to_checksum_address(OPERATING_WALLET_ADDRESS)
        token_address = Web3.to_checksum_address(USDC_ARB_ADDRESS)

        abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function",
            },
        ]

        contract = w3.eth.contract(address=token_address, abi=abi)

        balance = contract.functions.balanceOf(address).call()
        decimals = contract.functions.decimals().call()
        amount_usdc = float(balance / (10 ** decimals))

        return amount_usdc
        
    async def deposit_binance(
        self,
        amount: float,
        recv_window_ms: int = 5000,
    ):
        # --- 1. получить адрес депозита Binance ---
        params = {
            "coin": "USDC",
            "network": "ARBITRUM",
            "recvWindow": recv_window_ms,
            "timestamp": int(time.time() * 1000),
        }

        query = urlencode(params)
        signature = self.sign(query)

        url = f"{BINANCE_SPOT_BASE_URL}/sapi/v1/capital/deposit/address?{query}&signature={signature}"

        headers = {"X-MBX-APIKEY": self.secrets.get("BINANCE_HMAC_API_KEY")}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                raw = await resp.read()

                if resp.status != 200:
                    raise RuntimeError(f"deposit addr error: {resp.status} {raw}")

                data = orjson.loads(raw)

        deposit_address = Web3.to_checksum_address(data["address"])
        
        
        ERC20_ABI = [
            {
                "name": "transfer",
                "type": "function",
                "stateMutability": "nonpayable",
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"},
                ],
                "outputs": [{"name": "", "type": "bool"}],
            }
        ]

        # --- 2. отправить USDC через Arbitrum ---
        w3 = Web3(Web3.HTTPProvider(ARB_RPC))
        account = Account.from_key(self.secrets.get("OPERATING_WALLET_PRIVATE_KEY"))

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ARB_ADDRESS),
            abi=ERC20_ABI
        )

        deposit_address = Web3.to_checksum_address(deposit_address)

        amount_wei = int(amount * 1_000_000)
        
        base_fee = w3.eth.get_block("latest")["baseFeePerGas"]
        priority_fee = w3.to_wei(0.01, "gwei")
        max_fee = base_fee * 2 + priority_fee

        tx = contract.functions.transfer(
            deposit_address,
            amount_wei
        ).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 100000,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee,
            "chainId": 42161,
            "type": 2,
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return {
            "deposit_address": deposit_address,
            "tx_hash": tx_hash.hex(),
        }
    
    async def deposit_hyper(self, amount: int):
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

        latest_block = w3.eth.get_block("pending")
        base_fee = latest_block.get("baseFeePerGas", w3.eth.gas_price)
        priority_fee = w3.to_wei(0.05, "gwei")
        max_fee = int(base_fee * 2 + priority_fee)

        tx = usdc.functions.transfer(BRIDGE, amount).build_transaction({
            "from": address,
            "nonce": w3.eth.get_transaction_count(address, "pending"),
            "gas": 100000,
            "maxPriorityFeePerGas": priority_fee,
            "maxFeePerGas": max_fee,
            "type": 2,
            "chainId": 42161,
        })

        signed_tx = w3.eth.account.sign_transaction(
            tx,
            self.secrets.get("OPERATING_WALLET_PRIVATE_KEY")
        )
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return w3.to_hex(tx_hash)
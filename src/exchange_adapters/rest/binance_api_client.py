import json
import os
import time
import hmac
import hashlib
import aiohttp
import orjson
from web3 import Web3
from eth_account import Account
from urllib.parse import urlencode
from dotenv import load_dotenv


from src.logging import LOG_ENABLED, log_event

load_dotenv()

ARB_RPC = os.getenv("ARB_RPC", "")
USDC_ARB_ADDRESS = os.getenv("USDC_ARB_ADDRESS", "")

BINANCE_SPOT_BASE_URL = os.getenv("BINANCE_SPOT_BASE_URL", "")
BINANCE_PERP_BASE_URL = os.getenv("BINANCE_PERP_BASE_URL", "")

OPERATING_WALLET_ADDRESS = os.getenv("OPERATING_WALLET_ADDRESS", "")



class BinanceApiClient:
    def __init__(self, secrets):
        self.secrets = secrets
        pass
    
    def sign(self, query: str) -> str:
        return hmac.new(
            self.secrets.get("BINANCE_HMAC_API_SECRET").encode(),
            query.encode(),
            hashlib.sha256
        ).hexdigest()
    
    async def get_perp_account_data(self):
        ts = int(time.time() * 1000)
        query = f"timestamp={ts}"
        signature = self.sign(query)

        url = f"{BINANCE_PERP_BASE_URL}/fapi/v3/account?{query}&signature={signature}"

        headers = {
            "X-MBX-APIKEY": self.secrets.get("BINANCE_HMAC_API_KEY")
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                raw = await resp.read()

                if resp.status != 200:
                    raise RuntimeError(f"{resp.status} {raw}")

                data = orjson.loads(raw)
                
        return data
    
    async def get_spot_account_data(self):
        ts = int(time.time() * 1000)
        query = f"timestamp={ts}"

        signature = self.sign(query)
        url = f"{BINANCE_SPOT_BASE_URL}/api/v3/account?{query}&signature={signature}"

        headers = {
            "X-MBX-APIKEY": self.secrets.get("BINANCE_HMAC_API_KEY")
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                raw = await resp.read()

                if resp.status != 200:
                    raise RuntimeError(f"{resp.status} {raw}")
                
                data = orjson.loads(raw)

        return data
    
    async def transfer_perp_to_spot(
        self,
        asset: str,
        amount: float,
        recv_window_ms: int = 5000,
    ):
        params = {
            "type": "UMFUTURE_MAIN",
            "asset": asset,
            "amount": amount,
            "recvWindow": recv_window_ms,
            "timestamp": int(time.time() * 1000),
        }

        query = urlencode(params)
        signature = self.sign(query)
        url = f"{BINANCE_SPOT_BASE_URL}/sapi/v1/asset/transfer?{query}&signature={signature}"

        headers = {
            "X-MBX-APIKEY": self.secrets.get("BINANCE_HMAC_API_KEY"),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as resp:
                raw = await resp.read()

                if resp.status != 200:
                    raise RuntimeError(f"transfer error: {resp.status} {raw}")

                data = orjson.loads(raw)
        
        return data
    
    async def transfer_spot_to_perp(
        self,
        asset: str,
        amount: str,
        recv_window_ms: int = 5000,
    ):
        params = {
            "type": "MAIN_UMFUTURE",
            "asset": asset,
            "amount": amount,
            "recvWindow": recv_window_ms,
            "timestamp": int(time.time() * 1000),
        }

        query = urlencode(params)
        signature = self.sign(query)
        url = f"{BINANCE_SPOT_BASE_URL}/sapi/v1/asset/transfer?{query}&signature={signature}"

        headers = {
            "X-MBX-APIKEY": self.secrets.get("BINANCE_HMAC_API_KEY"),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as resp:
                raw = await resp.read()

                if resp.status != 200:
                    raise RuntimeError(f"spot->usdm transfer error: {resp.status} {raw}")

                data = orjson.loads(raw)
                
        return data
    
    async def set_leverage(
        self,
        asset: str, 
        leverage: int
    ):
        params = {
            "symbol": asset,
            "leverage": int(leverage),
            "timestamp": int(time.time() * 1000),
        }

        query = urlencode(params)
        signature = self.sign(query)

        url = f"{BINANCE_PERP_BASE_URL}/fapi/v1/leverage?{query}&signature={signature}"

        headers = {"X-MBX-APIKEY": self.secrets.get("BINANCE_HMAC_API_KEY")}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as resp:
                return resp


    async def get_risk_info(self, asset: str):
        params = {
            "symbol": asset,
            "timestamp": int(time.time() * 1000),
        }

        query = urlencode(params)
        signature = self.sign(query)

        url = f"{BINANCE_PERP_BASE_URL}/fapi/v2/positionRisk?{query}&signature={signature}"

        headers = {
            "X-MBX-APIKEY": self.secrets.get("BINANCE_HMAC_API_KEY"),
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                raw = await resp.read()

                if resp.status != 200:
                    raise RuntimeError(f"positionRisk error: {resp.status} {raw}")

                data = orjson.loads(raw)

        return data

    async def create_limit_order(
        self,
        client_order_id: str,
        asset: str,
        is_long: bool,
        qty: float,
        price: float,
        time_in_force: str = "GTX",
        recv_window_ms: int = 5000,
    ):
        params = {
            "symbol": asset,
            "side": "BUY" if is_long else "SELL",
            "type": "LIMIT",
            "timeInForce": time_in_force,
            "quantity": qty,
            "price": price,
            "newClientOrderId": client_order_id,
            "recvWindow": recv_window_ms,
            "timestamp": int(time.time() * 1000),
        }

        try:
            LOG_ENABLED and log_event("binance_api_client", action="send limit order")
            query = urlencode(params)
            signature = self.sign(query)

            url = f"{BINANCE_PERP_BASE_URL}/fapi/v1/order?{query}&signature={signature}"

            headers = {
                "X-MBX-APIKEY": self.secrets.get("BINANCE_HMAC_API_KEY"),
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers) as resp:
                    raw = await resp.read()

                    if resp.status != 200:
                        raise RuntimeError(f"order error: {resp.status} {raw}")

                    data = orjson.loads(raw)
                    return data
                
        except Exception as e:
            error_str = str(e)
            json_part = error_str.split("b'")[1].rstrip("'")
            error_dict = json.loads(json_part)
            code = error_dict.get("code")
            msg = error_dict.get("msg")
            LOG_ENABLED and log_event("binance_api_client", action="sent limit order", error=error_str)
            return code
    
    async def modify_order(
        self,
        asset: str,
        client_order_id: str,
        is_long: str,
        qty: float,
        price: float,
        recv_window_ms: int = 5000,
    ):
        params = {
            "symbol": asset,
            "side": "BUY" if is_long else "SELL",
            "quantity": qty,
            "price": price,
            "origClientOrderId": client_order_id,
            "timestamp": int(time.time() * 1000),
            "recvWindow": recv_window_ms,
        }
        
        try:
            LOG_ENABLED and log_event("binance_api_client", action="send modify limit order")
            
            query = urlencode(params)
            signature = self.sign(query)

            url = f"{BINANCE_PERP_BASE_URL}/fapi/v1/order?{query}&signature={signature}"

            headers = {
                "X-MBX-APIKEY": self.secrets.get("BINANCE_HMAC_API_KEY"),
            }

            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers) as resp:
                    raw = await resp.read()

                    if resp.status != 200:
                        raise RuntimeError(f"modify error: {resp.status} {raw}")

                    data = orjson.loads(raw)
                    return data
                
        except Exception as e:
            LOG_ENABLED and log_event("binance_api_client", action="sent modify limit order", error=str(e))
            return
    
    async def cancel_order(
        self,
        asset: str,
        client_order_id: int,
        recv_window_ms: int = 5000,
    ):
        params = {
            "symbol": asset,
            "origClientOrderId": client_order_id,
            "recvWindow": recv_window_ms,
            "timestamp": int(time.time() * 1000),
        }

        try:
            LOG_ENABLED and log_event("binance_api_client", action="send cancel limit order")
            query = urlencode(params)
            signature = self.sign(query)

            url = f"{BINANCE_PERP_BASE_URL}/fapi/v1/order?{query}&signature={signature}"

            headers = {
                "X-MBX-APIKEY": self.secrets.get("BINANCE_HMAC_API_KEY"),
            }

            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=headers) as resp:
                    raw = await resp.read()

                    if resp.status != 200:
                        raise RuntimeError(f"cancel error: {resp.status} {raw}")

                    data = orjson.loads(raw)
                    return data
        
        except Exception as e:
            LOG_ENABLED and log_event("binance_api_client", action="sent cancel limit order", error=str(e))
            return
    
    
    async def get_deposit_history(self):
        params = {
            "timestamp": int(time.time() * 1000),
            "limit": 10,
        }

        query = urlencode(params)
        signature = self.sign(query)

        url = f"{BINANCE_SPOT_BASE_URL}/sapi/v1/capital/deposit/hisrec?{query}&signature={signature}"

        headers = {
            "X-MBX-APIKEY": self.secrets.get("BINANCE_HMAC_API_KEY"),
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                raw = await resp.read()

                if resp.status != 200:
                    raise RuntimeError(f"{resp.status} {raw}")

                data = orjson.loads(raw)
                
        return data
    
    async def withdraw(
        self,
        amount: float,
        recv_window_ms: int = 5000,
    ):
        params = {
            "coin": "USDC",
            "address": OPERATING_WALLET_ADDRESS,
            "amount": amount,
            "network": "ARBITRUM",
            "recvWindow": recv_window_ms,
            "timestamp": int(time.time() * 1000),
        }

        query = urlencode(params)
        signature = self.sign(query)

        url = f"{BINANCE_SPOT_BASE_URL}/sapi/v1/capital/withdraw/apply?{query}&signature={signature}"

        headers = {
            "X-MBX-APIKEY": self.secrets.get("BINANCE_HMAC_API_KEY"),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as resp:
                raw = await resp.read()

                if resp.status != 200:
                    raise RuntimeError(f"withdraw error: {resp.status} {raw}")

                data = orjson.loads(raw)
                print(data)

        return data
    
    async def deposit(
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
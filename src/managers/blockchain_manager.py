import os
import time
import asyncio
from dotenv import load_dotenv

from src.entities import BlockchainState
from src.exchange_adapters.rest.blockchain_api_client import BlockchainApiClient
from src.logging import LOG_ENABLED, log_event

load_dotenv()

STATE_UPDATE_FREQUENCY_REST = float(os.getenv("STATE_UPDATE_FREQUENCY_REST"))


class BlockchainManager:
    def __init__(self, secrets):
        self.api_client = BlockchainApiClient(secrets=secrets)
        self.last_state_update_timestamp = 0
        
    async def init_state(
        self, 
        state: BlockchainState,
    ):
        state = await self.load_exchange_data(state)
        return state
        
    async def load_exchange_data(
        self, 
        state: BlockchainState,
    ):
        amount_usdc = await self.api_client.get_balance_data()
        state.ts = int(time.time() * 1000)
        state.amount_usdc = amount_usdc
        return state
    
    def update_state(
        self, 
        state: BlockchainState,
    ):
        now = time.time()
        if now - self.last_state_update_timestamp > STATE_UPDATE_FREQUENCY_REST:
            self.last_state_update_timestamp = now
            asyncio.create_task(self._update_state(state=state))
            
    async def _update_state(
        self, 
        state: BlockchainState,
    ):
        amount_usdc = await self.api_client.get_balance_data()
        state.ts = int(time.time() * 1000)
        state.amount_usdc = amount_usdc
        
    async def deposit_hyper(
        self, 
        amount_in_usdc: float
    ):
        amount = int(amount_in_usdc * 1_000_000)
        await self.api_client.deposit(amount=amount)
        
    async def deposit_binance(
        self,
        amount_in_usdc: float,
    ):
        amount_in_usdc = int(amount_in_usdc)
        data = await self.api_client.deposit(amount=amount_in_usdc)
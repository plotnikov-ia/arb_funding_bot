import asyncio
import time

from src.security import Secrets

from src.managers import BinanceManager, HyperManager, BlockchainManager

from src.entities.account_data.account_state import AccountState, BlockchainState

from src.stores import MarketDataStore, AccountDataStoreBinance, AccountDataStoreHyper

from src.handlers.market_data import MarketDataHandlerBinance, MarketDataHandlerHyper
from src.handlers.account_data import AccountHandlerBinance, AccountHandlerHyper

from src.exchange_adapters.ws.account_data import connect_account_binance, connect_account_hyper
from src.exchange_adapters.ws.market_data import connect_bbo_binance, connect_bbo_hyper, connect_orderbook_binance, connect_orderbook_hyper

from src.strategy import Strategy

from src.logging import setup_logging
from src.logging import LOG_ENABLED, log_event
from src.alerting import send_alert


async def main() -> None:
    stop_event = asyncio.Event()
    account_connected_event = asyncio.Event()
    
    listener = setup_logging()
    
    LOG_ENABLED and log_event("main", action="loading secrets")
    secrets = Secrets()
    secrets.load_secrets()
    LOG_ENABLED and log_event("main", action="secrets loaded")
    send_alert(alert_type="warning", json_data={"event": "secrets loaded"})
    
    LOG_ENABLED and log_event("main", action="init market data")
    
    market_data_store = MarketDataStore()
    market_data_handler_binance = MarketDataHandlerBinance(store=market_data_store)
    market_data_handler_hyper = MarketDataHandlerHyper(store=market_data_store)
    
    LOG_ENABLED and log_event("main", action="init blockchain account")
    blockchain_manager = BlockchainManager(secrets=secrets)
    state_blockchain = await blockchain_manager.init_state(BlockchainState())
    
    LOG_ENABLED and log_event("main", action="init hyper account")
    
    hyper_manager = HyperManager(secrets=secrets)
    await hyper_manager.set_leverage(asset="ETH")
    state_hyper = await hyper_manager.init_state(AccountState(exchange="hyper"))
    store_hyper = AccountDataStoreHyper(state=state_hyper)
    account_data_handler_hyper = AccountHandlerHyper(store=store_hyper)
    
    LOG_ENABLED and log_event("main", action="init binance account")
    
    binance_manager = BinanceManager(secrets=secrets)
    await binance_manager.set_leverage(asset="ETHUSDC")
    state_binance = await binance_manager.init_state(AccountState(exchange="binance"))
    store_binance = AccountDataStoreBinance(state=state_binance)
    account_data_handler_binance = AccountHandlerBinance(store=store_binance)
    
    strategy = Strategy(
        blockchain_manager=blockchain_manager,
        binance_manager=binance_manager,
        hyper_manager=hyper_manager,
    )
    
    LOG_ENABLED and log_event("main", action="ws connecting")
    
    
    tasks = [
        asyncio.create_task(connect_bbo_binance(market_data_handler_binance, secrets), name="ws_market_data_feed_bbo_binance"),
        asyncio.create_task(connect_orderbook_binance(market_data_handler_binance), name="ws_market_data_feed_orderbook_binance"),
        asyncio.create_task(connect_bbo_hyper(market_data_handler_hyper), name="ws_market_data_feed_bbo_hyper"),
        asyncio.create_task(connect_orderbook_hyper(market_data_handler_hyper), name="ws_market_data_feed_orderbook_hyper"),
        
        asyncio.create_task(connect_account_binance(account_data_handler_binance, account_connected_event, secrets), name="ws_account_data_binance"),
        asyncio.create_task(connect_account_hyper(account_data_handler_hyper), name="ws_account_data_hyper"),
    ]
    
    
    await account_connected_event.wait()

    LOG_ENABLED and log_event("main", action="strategy started")
    send_alert(alert_type="info", json_data={"event": "strategy started"})

    tasks.append(
        asyncio.create_task(
            strategy.step(
                stop_event=stop_event,
                market_data_store=market_data_store,
                state_blockchain=state_blockchain,
                store_binance=store_binance,
                store_hyper=store_hyper,
            )
        )
    )
    
    await stop_event.wait()

    for t in tasks:
        t.cancel()

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError as e:
        LOG_ENABLED and log_event("main", error=str(e))
        pass
    
    
if __name__ == "__main__":
    asyncio.run(main())
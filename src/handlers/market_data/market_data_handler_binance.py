import time
import orjson


from src.stores.market_data_store import MarketDataStore


class MarketDataHandlerBinance:
    def __init__(
        self,
        store: MarketDataStore
    ) -> None:
        self.last_bbo_binance_msg = time.monotonic()
        self.last_orderbook_binance_msg = time.monotonic()
        
        self.store = store
    
        
    def handle_bbo_binance(self, data):
        self.last_bbo_binance_msg = time.monotonic()
        self.store.update_bbo_binance(data=data)
                
    def handle_orderbook_binance(self, raw: bytes):
        self.last_orderbook_binance_msg = time.monotonic()
        json_data = orjson.loads(raw)
        self.store.update_orderbook_binance(ts=json_data["E"], raw_asks=json_data["a"], raw_bids=json_data["b"])
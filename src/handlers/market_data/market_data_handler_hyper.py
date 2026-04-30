import time
import orjson

from src.stores.market_data_store import MarketDataStore

class MarketDataHandlerHyper:
    def __init__(
        self,
        store: MarketDataStore
    ) -> None:
        self.last_bbo_hyper_msg = time.monotonic()
        self.last_orderbook_hyper_msg = time.monotonic()
        
        self.store = store
        
    def handle_bbo_hyper(self, raw: bytes):
        self.last_bbo_hyper_msg = time.monotonic()
        json_data = orjson.loads(raw)
        
        if json_data["channel"] == "subscriptionResponse":
            pass
        
        if json_data["channel"] == "bbo":
            self.store.update_bbo_hyper(data=json_data)
        
    def handle_orderbook_hyper(self, raw: bytes):
        self.last_orderbook_hyper_msg = time.monotonic()
        
        json_data = orjson.loads(raw)
        
        if json_data["channel"] == "subscriptionResponse":
            pass
        
        if json_data["channel"] == "l2Book":
            self.store.update_orderbook_hyper(ts=json_data["data"]["time"], raw_asks=json_data["data"]["levels"][1], raw_bids=json_data["data"]["levels"][0])
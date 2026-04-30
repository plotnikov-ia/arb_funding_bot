from src.entities import Orderbook, BBO


class MarketDataStore:
    def __init__(self) -> None:
        
        self.depth = 5
        
        self.bbo_binance: BBO = None
        self.bbo_hyper: BBO = None
        
        self.orderbook_binance: Orderbook = None
        self.orderbook_hyper: Orderbook = None
        
        
    def update_bbo_binance(self, data):
        (event_time, book_update_id, bid_price, bid_qty, ask_price, ask_qty) = data
        
        self.bbo_binance = BBO(
            ts=int(event_time),
            book_update_id=int(book_update_id),
            bid_price_1=float(bid_price),
            bid_qty_1=float(bid_qty),
            ask_price_1=float(ask_price),
            ask_qty_1=float(ask_qty),
        )
    
    def update_bbo_hyper(self, data):
        self.bbo_hyper = BBO(
            ts=int(data["data"]["time"]),
            book_update_id=int(0),
            bid_price_1=float(data["data"]["bbo"][0]["px"]),
            bid_qty_1=float(data["data"]["bbo"][0]["sz"]),
            ask_price_1=float(data["data"]["bbo"][1]["px"]),
            ask_qty_1=float(data["data"]["bbo"][1]["sz"]),
        )
        
        
    def update_orderbook_binance(
        self, 
        ts: str, 
        raw_asks: list, 
        raw_bids: list
    ):
        ask_price_list = []
        ask_qty_list = []
        bid_price_list = []
        bid_qty_list = []
            
        for ask in raw_asks[:self.depth]:
            ask_price_list.append(float(ask[0]))
            ask_qty_list.append(float(ask[1]))
            
        for bid in raw_bids[:self.depth]:
            bid_price_list.append(float(bid[0]))
            bid_qty_list.append(float(bid[1]))
        
        self.orderbook_binance = Orderbook(
            ts=int(ts),
            bid_price_list=bid_price_list,
            bid_qty_list=bid_qty_list,
            ask_price_list=ask_price_list,
            ask_qty_list=ask_qty_list,
        )
        
    def update_orderbook_hyper(
        self, 
        ts: str, 
        raw_asks: list, 
        raw_bids: list
    ):
        ask_price_list = []
        ask_qty_list = []
        bid_price_list = []
        bid_qty_list = []
        
        for ask in raw_asks[:self.depth]:
            ask_price_list.append(float(ask["px"]))
            ask_qty_list.append(float(ask["sz"]))
    
        for bid in raw_bids[:self.depth]:
            bid_price_list.append(float(bid["px"]))
            bid_qty_list.append(float(bid["sz"]))
            
        self.orderbook_hyper = Orderbook(
            ts=int(ts),
            bid_price_list=bid_price_list,
            bid_qty_list=bid_qty_list,
            ask_price_list=ask_price_list,
            ask_qty_list=ask_qty_list,
        )
                    
        

    # def get(self):
    #     for i, (p, q) in enumerate(islice(self.bids.items(), self.depth)):
    #         self._bid_price_np[i] = p
    #         self._bid_qty_np[i] = q

    #     for i, (p, q) in enumerate(islice(self.asks.items(), self.depth)):
    #         self._ask_price_np[i] = p
    #         self._ask_qty_np[i] = q

    #     return Orderbook(
    #         ts=self.ts,
    #         bid_price_list=self._bid_price_np.copy(),
    #         bid_qty_list=self._bid_qty_np.copy(),
    #         ask_price_list=self._ask_price_np.copy(),
    #         ask_qty_list=self._ask_qty_np.copy(),
    #     )
            
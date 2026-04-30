import orjson

from src.stores import AccountDataStoreHyper

class AccountHandlerHyper:
    def __init__(self, store: AccountDataStoreHyper) -> None:
        self.store: AccountDataStoreHyper = store
    
    def handle_message(self, msg: bytes):
        json_data = orjson.loads(msg)
        channel = json_data.get("channel", "")
        
        if channel == "clearinghouseState":
            self.store.update_perp_state(data=json_data)
        
        if channel == "spotState":
            self.store.update_spot_state(data=json_data)
        
        if channel == "userFills":
            if not json_data["data"].get("isSnapshot", False):
                self.store.update_fills(data=json_data)
        
        if channel == "userNonFundingLedgerUpdates":
            if not json_data["data"].get("isSnapshot", False):
                self.store.update_cash_flow(data=json_data)
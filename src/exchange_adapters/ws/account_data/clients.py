import os
import orjson
from picows import WSListener, WSFrame, WSMsgType
from dotenv import load_dotenv

load_dotenv()

HYPER_WALLET_ADDRESS = os.getenv("HYPER_WALLET_ADDRESS", "")

from src.logging import LOG_ENABLED, log_event


class WsAccountHyper(WSListener):

    def __init__(self, handler):
        self.handler = handler

    def on_ws_connected(self, transport):
        
        transport.send(WSMsgType.TEXT, orjson.dumps({
            "method": "subscribe",
            "subscription": {
                "type": "userFills",
                "user": HYPER_WALLET_ADDRESS
            }
        }))

        # transport.send(WSMsgType.TEXT, orjson.dumps({
        #     "method": "subscribe",
        #     "subscription": {
        #         "type": "orderUpdates",
        #         "user": self.address
        #     }
        # }))

        transport.send(WSMsgType.TEXT, orjson.dumps({
            "method": "subscribe",
            "subscription": {
                "type": "clearinghouseState",
                "user": HYPER_WALLET_ADDRESS
            }
        }))
        
        transport.send(WSMsgType.TEXT, orjson.dumps({
            "method": "subscribe",
            "subscription": {
                "type": "spotState",
                "user": HYPER_WALLET_ADDRESS
            }
        }))
        
        transport.send(WSMsgType.TEXT, orjson.dumps({
            "method": "subscribe",
            "subscription": {
                "type": "userNonFundingLedgerUpdates",
                "user": HYPER_WALLET_ADDRESS
            }
        }))
        

    def on_ws_frame(self, transport, frame: WSFrame):
        if frame.msg_type != WSMsgType.TEXT:
            LOG_ENABLED and log_event("ws_account_message", exchange="hyper", message=str(frame))
            return

        raw = frame.get_payload_as_bytes()
        
        self.handler(raw)
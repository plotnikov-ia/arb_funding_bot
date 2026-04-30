import struct
import orjson
from picows import WSListener, WSFrame, WSMsgType

from src.logging import LOG_ENABLED, log_event


HEADER_STRUCT = struct.Struct("<HHHH")
BBA_STRUCT = struct.Struct("<qqbbqqqq")
POW10 = {i: 10.0**i for i in range(-20, 5)}


class WsBBOClientHyper(WSListener):
    __slots__ = ("handler", "coin")

    def __init__(self, handler, coin: str):
        self.handler = handler
        self.coin = coin

    def on_ws_connected(self, transport):
        sub_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "bbo",
                "coin": self.coin
            }
        }

        transport.send(WSMsgType.TEXT, orjson.dumps(sub_msg))

    def on_ws_frame(self, transport, frame: WSFrame):
        if frame.msg_type == WSMsgType.TEXT:
            self.handler(frame.get_payload_as_bytes())
        else:
            LOG_ENABLED and log_event("ws_market_bbo_message", exchange="hyper", message=str(frame))

class WsOrderBookClientHyper(WSListener):
    __slots__ = ("handler",)

    def __init__(self, handler):
        self.handler = handler

    def on_ws_connected(self, transport):
        sub_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "l2Book",
                "coin": "ETH"
            }
        }
        transport.send(WSMsgType.TEXT, orjson.dumps(sub_msg))

    def on_ws_frame(self, transport, frame: WSFrame):
        if frame.msg_type == WSMsgType.TEXT:
            self.handler(frame.get_payload_as_bytes())
        else:
            LOG_ENABLED and log_event("ws_market_orderbook_message", exchange="hyper", message=str(frame))

class WsOrderBookClientBinance(WSListener):
    __slots__ = ("handler",)

    def __init__(self, handler):
        self.handler = handler

    def on_ws_connected(self, transport):
        pass

    def on_ws_frame(self, transport, frame: WSFrame):
        if frame.msg_type == WSMsgType.TEXT:
            self.handler(frame.get_payload_as_bytes())
        else:
            LOG_ENABLED and log_event("ws_market_orderbook_message", exchange="binance", message=str(frame))
            
class WsBBOClientBinance(WSListener):
    __slots__ = ("handler", "symbol")

    def __init__(self, handler, symbol="ethusdt"):
        self.handler = handler
        self.symbol = symbol

    def on_ws_connected(self, transport):
        # SUBSCRIBE
        transport.send(
            WSMsgType.TEXT,
            (
                '{"method":"SUBSCRIBE","params":["'
                + self.symbol
                + '@bestBidAsk"],"id":1}'
            ).encode()
        )

    def on_ws_frame(self, transport, frame: WSFrame):

        if frame.msg_type == WSMsgType.BINARY:
            buf = frame.get_payload_as_bytes()

            # --- SBE header ---
            _, template_id, _, _ = HEADER_STRUCT.unpack_from(buf, 0)

            offset = 8

            (
                event_time,
                book_update_id,
                price_exp,
                qty_exp,
                bid_price,
                bid_qty,
                ask_price,
                ask_qty,
            ) = BBA_STRUCT.unpack_from(buf, offset)

            price_scale = POW10[price_exp]
            qty_scale   = POW10[qty_exp]

            self.handler((
                event_time,
                book_update_id,
                bid_price * price_scale,
                bid_qty   * qty_scale,
                ask_price * price_scale,
                ask_qty   * qty_scale,
            ))

        elif frame.msg_type == WSMsgType.TEXT:
            # контрольные ответы Binance
            payload = frame.get_payload_as_bytes()
            
        else:
            LOG_ENABLED and log_event("ws_market_bbo_message", exchange="binance", message=str(frame))
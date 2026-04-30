import os
import time
import asyncio
from picows import ws_connect


from src.exchange_adapters.ws.market_data.clients import WsBBOClientBinance, WsBBOClientHyper, WsOrderBookClientBinance, WsOrderBookClientHyper
from src.logging import LOG_ENABLED, log_event


CONNECT_TIMEOUT = 5.0


async def watchdog(ws, last_msg_fn, name, timeout=2, grace=5):
    start = time.monotonic()
    
    while True:
        await asyncio.sleep(1)
        
        if time.monotonic() - start < grace:
            continue
        
        if time.monotonic() - last_msg_fn() > timeout:
            LOG_ENABLED and log_event("ws_market_disconnect_watchdog", exchange=name, last_msg_ago=time.monotonic() - last_msg_fn(), timeout=timeout)
            ws.disconnect()
            break
        
async def connect_bbo_hyper(collector, coin="ETH"):
    URL = "wss://api.hyperliquid.xyz/ws"

    while True:
        try:
            LOG_ENABLED and log_event("ws_market_bbo_connecting", exchange="hyper")

            ws, _ = await asyncio.wait_for(
                ws_connect(
                    lambda: WsBBOClientHyper(
                        collector.handle_bbo_hyper,
                        coin
                    ),
                    URL
                ),
                timeout=CONNECT_TIMEOUT
            )

            LOG_ENABLED and log_event("ws_market_bbo_connected", exchange="hyper")

            await asyncio.gather(
                ws.wait_disconnected(),
                watchdog(
                    ws,
                    lambda: collector.last_bbo_hyper_msg,
                    "hyperliquid",
                ),
            )

            LOG_ENABLED and log_event("ws_market_bbo_disconnected", exchange="hyper")

        except asyncio.TimeoutError:
            LOG_ENABLED and log_event("ws_market_bbo_timeout", exchange="hyper", timeout=CONNECT_TIMEOUT)

        except Exception as e:
            LOG_ENABLED and log_event("ws_market_bbo_error", exchange="hyper", error=str(e))

        await asyncio.sleep(0.5)
        
async def connect_orderbook_hyper(collector):
    URL = "wss://api.hyperliquid.xyz/ws"

    while True:
        try:
            LOG_ENABLED and log_event("ws_market_orderbook_connecting", exchange="hyper")

            ws, _ = await asyncio.wait_for(
                ws_connect(
                    lambda: WsOrderBookClientHyper(collector.handle_orderbook_hyper),
                    URL
                ),
                timeout=CONNECT_TIMEOUT
            )

            LOG_ENABLED and log_event("ws_market_orderbook_connected", exchange="hyper")

            await asyncio.gather(
                ws.wait_disconnected(),
                watchdog(
                    ws,
                    lambda: collector.last_orderbook_hyper_msg,
                    "orderbook_hyperliquid",
                ),
            )

            LOG_ENABLED and log_event("ws_market_orderbook_disconnected", exchange="hyper")

        except asyncio.TimeoutError:
            LOG_ENABLED and log_event("ws_market_orderbook_timeout", exchange="hyper", timeout=CONNECT_TIMEOUT)

        except Exception as e:
            LOG_ENABLED and log_event("ws_market_orderbook_error", exchange="hyper", error=str(e))

        await asyncio.sleep(0.5)

async def connect_orderbook_binance(collector):
    URL = "wss://fstream.binance.com/ws/ethusdc@depth5@100ms"

    while True:
        try:
            LOG_ENABLED and log_event("ws_market_orderbook_connecting", exchange="binance")

            ws, _ = await asyncio.wait_for(
                ws_connect(
                    lambda: WsOrderBookClientBinance(collector.handle_orderbook_binance),
                    URL
                ),
                timeout=CONNECT_TIMEOUT
            )

            LOG_ENABLED and log_event("ws_market_orderbook_connected", exchange="binance")

            await asyncio.gather(
                ws.wait_disconnected(),
                watchdog(
                    ws,
                    lambda: collector.last_orderbook_binance_msg,
                    "orderbook_binance",
                ),
            )

            LOG_ENABLED and log_event("ws_market_orderbook_disconnected", exchange="binance")

        except asyncio.TimeoutError:
            LOG_ENABLED and log_event("ws_market_orderbook_timeout", exchange="binance", timeout=CONNECT_TIMEOUT)

        except Exception as e:
            LOG_ENABLED and log_event("ws_market_orderbook_error", exchange="binance", error=str(e))

        await asyncio.sleep(0.5)
        
async def connect_bbo_binance(collector, secrets):

    headers = [
        ("X-MBX-APIKEY", secrets.get("BINANCE_ED25519_API_KEY"))
    ]

    while True:
        try:
            LOG_ENABLED and log_event("ws_market_bbo_connecting", exchange="binance")
            
            ws, _ = await asyncio.wait_for(
                ws_connect(
                    lambda: WsBBOClientBinance(collector.handle_bbo_binance),
                    "wss://stream-sbe.binance.com:9443/ws",
                    extra_headers=headers,
                ),
                timeout=CONNECT_TIMEOUT
            )
            
            LOG_ENABLED and log_event("ws_market_bbo_connected", exchange="binance")

            await asyncio.gather(
                ws.wait_disconnected(),
                watchdog(
                    ws,
                    lambda: collector.last_bbo_binance_msg,
                    "bbo_binance",
                ),
            )
            
            LOG_ENABLED and log_event("ws_market_bbo_disconnected", exchange="binance")

        except asyncio.TimeoutError:
            LOG_ENABLED and log_event("ws_market_bbo_timeout", exchange="binance", timeout=CONNECT_TIMEOUT)

        except Exception as e:
            LOG_ENABLED and log_event("ws_market_bbo_error", exchange="binance", error=str(e))

        await asyncio.sleep(0.5)

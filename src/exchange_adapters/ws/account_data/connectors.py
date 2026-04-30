import os
import asyncio
import time
from picows import ws_connect
from binance import AsyncClient, BinanceSocketManager

from src.logging import LOG_ENABLED, log_event
from src.exchange_adapters.ws.account_data.clients import WsAccountHyper

CONNECT_TIMEOUT = 5.0

async def watchdog(ws, last_msg_fn, name, timeout=5, grace=5):
    start = time.monotonic()

    while True:
        await asyncio.sleep(1)

        if time.monotonic() - start < grace:
            continue

        if time.monotonic() - last_msg_fn() > timeout:
            LOG_ENABLED and log_event("ws_account_disconnect_watchdog", exchange=name, last_msg_ago=time.monotonic() - last_msg_fn(), timeout=timeout)
            ws.disconnect()
            break


async def connect_account_hyper(collector):
    URL = "wss://api.hyperliquid.xyz/ws"

    while True:
        try:
            LOG_ENABLED and log_event("ws_account_connecting", exchange="hyper")

            ws, _ = await asyncio.wait_for(
                ws_connect(
                    lambda: WsAccountHyper(
                        collector.handle_message,
                    ),
                    URL
                ),
                timeout=CONNECT_TIMEOUT
            )

            LOG_ENABLED and log_event("ws_account_connected", exchange="hyper")

            await asyncio.gather(
                ws.wait_disconnected(),
            )

            LOG_ENABLED and log_event("ws_account_disconnected", exchange="hyper")

        except asyncio.TimeoutError:
            LOG_ENABLED and log_event("ws_account_connect_timeout", exchange="hyper", timeout=CONNECT_TIMEOUT)

        except Exception as e:
            LOG_ENABLED and log_event("ws_account_error", exchange="hyper", error=str(e))

        await asyncio.sleep(0.5)
        

async def connect_account_binance(collector, connected_event, secrets):
    client = await AsyncClient.create(secrets.get("BINANCE_HMAC_API_KEY"), secrets.get("BINANCE_HMAC_API_SECRET"))
    bm = BinanceSocketManager(client)

    while True:
        try:
            socket = bm.futures_user_socket()

            async with socket as stream:
                LOG_ENABLED and log_event("ws_account_connected", exchange="binance")

                # 🔥 вот ключевая строка
                connected_event.set()

                while True:
                    msg = await stream.recv()
                    collector.handle_message(msg)

        except Exception as e:
            connected_event.clear()  # если отвалились — снова блокируем
            LOG_ENABLED and log_event("ws_account_error", exchange="binance", error=str(e))
            LOG_ENABLED and log_event("ws_account_disconnected", exchange="binance")

            await asyncio.sleep(1)
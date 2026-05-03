import os
import time
import asyncio
import httpx
import textwrap
from dotenv import load_dotenv


from src.logging import LOG_ENABLED, log_event

load_dotenv()

ALERT_URL = os.getenv("ALERT_URL", "")
ALERT_INTERVAL_SECONDS = float(os.getenv("ALERT_INTERVAL_SECONDS"))


def send_alert(alert_type: str, json_data: dict):
    LOG_ENABLED and log_event("alert_service", action="send tg alert")
    json_data["alert_type"] = alert_type
    asyncio.create_task(_send(json_data))

async def _send(json_data: dict):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(ALERT_URL, json=json_data)

        LOG_ENABLED and log_event("alert_service", action="sent tg alert")

    except Exception as e:
        LOG_ENABLED and log_event("alert_service", action="alert failed", error=str(e))
        
        
class AlertTradingService:
    def __init__(self) -> None:
        self.last_alert_time = 0
        
    def update(self, state_binance, state_hyper, state_blockchain):
        now = time.time()

        if now - self.last_alert_time >= ALERT_INTERVAL_SECONDS:

            message = textwrap.dedent(f"""
                🟡 --- Binance ---
                margin ratio: {state_binance.margin_ratio:.2f}
                equity: {state_binance.equity:.2f}
                quote_position: {state_binance.quote_position:.2f}
                base_position: {state_binance.base_position:.2f}
                quote_position_spot: {state_binance.quote_position_spot:.2f}
                locked_quote_position_spot: {state_binance.locked_quote_position_spot:.2f}

                🟢 --- Hyperliquid ---
                margin ratio: {state_hyper.margin_ratio:.2f}
                equity: {state_hyper.equity:.2f}
                quote_position: {state_hyper.quote_position:.2f}
                base_position: {state_hyper.base_position:.2f}

                🔵 --- Blockchain ---
                amount usdc: {state_blockchain.amount_usdc:.2f}
            """)
            
            json_data = {
                "str_message": message
            }
            
            send_alert(alert_type="info", json_data=json_data)
            
            self.last_alert_time = now
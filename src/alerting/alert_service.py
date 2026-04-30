import os
import time
import asyncio
import httpx
from dotenv import load_dotenv


from src.logging import LOG_ENABLED, log_event

load_dotenv()

ALERT_URL = os.getenv("ALERT_URL", "")

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
        self.alert_interval = 30 * 60  # 30 минут в секундах
        
    def update(self, state_binance, state_hyper):
        now = time.time()

        if now - self.last_alert_time >= self.alert_interval:
            send_alert(alert_type="info", json_data=state_binance.to_dict())
            send_alert(alert_type="info", json_data=state_hyper.to_dict())
            
            self.last_alert_time = now
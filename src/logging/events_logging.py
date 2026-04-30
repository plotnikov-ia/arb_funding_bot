import logging

logger = logging.getLogger("strategy")

def log_event(event: str, **fields):
    logger.info(
        event,
        extra={
            "data": {
                "event": event,
                **fields,
            }
        },
    )

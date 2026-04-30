import os
import time
import logging
import json
from logging.handlers import QueueHandler, QueueListener
from queue import SimpleQueue
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

LOG_ENABLED = os.getenv("LOG_ENABLED", "False").lower() == "true"
LOGGING_TYPE = os.getenv("LOGGING_TYPE", "file").lower()
LOG_FILE_PATH = "logging.jsonl"

os.makedirs(os.path.dirname(LOG_FILE_PATH) or ".", exist_ok=True)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": int(time.time() * 1000),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        if hasattr(record, "data"):
            base.update(record.data)

        return json.dumps(base, separators=(",", ":"))

def setup_logging():
    logger = logging.getLogger("strategy")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    if not LOG_ENABLED:
        logger.addHandler(logging.NullHandler())
        return None

    if LOGGING_TYPE == "console":
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        ))
        logger.addHandler(console_handler)
        return None

    elif LOGGING_TYPE == "file":
        os.makedirs(os.path.dirname(LOG_FILE_PATH) or ".", exist_ok=True)

        queue = SimpleQueue()
        queue_handler = QueueHandler(queue)

        file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
        file_handler.setFormatter(JsonFormatter())

        listener = QueueListener(queue, file_handler)
        listener.start()

        logger.addHandler(queue_handler)
        return listener

    else:
        raise ValueError(f"Unknown LOGGING_TYPE: {LOGGING_TYPE}")
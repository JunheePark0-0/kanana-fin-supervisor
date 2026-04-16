"""
Kanana_Agent 루트 `src.core.kanana_pipeline` 전용 로거.
`config.Config`에 ENABLE_LOCAL_LOGGING, LOG_DIR이 정의되어 있어야 합니다.
"""

import logging
from datetime import datetime
from pathlib import Path

from config import Config


class RealTimeFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()


def setup_logger(name: str = "Kanana_Orchestrator"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if getattr(Config, "ENABLE_LOCAL_LOGGING", False):
        log_dir = Path(getattr(Config, "LOG_DIR", "./logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = log_dir / f"orchestrator_{now_str}.log"
        file_handler = RealTimeFileHandler(log_filename, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        logger.addHandler(stream)

    globals()["logger"] = logger
    return logger


logger = setup_logger()


def log_conversation(user_message: str, ai_response: str, session_id: str = None):
    logger.info(f"[CONVERSATION] Session: {session_id}")
    logger.info(f"[USER] {user_message}")
    logger.info(f"[AI] {ai_response}")


def log_error(error: Exception, context: str = ""):
    logger.error(f"[ERROR] {context}: {str(error)}", exc_info=True)


def log_agent_action(action: str, details: dict = None):
    log_msg = f"[AGENT] {action}"
    if details:
        log_msg += f" - Details: {details}"
    logger.info(log_msg)

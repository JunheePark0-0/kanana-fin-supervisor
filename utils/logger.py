"""
Kanana_Agent 루트 공통 로거.
"""

import logging
from pathlib import Path

from utils.log_paths import (
    DEFAULT_AGENT_LOG_FILENAME,
    ORCHESTRATOR_FINAL_RESPONSE_FILENAME,
    get_agent_log_run_dir,
)
from config import BaseConfig as Config

class RealTimeFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

def setup_logger(
    name: str = "Kanana_Orchestrator",
    *,
    agent_log_name: str = "orchestrator",
    log_run_dir: Path | str | None = None,
    new_folder: bool = False,
):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if getattr(Config, "ENABLE_LOCAL_LOGGING", False):
        run_dir = Path(log_run_dir) if log_run_dir else get_agent_log_run_dir(agent_log_name, new_folder = new_folder)
        log_filename = run_dir / DEFAULT_AGENT_LOG_FILENAME
        file_handler = RealTimeFileHandler(log_filename, encoding = "utf-8")
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


def save_orchestrator_final_response(content: str) -> Path | None:
    """오케스트레이터 run 디렉터리에 final_response.rmd를 저장합니다."""
    if not getattr(Config, "ENABLE_LOCAL_LOGGING", False):
        return None
    run_dir = get_agent_log_run_dir("orchestrator")
    output_path = run_dir / ORCHESTRATOR_FINAL_RESPONSE_FILENAME
    output_path.write_text(content, encoding = "utf-8")
    return output_path

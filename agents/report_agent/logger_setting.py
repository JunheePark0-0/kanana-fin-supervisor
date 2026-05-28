from __future__ import annotations

import logging
from pathlib import Path

from config import AGENT_LOG_NAME, ENABLE_LOCAL_LOGGING
from utils.log_paths import DEFAULT_AGENT_LOG_FILENAME, get_agent_log_run_dir

_configured = False


def configure_report_logging(*, new_folder: bool = False) -> Path | None:
    """report_agent 실행 시 logs/report_agent/{timestamp}/agent.log 로 기록합니다."""
    global _configured
    if not ENABLE_LOCAL_LOGGING:
        return None

    run_dir = get_agent_log_run_dir(AGENT_LOG_NAME, new_folder=new_folder)
    log_file = run_dir / DEFAULT_AGENT_LOG_FILENAME

    root_logger = logging.getLogger()
    if new_folder or not _configured:
        for handler in list(root_logger.handlers):
            if getattr(handler, "_report_agent_log", False):
                root_logger.removeHandler(handler)
                handler.close()

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        file_handler._report_agent_log = True  # type: ignore[attr-defined]
        root_logger.addHandler(file_handler)
        _configured = True

    return run_dir

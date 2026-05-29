import logging
import os

from trend_config import TrendConfig
from utils.log_paths import DEFAULT_AGENT_LOG_FILENAME, get_agent_log_run_dir

_LOG_FILE: str | None = None


def init_trend_file_logging(*, new_folder: bool = False) -> str | None:
    """Trend Agent 실행 시에만 타임스탬프 로그 파일을 생성"""
    global _LOG_FILE
    if not TrendConfig.ENABLE_LOCAL_LOGGING:
        return None
    run_dir = get_agent_log_run_dir(TrendConfig.AGENT_LOG_NAME, new_folder=new_folder)
    _LOG_FILE = str(run_dir / DEFAULT_AGENT_LOG_FILENAME)
    return _LOG_FILE


def get_log_file() -> str | None:
    return _LOG_FILE


def _attach_file_handler(logger: logging.Logger) -> None:
    log_file = get_log_file()
    if not log_file:
        return
    for handler in logger.handlers:
        if getattr(handler, "_trend_agent_log", False):
            return
    formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler._trend_agent_log = True  # type: ignore[attr-defined]
    logger.addHandler(file_handler)


def get_logger(name="KananaAgent") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        _attach_file_handler(logger)
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    _attach_file_handler(logger)
    return logger


if __name__ == "__main__":
    init_trend_file_logging(new_folder=True)
    test_log = get_logger("TestLogger")

    print("--- 로그 테스트 시작 ---")
    test_log.info("INFO 레벨 로그 정상 작동")
    test_log.warning("WARNING 레벨 로그 정상 작동")
    test_log.error("ERROR 레벨 로그 정상 작동")
    print("--- 로그 테스트 종료 ---")

    log_path = get_log_file()
    if log_path and os.path.exists(log_path):
        print(f"로그 파일 생성 확인: {log_path}")
    elif TrendConfig.ENABLE_LOCAL_LOGGING:
        print("로그 파일 생성 실패")
    else:
        print("로컬 로깅 비활성화 — 콘솔만 사용")

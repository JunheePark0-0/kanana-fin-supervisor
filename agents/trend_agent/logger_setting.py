import logging
import os

from trend_config import TrendConfig
from utils.log_paths import DEFAULT_AGENT_LOG_FILENAME, get_agent_log_run_dir

_LOG_FILE: str | None = None


def get_log_file() -> str | None:
    """로컬 로깅 활성화 시 타임스탬프 기반 로그 파일 경로 반환 (싱글턴)."""
    global _LOG_FILE
    if not TrendConfig.ENABLE_LOCAL_LOGGING:
        return None
    if _LOG_FILE is None:
        run_dir = get_agent_log_run_dir(TrendConfig.AGENT_LOG_NAME)
        _LOG_FILE = str(run_dir / DEFAULT_AGENT_LOG_FILENAME)
    return _LOG_FILE


def get_logger(name="KananaAgent") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    log_file = get_log_file()
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


if __name__ == "__main__":
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

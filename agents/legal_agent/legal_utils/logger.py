import logging
from pathlib import Path

from legal_config import LegalConfig
from utils.log_paths import DEFAULT_AGENT_LOG_FILENAME, create_agent_log_run_dir


class RealTimeFileHandler(logging.FileHandler):
    """실시간으로 로그가 기록되도록 하는 핸들러"""
    def emit(self, record):
        super().emit(record)
        self.flush()

def setup_logger(
    name: str = "legal_agent",
    *,
    log_run_dir: Path | str | None = None,
):
    """로거 설정"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    
    if logger.handlers:
        logger.handlers.clear()
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if LegalConfig.ENABLE_LOCAL_LOGGING:
        run_dir = Path(log_run_dir) if log_run_dir else create_agent_log_run_dir(LegalConfig.AGENT_LOG_NAME)
        log_filename = run_dir / DEFAULT_AGENT_LOG_FILENAME
        file_handler = RealTimeFileHandler(log_filename, encoding = 'utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        logger.addHandler(stream)
    
    globals()["logger"] = logger
    return logger


def _console_logger(name: str = "legal_agent") -> logging.Logger:
    """import 시점에는 콘솔만 사용하고, 파일 로그는 에이전트 실행 시 setup_logger로 설정"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        logger.addHandler(stream)
    return logger


logger = _console_logger()

def log_conversation(user_message: str, ai_response: str, session_id: str = None):
    """대화 로그 기록"""
    logger.info(f"[CONVERSATION] Session: {session_id}")
    logger.info(f"[USER] {user_message}")
    logger.info(f"[AI] {ai_response}")

def log_error(error: Exception, context: str = ""):
    """에러 로그 기록"""
    logger.error(f"[ERROR] {context}: {str(error)}", exc_info = True)

def log_agent_action(action: str, details: dict = None):
    """Agent 액션 로그 기록"""
    log_msg = f"[AGENT] {action}"
    if details:
        log_msg += f" - Details: {details}"
    logger.info(log_msg)

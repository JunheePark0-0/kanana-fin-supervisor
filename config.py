from pathlib import Path
import os

def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class BaseConfig:
    """Agent 전역 설정 (모든 Agent에 공통적으로 사용되는 설정)"""

    PROJECT_ROOT = Path(__file__).resolve().parent

    # --------------------------------------------
    # .env 설정
    # --------------------------------------------
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY", "")
    USER_EMAIL = os.getenv("USER_EMAIL", "")

    KANANA_MAX_NEW_TOKENS = int(os.getenv("KANANA_MAX_NEW_TOKENS", "1024"))
    ENABLE_LOCAL_LOGGING = _env_bool("ENABLE_LOCAL_LOGGING", "true")

    # --------------------------------------------
    # 모델 설정
    # --------------------------------------------
    KANANA_MODEL_NAME = "kakaocorp/kanana-1.5-2.1b-instruct-2505"
    BGE_M3_MODEL_NAME = "BAAI/bge-m3"
    
    KANANA_SUMMARY_MAX_NEW_TOKENS = int(os.getenv("KANANA_SUMMARY_MAX_NEW_TOKENS", "4096"))
    # --------------------------------------------
    # 경로 설정
    # --------------------------------------------
    DATA_DIR = "./data"
    LOG_DIR = "./logs"
    KANANA_MODEL_PATH = "./models/Kanana"
    BGE_M3_MODEL_PATH = "./models/bge-m3"

    @classmethod
    def resolve_path(cls, path_value: str) -> str:
        """프로젝트 루트 기준 절대 경로로 변환"""
        path = Path(path_value)
        if path.is_absolute():
            return str(path)
        return str((cls.PROJECT_ROOT / path).resolve())

    @classmethod
    def resolve_data_path(cls, *parts: str) -> str:
        """공통 data 루트 기준 절대 경로로 변환"""
        path = Path(cls.DATA_DIR)
        for part in parts:
            path /= part
        return cls.resolve_path(str(path))

    @classmethod
    def agent_log_root(cls, agent_name: str) -> str:
        """logs/{agent_name} 절대 경로"""
        return cls.resolve_path(str(Path(cls.LOG_DIR) / agent_name))

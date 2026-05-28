import os

from utils.config_bootstrap import bootstrap_config

_CTX = bootstrap_config(__file__)
BaseConfig = _CTX.base_config

class Config:
    """Agent 전역 설정"""
    # ============================================================================
    # 로깅 설정 
    # ============================================================================
    ENABLE_LOCAL_LOGGING = BaseConfig.ENABLE_LOCAL_LOGGING
    AGENT_LOG_NAME = "stock_agent"

    # ============================================================================
    # 모델 설정
    # ============================================================================
    KANANA_MODEL_NAME = BaseConfig.KANANA_MODEL_NAME
    KANANA_MAX_NEW_TOKENS = BaseConfig.KANANA_MAX_NEW_TOKENS * 2 # stock agent는 더 많은 토큰 필요
    KANANA_SUMMARY_MAX_NEW_TOKENS = 2048

    # ============================================================================
    # API 키 / 외부 식별 (루트 .env)
    # ============================================================================
    USER_EMAIL = os.getenv("USER_EMAIL", "")

    # ============================================================================
    # 경로 설정
    # ============================================================================
    KANANA_MODEL_PATH = BaseConfig.resolve_path(BaseConfig.KANANA_MODEL_PATH)

    NEWS_FILE_PATH = BaseConfig.resolve_data_path("stock_data", "News")
    NEWS_DB_PATH = BaseConfig.resolve_data_path("stock_data", "database", "News")
    SEC_FILE_PATH = BaseConfig.resolve_data_path("stock_data", "SEC")
    SEC_DB_PATH = BaseConfig.resolve_data_path("stock_data", "database", "SEC")

    MAX_NEWS_COUNT = 20 # 수집할 뉴스 최대 개수
    MAX_SEC_DAYS = 14 # 수집할 SEC 일수

    # ============================================================================
    # 티커 매핑
    # ============================================================================
    TICKER_MAP = {
        "NVDA": "NVIDIA",
        "MSFT": "Microsoft",
        "TSLA": "Tesla",
        "LLY": "Eli Lilly",
        "BAC": "Bank of America",
        "KO": "Coca-Cola",
        "META": "Meta",
        "AAPL": "Apple",
        "GOOG": "Google",
        "AMZN": "Amazon",
    }

    @classmethod
    def get_config_summary(cls):
        """현재 설정 요약"""
        return {
            "로컬 로깅": "활성화" if cls.ENABLE_LOCAL_LOGGING else "비활성화",
            "모델": cls.KANANA_MODEL_NAME,
        }

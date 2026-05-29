import os

from utils.config_bootstrap import bootstrap_config

_CTX = bootstrap_config(__file__)
BaseConfig = _CTX.base_config


class NewsConfig(BaseConfig):
    """News Agent 전역 설정 (공통값은 BaseConfig에서 상속)"""

    AGENT_LOG_NAME = "news_agent"
    QDRANT_PATH = BaseConfig.resolve_data_path("news_data")
    COLLECTION_NAME = "kr_news"
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    MODEL_DIR = BaseConfig.resolve_path(BaseConfig.KANANA_MODEL_PATH)
    EMBEDDING_MODEL_DIR = BaseConfig.resolve_path(BaseConfig.BGE_M3_MODEL_PATH)
    INGEST_OUTPUT_DIR = BaseConfig.resolve_data_path("news_data", "ingest_output")
    SKIP_QDRANT = False

import os
from pathlib import Path

from utils.config_bootstrap import bootstrap_config

_CTX = bootstrap_config(__file__)
BaseConfig = _CTX.base_config

AGENT_LOG_NAME = "news_agent"
# BaseConfig 따름; 에이전트별 override 가능 (예: ENABLE_LOCAL_LOGGING = False)
ENABLE_LOCAL_LOGGING = BaseConfig.ENABLE_LOCAL_LOGGING
QDRANT_PATH = BaseConfig.resolve_data_path("news_data")
COLLECTION_NAME = "kr_news"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
MODEL_DIR = BaseConfig.resolve_path(BaseConfig.KANANA_MODEL_PATH)
EMBEDDING_MODEL_DIR = BaseConfig.resolve_path(BaseConfig.BGE_M3_MODEL_PATH)
INGEST_OUTPUT_DIR = BaseConfig.resolve_data_path("news_data", "ingest_output")

# 적재/다른 프로세스가 Qdrant DB를 사용 중일 때 True로 두면 Qdrant에 연결하지 않음
SKIP_QDRANT = False

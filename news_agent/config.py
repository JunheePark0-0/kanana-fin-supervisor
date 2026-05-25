import os
from pathlib import Path

from utils.config_bootstrap import bootstrap_config

_CTX = bootstrap_config(__file__, dotenv_mode="agent")
BaseConfig = _CTX.base_config


LOG_DIR = BaseConfig.resolve_path(BaseConfig.LOG_DIR)
QDRANT_PATH = BaseConfig.resolve_path(
    os.getenv("QDRANT_PATH", BaseConfig.resolve_data_path("news_data", "qdrant_db"))
)
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "kr_news")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
MODEL_DIR = BaseConfig.resolve_path(BaseConfig.KANANA_MODEL_PATH)
EMBEDDING_MODEL_DIR = BaseConfig.resolve_path(BaseConfig.BGE_M3_MODEL_PATH)
INGEST_OUTPUT_DIR = BaseConfig.resolve_data_path("news_data", "ingest_output")
SEARCH_LOG_PATH = str((Path(LOG_DIR) / "news_search_log.jsonl").resolve())
QA_LOG_PATH = str((Path(LOG_DIR) / "news_qa_log.jsonl").resolve())

# 적재/다른 프로세스가 Qdrant DB를 사용 중일 때 True로 두면 Qdrant에 연결하지 않음
SKIP_QDRANT = os.getenv("SKIP_QDRANT", "0").lower() in ("1", "true", "yes")

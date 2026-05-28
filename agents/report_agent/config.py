from __future__ import annotations

import os
from dataclasses import dataclass

from utils.config_bootstrap import bootstrap_config

_CTX = bootstrap_config(__file__)
BaseConfig = _CTX.base_config

AGENT_LOG_NAME = "report_agent"
ENABLE_LOCAL_LOGGING = BaseConfig.ENABLE_LOCAL_LOGGING


@dataclass(frozen=True)
class Settings:
    upstage_api_key: str | None = os.getenv("UPSTAGE_API_KEY") or None
    huggingfacehub_api_token: str | None = os.getenv("HUGGINGFACEHUB_API_TOKEN") or None
    kanana_model_id: str = BaseConfig.KANANA_MODEL_NAME
    kanana_model_path: str = BaseConfig.resolve_path(BaseConfig.KANANA_MODEL_PATH)
    runtime_dir: str = BaseConfig.resolve_data_path("report_data", "runtime_files")


settings = Settings()

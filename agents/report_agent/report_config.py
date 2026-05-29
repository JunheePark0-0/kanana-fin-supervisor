from __future__ import annotations
import os
from utils.config_bootstrap import bootstrap_config

_CTX = bootstrap_config(__file__)
BaseConfig = _CTX.base_config


class ReportConfig(BaseConfig):
    """Report Agent 전역 설정 (공통값은 BaseConfig에서 상속)"""

    AGENT_LOG_NAME = "report_agent"
    upstage_api_key: str | None = os.getenv("UPSTAGE_API_KEY") or None
    huggingfacehub_api_token: str | None = os.getenv("HUGGINGFACEHUB_API_TOKEN") or None
    kanana_model_id: str = BaseConfig.KANANA_MODEL_NAME
    kanana_model_path: str = BaseConfig.resolve_path(BaseConfig.KANANA_MODEL_PATH)
    runtime_dir: str = BaseConfig.resolve_data_path("report_data", "runtime_files")


settings = ReportConfig

import os
import warnings

import torch

from utils.config_bootstrap import bootstrap_config

_CTX = bootstrap_config(__file__)
BaseConfig = _CTX.base_config


class TrendConfig(BaseConfig):
    """Trend Agent 전역 설정 (공통값은 BaseConfig에서 상속)"""

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    AGENT_LOG_NAME = "trend_agent"

    DATA_DIR = BaseConfig.resolve_data_path("trend_data")
    DATA_PATH = os.path.join(DATA_DIR, "kcif_articles_accumulate.csv")
    DB_PATH = os.path.join(DATA_DIR, "chroma_db_bge")

    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

    # 모델 Kanana 설정 - 로컬 모델 파일 경로
    KANANA_MODEL_PATH = BaseConfig.resolve_path(BaseConfig.KANANA_MODEL_PATH)
    LLM_MODEL = KANANA_MODEL_PATH

    # 디바이스 설정
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    MODEL_DTYPE = torch.float16 if torch.cuda.is_available() else torch.float32

    # 임베딩
    EMBED_MODEL_NAME = BaseConfig.resolve_path(BaseConfig.BGE_M3_MODEL_PATH)
    EMBED_MODEL_KWARGS = {"device": DEVICE, "local_files_only": True}
    EMBED_ENCODE_KWARGS = {"normalize_embeddings": True}

    @classmethod
    def ensure_dirs(cls):
        """필요한 디렉토리 자동 생성"""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.agent_log_root(cls.AGENT_LOG_NAME), exist_ok=True)


if not TrendConfig.TAVILY_API_KEY:
    warnings.warn(
        "TAVILY_API_KEY가 설정되지 않았습니다. 웹 검색 기능이 비활성화됩니다.",
        stacklevel=2,
    )

TrendConfig.ensure_dirs()

if __name__ == "__main__":
    print(f"BASE_DIR  : {TrendConfig.BASE_DIR}")
    print(f"DATA_DIR  : {TrendConfig.DATA_DIR}")
    print(f"LOG_ROOT  : {TrendConfig.agent_log_root(TrendConfig.AGENT_LOG_NAME)}")
    print(f"LLM_MODEL : {TrendConfig.LLM_MODEL}")
    print(f"DEVICE    : {TrendConfig.DEVICE}")
    print(f"TAVILY_API_KEY 로드: {'Yes' if TrendConfig.TAVILY_API_KEY else 'No'}")

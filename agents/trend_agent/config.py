import os
import torch

from utils.config_bootstrap import bootstrap_config
from utils.log_paths import agent_log_root

_CTX = bootstrap_config(__file__)
BaseConfig = _CTX.base_config

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    AGENT_LOG_NAME = "trend_agent"
    ENABLE_LOCAL_LOGGING = BaseConfig.ENABLE_LOCAL_LOGGING

    # 데이터 경로
    DATA_DIR  = BaseConfig.resolve_data_path("trend_data")
    DATA_PATH = os.path.join(DATA_DIR, "kcif_articles_accumulate.csv")
    DB_PATH   = os.path.join(DATA_DIR, "chroma_db_bge")

    # API 키 (루트 .env)
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    if not TAVILY_API_KEY:
        import warnings
        warnings.warn("TAVILY_API_KEY가 설정되지 않았습니다. 웹 검색 기능이 비활성화됩니다.", stacklevel=2)

    # 모델 Kanana 설정 - 로컬 모델 파일 경로
    KANANA_MODEL_PATH = BaseConfig.resolve_path(BaseConfig.KANANA_MODEL_PATH)
    LLM_MODEL = KANANA_MODEL_PATH

    # 디바이스 설정
    DEVICE     = "cuda" if torch.cuda.is_available() else "cpu"
    MODEL_DTYPE = torch.float16 if torch.cuda.is_available() else torch.float32

    # 임베딩
    EMBED_MODEL_NAME   = BaseConfig.resolve_path(BaseConfig.BGE_M3_MODEL_PATH)
    EMBED_MODEL_KWARGS = {'device': DEVICE, 'local_files_only': True}
    EMBED_ENCODE_KWARGS = {'normalize_embeddings': True}

    @classmethod
    def ensure_dirs(cls):
        """필요한 디렉토리 자동 생성"""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(agent_log_root(cls.AGENT_LOG_NAME), exist_ok=True)

# 디렉토리 자동 생성
Config.ensure_dirs()

# 정상 작동 확인
if __name__ == "__main__":
    print(f"BASE_DIR  : {Config.BASE_DIR}")
    print(f"DATA_DIR  : {Config.DATA_DIR}")
    print(f"LOG_ROOT  : {agent_log_root(Config.AGENT_LOG_NAME)}")
    print(f"LLM_MODEL : {Config.LLM_MODEL}")
    print(f"DEVICE    : {Config.DEVICE}")
    print(f"TAVILY_API_KEY 로드: {'Yes' if Config.TAVILY_API_KEY else 'No'}")

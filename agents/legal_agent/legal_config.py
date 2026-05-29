"""
Legal Agent 설정 파일
환경변수나 직접 설정으로 Agent의 동작을 제어합니다.

"""

import os

from utils.config_bootstrap import bootstrap_config

_CTX = bootstrap_config(__file__)
BaseConfig = _CTX.base_config

class LegalConfig(BaseConfig):
    """Agent 전역 설정 (공통값은 BaseConfig에서 상속)"""
    
    # ============================================================================
    # 로깅 설정
    # ============================================================================
    AGENT_LOG_NAME = "legal_agent"

    # ============================================================================
    # 모델 설정
    # ============================================================================
    # Kanana 모델
    KANANA_MAX_NEW_TOKENS = BaseConfig.KANANA_MAX_NEW_TOKENS

    # ============================================================================
    # 경로 설정
    # ============================================================================
    KANANA_MODEL_PATH = BaseConfig.resolve_path(BaseConfig.KANANA_MODEL_PATH)
    LEGAL_DATA_DIR = BaseConfig.resolve_data_path("legal_data")
    LAWS_ROOT_DIR = os.path.join(LEGAL_DATA_DIR, "Laws")
    LAWS_RAW_DIR = os.path.join(LAWS_ROOT_DIR, "Raw")
    LAWS_PARSED_DIR = os.path.join(LAWS_ROOT_DIR, "Parsed")
    LAWS_PROCESSED_DIR = os.path.join(LAWS_ROOT_DIR, "Processed")
    LAW_DB_PATH = os.path.join(LEGAL_DATA_DIR, "LawDB")
    FILTERED_DB_PATH = os.path.join(LEGAL_DATA_DIR, "FilteredDB")

    @classmethod
    def get_config_summary(cls):
        """현재 설정 요약"""
        return {
            "로컬 로깅": "활성화" if cls.ENABLE_LOCAL_LOGGING else "비활성화",
            "모델": cls.KANANA_MODEL_NAME,
        }



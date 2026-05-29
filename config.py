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

    KANANA_MAX_NEW_TOKENS = int(os.getenv("KANANA_MAX_NEW_TOKENS", "512"))
    ENABLE_LOCAL_LOGGING = _env_bool("ENABLE_LOCAL_LOGGING", "true")

    # --------------------------------------------
    # 모델 설정
    # --------------------------------------------
    KANANA_MODEL_NAME = "kakaocorp/kanana-1.5-2.1b-instruct-2505"
    BGE_M3_MODEL_NAME = "BAAI/bge-m3"
    
    KANANA_SUMMARY_MAX_NEW_TOKENS = int(os.getenv("KANANA_SUMMARY_MAX_NEW_TOKENS", "2048"))
    # --------------------------------------------
    # 경로 설정
    # --------------------------------------------
    DATA_DIR = "./data"
    LOG_DIR = "./logs"
    KANANA_MODEL_PATH = "./models/Kanana"
    BGE_M3_MODEL_PATH = "./models/bge-m3"

    # --------------------------------------------
    # Stock Agent 관련 티커 설정
    # --------------------------------------------
    TICKER_MAP = {
        # NVIDIA
        "엔비디아": "NVDA",
        "NVIDIA": "NVDA",
        "NVDA": "NVDA",

        # Microsoft
        "마이크로소프트": "MSFT",
        "Microsoft": "MSFT",
        "MSFT": "MSFT",

        # Tesla
        "테슬라": "TSLA",
        "Tesla": "TSLA",
        "TSLA": "TSLA",

        # Eli Lilly
        "일라이 릴리": "LLY",
        "Eli Lilly": "LLY",
        "LLY": "LLY",

        # Bank of America
        "뱅크 오브 아메리카": "BAC",
        "Bank of America": "BAC",
        "BAC": "BAC",

        # Coca-Cola
        "코카콜라": "KO",
        "코카-콜라": "KO",
        "Coca-Cola": "KO",
        "KO": "KO",

        # Meta
        "메타": "META",
        "Meta": "META",
        "META": "META",

        # Apple
        "애플": "AAPL",
        "Apple": "AAPL",
        "AAPL": "AAPL",

        # Google
        "구글": "GOOG",
        "Google": "GOOG",
        "알파벳": "GOOG",
        "Alphabet": "GOOG",
        "GOOG": "GOOG",
        "GOOGL": "GOOG",

        # Amazon
        "아마존": "AMZN",
        "Amazon": "AMZN",
        "AMZN": "AMZN",

        # Intel
        "인텔": "INTC",
        "Intel": "INTC",
        "INTC": "INTC",

        # Qualcomm
        "퀄컴": "QCOM",
        "Qualcomm": "QCOM",
        "QCOM": "QCOM",

        # Oracle
        "오라클": "ORCL",
        "Oracle": "ORCL",
        "ORCL": "ORCL",

        # Netflix
        "넷플릭스": "NFLX",
        "Netflix": "NFLX",
        "NFLX": "NFLX",

        # Spotify
        "스포티파이": "SPOT",
        "Spotify": "SPOT",
        "SPOT": "SPOT",

        # Wells Fargo
        "웰스파고": "WFC",
        "Wells Fargo": "WFC",
        "WFC": "WFC",

        # BlackRock
        "블랙록": "BLK",
        "BlackRock": "BLK",
        "BLK": "BLK",

        # Visa
        "비자": "V",
        "Visa": "V",
        "V": "V",

        # Mastercard
        "마스터카드": "MA",
        "Mastercard": "MA",
        "MA": "MA",

        # Walmart
        "월마트": "WMT",
        "Walmart": "WMT",
        "WMT": "WMT",

        # Target
        "타겟": "TGT",
        "Target": "TGT",
        "TGT": "TGT",

        # Costco
        "코스트코": "COST",
        "Costco": "COST",
        "COST": "COST",

        # Nike
        "나이키": "NKE",
        "Nike": "NKE",
        "NKE": "NKE",

        # Starbucks
        "스타벅스": "SBUX",
        "Starbucks": "SBUX",
        "SBUX": "SBUX",

        # McDonald's
        "맥도날드": "MCD",
        "McDonald's": "MCD",
        "MCD": "MCD",
    }

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

import torch
import sys
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import BaseConfig

_DEFAULT_BGE_MODEL_DIR = str((_PROJECT_ROOT / BaseConfig.BGE_M3_MODEL_PATH).resolve())


def get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def get_embeddings(
    model_name_or_path: str = _DEFAULT_BGE_MODEL_DIR,
    local_files_only: bool = False,
) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=model_name_or_path,
        model_kwargs={"device": get_device(), "local_files_only": local_files_only},
        encode_kwargs={"normalize_embeddings": True},
    )

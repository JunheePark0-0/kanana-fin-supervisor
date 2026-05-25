import torch
import sys
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoModelForCausalLM, AutoTokenizer

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config_base import BaseConfig

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


def load_kanana_model(model_dir: str):
    tokenizer = AutoTokenizer.from_pretrained(
        model_dir, local_files_only=True, use_fast=True
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    if torch.cuda.is_available():
        major, _ = torch.cuda.get_device_capability()
        torch_dtype = torch.bfloat16 if major >= 8 else torch.float16
        device_map = "auto"
    else:
        torch_dtype = torch.float32
        device_map = None

    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        local_files_only=True,
        torch_dtype=torch_dtype,
        device_map=device_map,
        low_cpu_mem_usage=True,
    ).eval()
    return tokenizer, model


def get_kanana_response(model, tokenizer, messages, max_tokens=512, temp=0.3):
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    ).to(model.device)

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=temp,
            repetition_penalty=1.2,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    input_len = inputs.input_ids.shape[1]
    return tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()

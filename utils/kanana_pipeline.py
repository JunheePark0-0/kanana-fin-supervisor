# Kanana 공통 로더 + inference helpers (오케스트레이터·모든 에이전트 공유)

from __future__ import annotations

import json
import re
import time
from typing import Any, Callable

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline as hf_pipeline

from config import BaseConfig as Config
from utils.logger import log_agent_action

KANANA_MAX_NEW_TOKENS = Config.KANANA_MAX_NEW_TOKENS

_model = None
_tokenizer = None
_pipeline = None


def _resolve_model_path() -> str:
    return Config.resolve_path(Config.KANANA_MODEL_PATH)

def _load_dtype() -> torch.dtype:
    return torch.float16 if torch.cuda.is_available() else torch.float32

def get_kanana_model():
    """Kanana model/tokenizer 싱글톤 (float16 on CUDA, float32 on CPU)."""
    global _model, _tokenizer

    if _model is None:
        start_time = time.time()
        model_path = _resolve_model_path()
        dtype = _load_dtype()

        print("📥 로컬 토크나이저 로드 중...")
        tokenizer_start = time.time()
        _tokenizer = AutoTokenizer.from_pretrained(model_path, fix_mistral_regex=True)
        if _tokenizer.pad_token_id is None:
            _tokenizer.pad_token = _tokenizer.eos_token
        print(f"   ✓ 토크나이저 로드 완료 ({time.time() - tokenizer_start:.1f}초)")

        print(f"📦 로컬 Kanana 모델 로드 중... (dtype = {dtype})")
        model_start = time.time()
        load_kwargs: dict[str, Any] = {
            "torch_dtype": dtype,
            "low_cpu_mem_usage": True,
        }
        if torch.cuda.is_available():
            load_kwargs["device_map"] = "auto"
        _model = AutoModelForCausalLM.from_pretrained(model_path, **load_kwargs)
        if not torch.cuda.is_available():
            _model = _model.to("cpu")
        _model.eval()
        print(f"   ✓ 로컬 모델 로드 완료 ({time.time() - model_start:.1f}초)")
        print(f"✅ Kanana 모델 로드 완료 (총 {time.time() - start_time:.1f}초)")

    return _model, _tokenizer


def get_kanana_pipeline():
    """HF text-generation pipeline (공유 model/tokenizer 기반)."""
    global _pipeline

    model, tokenizer = get_kanana_model()
    if _pipeline is None:
        print("🔧 Kanana 파이프라인 생성 중...")
        pipeline_start = time.time()
        _pipeline = hf_pipeline(
            "text-generation",
            model = model,
            tokenizer = tokenizer,
        )
        print(f"   ✓ 파이프라인 생성 완료 ({time.time() - pipeline_start:.1f}초)")

        print("🔥 GPU 워밍업 중...")
        warmup_start = time.time()
        try:
            _ = _pipeline(
                [
                    {"role": "system", "content": "당신은 AI 어시스턴트입니다."},
                    {"role": "user", "content": "안녕하세요."},
                ],
                max_new_tokens = 10,
                do_sample = False,
                return_full_text = False,
                eos_token_id = tokenizer.eos_token_id,
            )
            print(f"   ✓ GPU 워밍업 완료 ({time.time() - warmup_start:.1f}초)")
        except Exception as e:
            print(f"   ⚠️ GPU 워밍업 실패 (무시됨): {e}")

    return _pipeline, tokenizer


def ensure_kanana_loaded() -> None:
    """오케스트레이터 startup 등에서 Kanana를 1회 선로드."""
    get_kanana_model()
    get_kanana_pipeline()


def get_kanana_response(
    messages: list,
    max_tokens: int = 512,
    temp: float = 0.3,
    repetition_penalty: float = 1.2,
) -> str:
    """chat messages → generate (news 등 pipeline 미사용 에이전트용)."""
    model, tokenizer = get_kanana_model()
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt = True,
        return_tensors = "pt",
        return_dict = True,
    ).to(model.device)

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens = max_tokens,
            do_sample = True,
            temperature = temp,
            repetition_penalty = repetition_penalty,
            pad_token_id = tokenizer.pad_token_id,
            eos_token_id = tokenizer.eos_token_id,
        )

    input_len = inputs.input_ids.shape[1]
    return tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()


def call_kanana(
    system_prompt: str,
    user_input: dict,
    max_new_tokens: int = KANANA_MAX_NEW_TOKENS,
    temperature: float = 0.5,
) -> str:
    """Kanana pipeline 호출 (system prompt + placeholder dict)."""
    pipeline, tokenizer = get_kanana_pipeline()

    formatted_system = system_prompt
    for key, value in user_input.items():
        formatted_system = formatted_system.replace(f"{{{key}}}", str(value))

    messages = [
        {"role": "system", "content": formatted_system},
        {"role": "user", "content": "위 지시사항에 따라 처리해주세요."},
    ]

    if Config.ENABLE_LOCAL_LOGGING:
        log_agent_action("Kanana 호출", {
            "max_new_tokens": max_new_tokens,
            "prompt_length": len(system_prompt),
            "user_input_keys": list(user_input.keys()),
        })

    try:
        call_start = time.time()
        response = pipeline(
            messages,
            max_new_tokens = max_new_tokens,
            do_sample = True,
            temperature = temperature,
            return_full_text = False,
            eos_token_id = tokenizer.eos_token_id,
        )
        call_time = time.time() - call_start

        if not response or len(response) == 0:
            print("⚠️ Kanana 파이프라인이 빈 응답을 반환했습니다.")
            return ""

        raw = response[0]
        if isinstance(raw, str):
            result = raw
        elif isinstance(raw, dict):
            result = raw.get("generated_text", "")
            if isinstance(result, list):
                last = result[-1] if result else ""
                result = last.get("content", "") if isinstance(last, dict) else str(last)
        else:
            result = str(raw)

        if not result or result.strip() == "":
            print("⚠️ Kanana가 빈 텍스트를 생성했습니다.")
            print(f"   원본 응답: {response}")

        if Config.ENABLE_LOCAL_LOGGING:
            log_agent_action("Kanana 응답 완료", {
                "response_length": len(result),
                "call_time": call_time,
                "has_response": bool(result),
            })
        return result

    except Exception as e:
        import traceback
        print(f"❌ Kanana 모델 호출 중 오류가 발생했습니다: {e}")
        print(f"   상세 오류: {traceback.format_exc()}")
        if Config.ENABLE_LOCAL_LOGGING:
            from utils.logger import log_error
            log_error(e, "call_kanana")
        raise


def call_kanana_structured(
    system_prompt: str,
    user_input: dict,
    output_schema: type,
    max_new_tokens: int = KANANA_MAX_NEW_TOKENS,
    transform_data: Callable[[dict], dict] | None = None,
) -> Any:
    """Structured JSON output 호출 (보정·재시도 포함)."""
    from pydantic import ValidationError

    schema_prompt = (
        "\n\n[출력 형식]\n"
        "아래 형식을 따르는 **하나의 JSON 객체만** 출력하세요.\n"
        "키 이름과 값만 포함된 JSON 형태로 답변해야 합니다.\n\n"
        f"{output_schema.model_json_schema()}\n\n"
        "[중요]\n"
        "- 반드시 최상위에 실제 필드 값들만 있는 JSON 객체를 출력하세요.\n\n"
    )
    full_prompt = system_prompt + schema_prompt

    if Config.ENABLE_LOCAL_LOGGING:
        log_agent_action("Structured Output 호출", {
            "output_schema": output_schema.__name__,
            "user_input_keys": list(user_input.keys()),
            "max_new_tokens": max_new_tokens,
        })

    response_text = call_kanana(full_prompt, user_input, max_new_tokens=max_new_tokens)

    def _parse_response(text: str) -> Any:
        json_candidate = _extract_json_candidate(text)
        decoder = json.JSONDecoder()
        data, _ = decoder.raw_decode(json_candidate.strip())
        if transform_data is not None:
            data = transform_data(data)
        return output_schema(**data)

    try:
        result = _parse_response(response_text)
        if Config.ENABLE_LOCAL_LOGGING:
            log_agent_action("Structured Output 파싱 성공", {"schema": output_schema.__name__})
        return result
    except (json.JSONDecodeError, ValidationError):
        pass

    try:
        result = _parse_response(_repair_common_json_issues(response_text))
        return result
    except (json.JSONDecodeError, ValidationError):
        pass

    retry_prompt = (
        full_prompt
        + "\n[재출력 지시]\n"
        "- 설명 없이 JSON 객체 하나만 출력하세요.\n"
    )
    retry_text = call_kanana(retry_prompt, user_input, max_new_tokens=max_new_tokens)
    try:
        return _parse_response(retry_text)
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"❌ Structured Output 파싱 실패 [{output_schema.__name__}]: {e}")
        print(f"원본 응답: {response_text[:300]}")
        if Config.ENABLE_LOCAL_LOGGING:
            from utils.logger import log_error
            log_error(e, f"call_kanana_structured - Schema: {output_schema.__name__}")
        raise


def _extract_first_json(text: Any) -> str:
    start = text.find("{")
    if start == -1:
        return text.strip()

    depth = 0
    in_string = False
    escape_next = False

    for i, ch in enumerate(text[start:], start=start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return text[start:].strip()


def _extract_json_candidate(text: str) -> str:
    codeblock_match = re.search(
        r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL | re.IGNORECASE
    )
    if codeblock_match:
        return codeblock_match.group(1).strip()
    return _extract_first_json(text)


def _repair_common_json_issues(raw_text: str) -> str:
    repaired = raw_text.strip()
    repaired = repaired.replace(""", "\"").replace(""", "\"").replace("'", "'")
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    return repaired


def extract_pure_text(raw_text: Any) -> str:
    if not raw_text:
        return ""
    if '"output":' in raw_text or '"action":' in raw_text:
        try:
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                json_obj = json.loads(match.group(0))
                return json_obj.get("output", raw_text)
        except Exception:
            match = re.search(r'"output"\s*:\s*"(.*?)"', raw_text, re.DOTALL)
            if match:
                return match.group(1).replace("\\n", "\n")
    return raw_text.replace("```json", "").replace("```", "").strip()


def _extract_output_only(text: str) -> str:
    if not text or not text.strip():
        return text

    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        inner_lines = lines[1:-1] if len(lines) > 2 else lines[1:]
        stripped = "\n".join(inner_lines).strip()

    if stripped.startswith("{"):
        json_str = _extract_first_json(stripped)
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and "output" in parsed:
                return str(parsed["output"]).strip()
        except json.JSONDecodeError:
            pass

        match = re.search(
            r'"output"\s*:\s*"((?:[^"\\]|\\.)*)"',
            stripped,
            re.DOTALL,
        )
        if match:
            return match.group(1).replace("\\n", "\n").replace('\\"', '"').strip()

    return stripped

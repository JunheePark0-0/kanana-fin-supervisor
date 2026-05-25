# Kanana Model 로드 파이프라인 (오케스트레이터·모든 에이전트에서 공유)

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline as hf_pipeline
from typing import Any
import time
import json
import re

from config_base import BaseConfig as Config
from utils.logger import logger, log_agent_action

KANANA_MAX_NEW_TOKENS = Config.KANANA_MAX_NEW_TOKENS

_pipeline = None
_tokenizer = None


def get_kanana_pipeline():
    """Kanana 모델 파이프라인을 받아오는 함수"""
    global _pipeline, _tokenizer

    if _pipeline is None:
        start_time = time.time()
        model_path = Config.resolve_path(Config.KANANA_MODEL_PATH)

        print("📥 로컬 토크나이저 로드 중...")
        tokenizer_start = time.time()
        _tokenizer = AutoTokenizer.from_pretrained(model_path, fix_mistral_regex=True)
        print(f"   ✓ 토크나이저 로드 완료 ({time.time() - tokenizer_start:.1f}초)")

        print("📦 로컬 모델 로드 중...")
        model_start = time.time()
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        print(f"   ✓ 로컬 모델 로드 완료 ({time.time() - model_start:.1f}초)")

        print("🔧 파이프라인 생성 중...")
        pipeline_start = time.time()
        _pipeline = hf_pipeline(
            "text-generation",
            model=model,
            tokenizer=_tokenizer,
        )
        print(f"   ✓ 파이프라인 생성 완료 ({time.time() - pipeline_start:.1f}초)")

        total_time = time.time() - start_time
        print(f"✅ Kanana 모델 파이프라인 로드 완료 (총 {total_time:.1f}초)")

        print("🔥 GPU 워밍업 중... (첫 질문 응답 속도 향상을 위한 사전 작업)")
        warmup_start = time.time()
        try:
            warmup_messages = [
                {"role": "system", "content": "당신은 AI 어시스턴트입니다."},
                {"role": "user", "content": "안녕하세요."},
            ]
            _ = _pipeline(
                warmup_messages,
                max_new_tokens=10,
                do_sample=False,
                return_full_text=False,
                eos_token_id=_tokenizer.eos_token_id,
            )
            print(f"   ✓ GPU 워밍업 완료 ({time.time() - warmup_start:.1f}초)")
        except Exception as e:
            print(f"   ⚠️ GPU 워밍업 실패 (무시됨): {e}")

    return _pipeline, _tokenizer


def call_kanana(
    system_prompt: str,
    user_input: dict,
    max_new_tokens: int = KANANA_MAX_NEW_TOKENS,
) -> str:
    """Kanana 모델을 직접 호출하는 함수"""
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
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.5,
            return_full_text=False,
            eos_token_id=tokenizer.eos_token_id,
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
        print(f"   프롬프트 길이: {len(formatted_system)}")
        print(f"   max_new_tokens: {max_new_tokens}")
        if Config.ENABLE_LOCAL_LOGGING:
            from utils.logger import log_error
            log_error(e, "call_kanana")
        raise


def call_kanana_structured(
    system_prompt: str,
    user_input: dict,
    output_schema: type,
    max_new_tokens: int = KANANA_MAX_NEW_TOKENS,
) -> Any:
    """Kanana 모델의 output 형태를 JSON으로 한정하여 호출하는 함수"""
    from pydantic import ValidationError

    schema_prompt = (
        "\n\n[출력 형식]\n"
        "아래 형식을 따르는 **하나의 JSON 객체만** 출력하세요.\n"
        "아래 스키마에 포함되지 않은 다른 필드는 포함해서는 안 됩니다.\n"
        "키 이름과 값만 포함된 JSON 형태로 답변해야 합니다.\n\n"
        f"{output_schema.model_json_schema()}\n\n"
        "[중요]\n"
        "- 반드시 최상위에 실제 필드 값들만 있는 JSON 객체를 출력하세요.\n"
        "- 예: {{\"pros\": \"...\", \"cons\": \"...\", \"conclusion\": \"...\"}}\n\n"
    )
    full_prompt = system_prompt + schema_prompt

    if Config.ENABLE_LOCAL_LOGGING:
        log_agent_action("Structured Output 호출", {
            "output_schema": output_schema.__name__,
            "user_input_keys": list(user_input.keys()),
            "max_new_tokens": max_new_tokens,
        })

    response_text = call_kanana(full_prompt, user_input, max_new_tokens=max_new_tokens)

    try:
        codeblock_match = re.search(
            r"```(?:json)?\s*(\{.*\})\s*```", response_text, re.DOTALL | re.IGNORECASE
        )
        json_str = codeblock_match.group(1).strip() if codeblock_match else _extract_first_json(response_text)

        decoder = json.JSONDecoder()
        data, _ = decoder.raw_decode(json_str.strip())
        result = output_schema(**data)

        if Config.ENABLE_LOCAL_LOGGING:
            log_agent_action("Structured Output 파싱 성공", {"schema": output_schema.__name__})
        return result

    except (json.JSONDecodeError, ValidationError) as e:
        print(f"❌ Structured Output 파싱 실패 [{output_schema.__name__}]: {e}")
        print(f"원본 응답: {response_text[:300]}")
        if Config.ENABLE_LOCAL_LOGGING:
            from utils.logger import log_error
            log_error(e, f"call_kanana_structured - Schema: {output_schema.__name__}")
        raise


def _extract_first_json(text: Any) -> str:
    """텍스트에서 첫 번째로 완성된 JSON 객체를 추출 (중괄호 깊이 추적)"""
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


def extract_pure_text(raw_text: Any) -> str:
    """모델 output에서 순수 텍스트만 추출 (JSON 중첩·마크다운 코드블록 제거)"""
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

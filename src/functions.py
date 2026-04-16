from typing import List, Dict, Optional, Any, Literal
import yaml
import os
import json
from config import Config

def load_prompt(prompt_name: str) -> str:
    """Kanana 프롬프트를 불러오는 함수 - 전체 프롬프트를 문자열로 반환"""
    with open(f"{os.path.dirname(os.path.abspath(__file__))}/prompts.yaml", "r", encoding = "utf-8") as f:
        prompts = yaml.safe_load(f)
        prompt = prompts.get(prompt_name, {})
    
    # System prompt 구성 (inputs에 {query} 등 플레이스홀더가 있으면 call_kanana에서 치환)
    system_prompt = f'{prompt.get("role", "")}\n\n{prompt.get("instructions", "")}'
    if prompt.get("inputs"):
        system_prompt += "\n\n" + str(prompt["inputs"])
    return system_prompt

def map_comp_name_to_ticker(comp_name: str) -> str:
    """기업 이름을 티커로 매핑하는 함수"""
    return Config.TICKER_MAP.get(comp_name, "")
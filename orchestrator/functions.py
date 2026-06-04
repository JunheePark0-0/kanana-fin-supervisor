from typing import List, Dict, Optional, Any, Literal
import yaml
import os
import json
from utils.ticker_map import TICKER_MAP
from utils.kanana_pipeline import call_kanana, call_kanana_structured

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

def extract_company_name(query: str, comp_list: List[str]) -> str:
    """
    사용자 질문에서 기업 이름을 추출하는 함수
    """
    query_lower = query.lower()
    for comp in comp_list:
        if comp.lower() in query_lower:
            return comp
    return None

def map_comp_name_to_ticker(comp_name: str) -> str:
    """기업 이름을 티커로 매핑하는 함수"""
    return TICKER_MAP.get(comp_name, "")
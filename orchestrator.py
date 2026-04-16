"""
1. 사용자 질문 파악 -> 라우팅
2. 라우팅 결과에 따라 필요한 에이전트 호출 (병렬)
3. 결과 취합 -> 최종 답변 생성
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

# 루트 `utils`·하위 에이전트 `utils`와 충돌하지 않도록 파이프라인을 먼저 로드
from src.core.kanana_pipeline import call_kanana, call_kanana_structured
from src.functions import load_prompt, map_comp_name_to_ticker
from src.schemas import (
    UserInput,
    AgentRequest,
    AgentResponse,
    FinalResponse,
    AgentName,
)

from Legal_Agent.main import legal_agent_main
from Stock_Agent.main import stock_agent_main


def _legal_raw_to_agent_response(raw: Any) -> AgentResponse:
    if isinstance(raw, Exception):
        return AgentResponse(
            agent_name="Legal Agent",
            answer=f"오류: {raw}",
            sources=[],
        )
    answer = ""
    sources: List[str] = []
    try:
        if isinstance(raw, dict):
            ans = raw.get("answer")
            if ans is not None:
                answer = str(getattr(ans, "answer", ans))
    except Exception:
        answer = str(raw)
    if not answer and isinstance(raw, dict):
        answer = str(raw)
    return AgentResponse(agent_name="Legal Agent", answer=answer, sources=sources)


def _stock_raw_to_agent_response(raw: Any) -> AgentResponse:
    if isinstance(raw, Exception):
        return AgentResponse(
            agent_name="Stock Agent",
            answer=f"오류: {raw}",
            sources=[],
        )
    if isinstance(raw, dict):
        parts: List[str] = []
        if raw.get("final_report") is not None:
            parts.append(str(raw["final_report"]))
        if raw.get("crawling_summary") is not None:
            parts.append(f"[크롤링 요약]\n{raw['crawling_summary']}")
        answer = "\n\n".join(parts) if parts else str(raw)
    else:
        answer = str(raw)
    return AgentResponse(agent_name="Stock Agent", answer=answer, sources=[])


def _resolve_input_ticker(user_input: UserInput) -> Optional[str]:
    if user_input.ticker:
        return user_input.ticker.strip().upper()
    if user_input.extracted_company:
        t = map_comp_name_to_ticker(user_input.extracted_company)
        return t or None
    return None


class Orchestrator:
    def __init__(self, jobs: Dict[str, Any]):
        self.jobs = jobs

    async def determine_agents(self, query: str, document_path: Optional[str] = None) -> AgentRequest:
        routing_prompt = load_prompt("routing_prompt")
        return call_kanana_structured(
            routing_prompt,
            {"query": query, "document_path": document_path or ""},
            output_schema=AgentRequest,
            max_new_tokens=128,
        )

    def summarize_results(self, results: List[AgentResponse]) -> str:
        final_answer = ""
        for result in results:
            final_answer += result._to_report_text()

        summary_prompt = load_prompt("summary_prompt")
        return call_kanana(
            summary_prompt,
            {"all_answers": final_answer},
            max_new_tokens=2056,
        )

    async def execute_agents(self, job_id: str, user_input: UserInput) -> FinalResponse:
        query = user_input.query
        document_path = user_input.document_path

        input_ticker = _resolve_input_ticker(user_input)

        if input_ticker:
            required_agents: List[AgentName] = ["Stock Agent"]
            ticker = input_ticker
            self.jobs[job_id]["routing"] = None
        else:
            routing = await self.determine_agents(query, document_path)
            required_agents = list(routing.selected_agents)
            self.jobs[job_id]["routing"] = routing.model_dump()
            ticker = None
            if routing.extracted_company:
                ticker = map_comp_name_to_ticker(routing.extracted_company) or None

        self.jobs[job_id]["status"] = "processing"
        self.jobs[job_id]["selected_agents"] = required_agents
        self.jobs[job_id]["ticker"] = ticker

        if "Stock Agent" in required_agents and not ticker:
            msg = "Stock Agent가 선택되었으나 티커를 결정할 수 없습니다. 질문에 기업명/티커를 넣거나 ticker 필드를 지정하세요."
            self.jobs[job_id]["status"] = "error"
            self.jobs[job_id]["error"] = msg
            raise ValueError(msg)

        tasks: List[Any] = []
        for name in required_agents:
            if name == "Legal Agent":
                tasks.append(self._run_legal(query, document_path))
            elif name == "Stock Agent":
                tasks.append(self._run_stock(ticker))
            elif name in ("Report Agent", "News Agent", "Trend Agent"):
                raise ValueError(f"{name}는 아직 오케스트레이터에 연결되지 않았습니다.")

        if not tasks:
            msg = "선택된 실행 가능한 에이전트가 없습니다."
            self.jobs[job_id]["status"] = "error"
            self.jobs[job_id]["error"] = msg
            raise ValueError(msg)

        agent_responses: List[AgentResponse] = await asyncio.gather(*tasks)

        summary = self.summarize_results(agent_responses)
        final_response = FinalResponse(summary=summary, all_answers=agent_responses)

        final_report = final_response._to_final_report()
        self.jobs[job_id]["status"] = "completed"
        self.jobs[job_id]["result"] = final_report
        self.jobs[job_id]["final_response"] = final_response.model_dump()

        return final_response

    async def _run_legal(self, query: str, document_path: Optional[str]) -> AgentResponse:
        try:
            raw = await legal_agent_main(query, document_path)
            return _legal_raw_to_agent_response(raw)
        except Exception as e:
            return _legal_raw_to_agent_response(e)

    async def _run_stock(self, ticker: str) -> AgentResponse:
        try:
            raw = await stock_agent_main(ticker)
            return _stock_raw_to_agent_response(raw)
        except Exception as e:
            return _stock_raw_to_agent_response(e)

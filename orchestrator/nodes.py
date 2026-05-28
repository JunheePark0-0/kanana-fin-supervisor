from typing import List, Dict, TypedDict, Optional
import operator
import asyncio

from orchestrator.states import OrchestratorState
from orchestrator.schemas import UserInput, AgentName, AgentRequest, AgentResponse, FinalResponse
from config import BaseConfig as Config
from orchestrator.functions import load_prompt, extract_company_name, map_comp_name_to_ticker
from utils.kanana_pipeline import call_kanana, call_kanana_structured

from agents.legal_agent.main import legal_agent_main
from agents.stock_agent.main import stock_agent_main
from agents.news_agent.main import news_agent_main
from agents.trend_agent.main import trend_agent_main
from agents.report_agent.main import report_agent_main

from orchestrator.converters import legal_raw_to_agent_response, news_raw_to_agent_response, report_raw_to_agent_response, stock_raw_to_agent_response, trend_raw_to_agent_response

async def routing_node(state: OrchestratorState) -> OrchestratorState:
    """
    라우팅 노드: 질문을 분석해 필요한 에이전트를 호출하는 노드
    """
    user_input = state["user_input"]
    query = user_input.query
    document_path = user_input.document_path
    
    # ticker가 이미 있다면 라우팅 생략
    input_ticker = user_input.ticker
    if input_ticker and not query.strip():
        return {
            **state,
            "selected_agents": ["Stock Agent"],
            "ticker": input_ticker.strip().upper(),
            "agent_requests": None
        }
    
    # 기업명 추출, 티커 매핑
    comp_list = list(Config.TICKER_MAP.keys())
    extracted_company = extract_company_name(query, comp_list)
    query_ticker = map_comp_name_to_ticker(extracted_company) if extracted_company else None

    ticker = input_ticker.strip().upper() if input_ticker else query_ticker

    # 라우팅 진행
    routing_prompt = load_prompt("routing_prompt")
    routing_response = call_kanana_structured(
        routing_prompt,
        {"query": query, "document_path": document_path or "", "ticker": ticker or ""},
        output_schema = AgentRequest
    )

    return {
        **state,
        "selected_agents": routing_response.selected_agents,
        "ticker": ticker,
        "agent_requests": routing_response
    }

async def run_agents_node(state: OrchestratorState) -> OrchestratorState:
    """
    에이전트 실행 노드: 라우팅 노드에서 선택된 에이전트를 호출, 실행 후 결과를 저장하는 노드
    """
    user_input = state["user_input"]
    query = user_input.query
    document_path = user_input.document_path
    ticker = state.get("ticker")

    selected_agents = state["selected_agents"]

    tasks = []
    agent_responses: List[AgentResponse] = []

    # Stock Agent 선택되었는데 ticker가 없는 경우
    skipped: List[AgentResponse] = []
    if "Stock Agent" in selected_agents and not ticker:
        selected_agents = [agent for agent in selected_agents if agent != "Stock Agent"]
        skipped.append(AgentResponse(
            agent_name = "Stock Agent",
            answer = "ticker가 없어 실행되지 않았습니다.",
            sources = []
        ))

    for agent_name in selected_agents:
        if agent_name == "Legal Agent":
            tasks.append(run_legal_agent(query, document_path))
        elif agent_name == "News Agent":
            tasks.append(run_news_agent(query))
        elif agent_name == "Report Agent":
            if not document_path:
                raise ValueError("Report Agent 실행에는 document_path(PDF 경로)가 필요합니다.")
            tasks.append(run_report_agent(document_path, query))
        elif agent_name == "Stock Agent":
            if not ticker:
                raise ValueError("Stock Agent 실행에는 ticker가 필요합니다.")
            tasks.append(run_stock_agent(ticker))
        elif agent_name == "Trend Agent":
            tasks.append(run_trend_agent(query))
        else:
            raise ValueError(f"Unknown agent name: {agent_name}")
    if tasks:
        agent_responses = await asyncio.gather(*tasks) if tasks else []
    return {
        **state,
        "agent_responses": list(agent_responses) + skipped,
    }

async def summarize_node(state: OrchestratorState) -> OrchestratorState:
    """
    결과 요약 노드: 에이전트 결과를 요약하여 최종 결과를 도출하는 노드
    """
    agent_responses = state["agent_responses"]
    all_answers = "\n\n".join([response._to_report_text() for response in agent_responses])
    all_sources = "\n".join(
        f"{response.agent_name}: {', '.join(response.sources)}" 
        for response in agent_responses if response.sources
        )
    summary_prompt = load_prompt("summary_prompt")
    summary_response = call_kanana(
        summary_prompt,
        {
            "all_answers": all_answers,
            "all_sources": all_sources
        },
        max_new_tokens = Config.KANANA_SUMMARY_MAX_NEW_TOKENS
    )
    final_response = FinalResponse(summary = summary_response, all_answers = agent_responses)
    final_report = final_response._to_final_report()
    print(final_report)
    return {
        **state,
        "final_response": final_response
    }

# 각 Agent 실행 -> 결과 도출 -> AgentResponse 변환
async def run_legal_agent(query: str, document_path: str | None = None) -> AgentResponse:
    try:
        raw_output = await legal_agent_main(query, document_path)
        return legal_raw_to_agent_response(raw_output)
    except Exception as e:
        return legal_raw_to_agent_response(e)

async def run_news_agent(query: str) -> AgentResponse:
    try:
        raw_output = await news_agent_main(query)
        return news_raw_to_agent_response(raw_output)
    except Exception as e:
        return news_raw_to_agent_response(e)

async def run_report_agent(document_path: str, task: str) -> AgentResponse:
    try:
        raw_output = await report_agent_main(pdf_path = document_path, task = task)
        return report_raw_to_agent_response(raw_output)
    except Exception as e:
        return report_raw_to_agent_response(e)

async def run_stock_agent(ticker: str) -> AgentResponse:
    try:
        raw_output = await stock_agent_main(ticker)
        return stock_raw_to_agent_response(raw_output)
    except Exception as e:
        return stock_raw_to_agent_response(e)

async def run_trend_agent(query: str) -> AgentResponse:
    try:
        raw_output = await trend_agent_main(query)
        return trend_raw_to_agent_response(raw_output)
    except Exception as e:
        return trend_raw_to_agent_response(e)

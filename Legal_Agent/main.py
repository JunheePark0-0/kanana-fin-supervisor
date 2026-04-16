"""
Agent 전체 실행 파일 - Kanana 버전
"""

import os
from dotenv import load_dotenv

import sys

# Legal_Agent 전용 `src`가 Kanana_Agent 루트의 `src`보다 우선하도록 순서 유지
_KANANA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LEGAL_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_LEGAL_ROOT, ".env"))
sys.path.insert(0, _KANANA_ROOT)
sys.path.insert(0, _LEGAL_ROOT)

# Config 및 Logger import
from config import Config
import utils.logger as app_logger
from utils.logger import log_agent_action

from src.Agent.schemas import UserInput
from src.Agent.kanana_pipeline import get_kanana_pipeline
from src.Agent.graph import legal_agent

import asyncio

# 그래프가 복잡하므로 전체 그래프를 한 번만 생성해두고 반복하여 사용하기 위함
_compiled_legal_agent = None
def get_compiled_agent():
    """그래프 컴파일 함수"""
    global _compiled_legal_agent
    if _compiled_legal_agent is None:
        _compiled_legal_agent = legal_agent()
    return _compiled_legal_agent

async def legal_agent_main(query: str, document_path:str = None):
    """Legal Agent - 상위 에이전트가 호출할 최종 진입 지점"""

    print("=" * 60)
    print("⚖️  Legal Agent")
    print("=" * 60)
    
    # 로컬 로깅 설정에 따라 logger 재설정
    app_logger.setup_logger()

    if Config.ENABLE_LOCAL_LOGGING:
        now_str = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"logs/law_agent_{now_str}.log"
        app_logger.logger.info(f"로컬 로깅 활성화: {now_str}")
    else:
        print("📝 로컬 로그: 비활성화")
        log_filename = None
    
    # ============================================================================
    # Agent 워크플로우
    # ============================================================================
    print("🔧 Agent 워크플로우 초기화 중...")
    agent = get_compiled_agent()
    print("✅ Agent 준비 완료!")

    original_input = UserInput(
        query = query if query else None,
        document_path = document_path if document_path else None
    )

    if Config.ENABLE_LOCAL_LOGGING:
        log_agent_action("에이전트 워크플로우 시작")

    if Config.ENABLE_LOCAL_LOGGING:
        log_agent_action("사용자 입력 수신", {
            "query": query,
            "document_path": document_path
        })

    result = await agent.ainvoke({
        "original_input": original_input,
        "input_query": query if query else ""
    })

    answer = None
    if result.get("answer"):
        answer = result.get("answer").answer
        if Config.ENABLE_LOCAL_LOGGING:
            app_logger.logger.info("\n" + "=" * 30)
            app_logger.logger.info("[최종 답변]")
            app_logger.logger.info(f"\n{answer}")
            app_logger.logger.info("\n" + "=" * 30)

    if Config.ENABLE_LOCAL_LOGGING:
        from utils.logger import log_conversation
        log_conversation(query, answer if answer is not None else "")

    if Config.ENABLE_LOCAL_LOGGING:
                log_agent_action("에이전트 워크플로우 완료")

    return result

if __name__ == "__main__":
    import asyncio
    sample_query = "임대차 계약 해지 통보 방법 알려줘"
    asyncio.run(legal_agent_main(sample_query))
"""
Agent 전체 실행 파일 - Kanana 버전
"""

import os
import sys

_KANANA_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LEGAL_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _KANANA_ROOT)
sys.path.insert(0, _LEGAL_ROOT)

# Config 및 Logger import
from legal_config import LegalConfig
import legal_utils.logger as app_logger
from legal_utils.logger import log_agent_action

from legal_src.Agent.schemas import UserInput
from legal_src.Agent.graph import legal_agent

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
    log_run_dir = None
    if LegalConfig.ENABLE_LOCAL_LOGGING:
        from utils.log_paths import create_agent_log_run_dir

        log_run_dir = create_agent_log_run_dir(LegalConfig.AGENT_LOG_NAME)
        app_logger.setup_logger(log_run_dir=log_run_dir)
        app_logger.logger.info(f"로컬 로깅 활성화: {log_run_dir}")
    else:
        app_logger.setup_logger()
        print("📝 로컬 로그: 비활성화")
    
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

    if LegalConfig.ENABLE_LOCAL_LOGGING:
        log_agent_action("에이전트 워크플로우 시작")

    if LegalConfig.ENABLE_LOCAL_LOGGING:
        log_agent_action("사용자 입력 수신", {
            "query": query,
            "document_path": document_path
        })

    result = await agent.ainvoke({
        "original_input": original_input,
        "input_query": query if query else ""
    })

    answer = None
    answer_output = result.get("answer")
    if answer_output:
        answer = answer_output.answer
        if LegalConfig.ENABLE_LOCAL_LOGGING:
            app_logger.logger.info("\n" + "=" * 30)
            app_logger.logger.info("[최종 답변]")
            app_logger.logger.info(f"\n{answer}")
            app_logger.logger.info("\n" + "=" * 30)

            from legal_utils.report_rmd import save_legal_final_report_rmd

            report_path = save_legal_final_report_rmd(
                query = query,
                document_path = document_path,
                answer = answer_output,
                log_run_dir = log_run_dir,
            )
            log_agent_action("final_response 저장", {"path": str(report_path)})

    if LegalConfig.ENABLE_LOCAL_LOGGING:
        from legal_utils.logger import log_conversation
        log_conversation(query, answer if answer is not None else "")

    if LegalConfig.ENABLE_LOCAL_LOGGING:
                log_agent_action("에이전트 워크플로우 완료")

    return result

if __name__ == "__main__":
    import asyncio
    sample_query = "임대차 계약 해지 통보 방법 알려줘"
    asyncio.run(legal_agent_main(sample_query))
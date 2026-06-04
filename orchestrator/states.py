from typing import List, Dict, TypedDict, Optional
import operator

from orchestrator.schemas import UserInput, AgentName, AgentRequest, AgentResponse, FinalResponse

class OrchestratorState(TypedDict, total = False):
    """Agent Orchestrator State"""
    user_input: UserInput
    job_id: str
    target_agent: Optional[AgentName] # 사용자가 선택한 에이전트
    selected_agents: List[AgentName]
    ticker: Optional[str]

    agent_requests: Optional[AgentRequest]
    agent_responses: List[AgentResponse]

    final_response: FinalResponse

    errors: Optional[Dict[str, str]]
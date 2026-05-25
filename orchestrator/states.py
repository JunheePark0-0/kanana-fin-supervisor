from typing import List, Dict, TypedDict, Optional
import operator

from orchestrator.schemas import UserInput, AgentRequest, AgentResponse, FinalResponse

class OrchestratorState(TypedDict, total = False):
    """Agent Orchestrator State"""
    user_input: UserInput

    agent_requests: List[AgentRequest]
    agent_responses: List[AgentResponse]

    final_response: FinalResponse

    errors: Optional[Dict[str, str]]
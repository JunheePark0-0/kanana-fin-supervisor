from typing import List, Dict, TypedDict, Optional
import operator

from src.schemas import UserInput, AgentResponse, FinalResponse

class OrchestratorState(TypedDict, total = False):
    """Agent Orchestrator State"""
    user_input: UserInput

    selected_agents: List[str]
    agent_responses: Dict[str, AgentResponse]

    final_response: FinalResponse
    summary: str

    errors: Optional[Dict[str, str]]
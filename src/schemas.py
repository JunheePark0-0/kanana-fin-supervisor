from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field, ConfigDict

class UserInput(BaseModel):
    """사용자 입력 형식"""
    query: str = Field(..., description = "The user's question")
    document_path: Optional[str] = Field(None, description = "The path of the document (ex. PDF)")

class AgentResponse(BaseModel):
    """각 에이전트의 결과 형식"""
    answer: str = Field(..., description = "The answer from each agent")
    sources: List[str] = Field(..., description = "The sources used when generating the answer")

class FinalResponse(BaseModel):
    """하위 에이전트의 응답을 조합한 최종 응답 형식"""
    final_answer: str = Field(..., description = "The final answer from the combined response")
    all_sources: List[str] = Field(..., description = "The sources used when generating the final answer")
    metadata: Optional[Dict[str, Any]] = Field(None, description = "The metadata of the final response")
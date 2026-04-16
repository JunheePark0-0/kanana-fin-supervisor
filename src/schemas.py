from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field, ConfigDict

class UserInput(BaseModel):
    """사용자 입력 형식"""
    query: str = Field(..., description = "The user's question")
    document_path: Optional[str] = Field(None, description = "The path of the document (ex. PDF)")
    ticker: Optional[str] = Field(None, description = "The ticker of the company")

class AgentRequest(BaseModel):
    """라우팅 에이전트의 결과 형식"""
    selected_agents: str = Literal["Report Agent", "Legal Agent", "Stock Agent", "News Agent", "Trend Agent"]
    extracted_company: Optional[str] = Field(None, description = "The company name extracted from the user's question")
    reason: str = Field(..., description = "The reason for selecting the agents")

class AgentResponse(BaseModel):
    """각 에이전트의 결과 형식"""
    agent_name: str = Literal["Report Agent", "Legal Agent", "Stock Agent", "News Agent", "Trend Agent"]
    answer: str = Field(..., description = "The answer from each agent")
    sources: List[str] = Field(..., description = "The sources used when generating the answer")

    def _to_report_text(self) -> str:
        """Report Agent의 결과를 텍스트로 변환하는 함수"""
        report = []
        report.append(f"="*30)
        report.append(f"{self.agent_name}")
        report.append(f"="*30)
        report.append(f"**답변**\n{self.answer}")
        if self.sources:
            report.append(f"**참고자료**\n{', '.join(self.sources)}")
        return "\n\n".join(report) if report else "에이전트 결과 도출에 실패했습니다."

class FinalResponse(BaseModel):
    """하위 에이전트의 응답을 조합한 최종 응답 형식"""
    summary: str = Field(..., description = "The summary of the final answer")
    all_answers: List[AgentResponse] = Field(..., description = "The all answers from all the required agents")

    def _to_final_report(self) -> str:
        """최종 결과를 텍스트로 변환하는 함수"""
        report = []
        report.append(f"="*50)
        report.append(f"**요약**\n{self.summary}")
        report.append(f"="*50)
        report.append(f"**모든 에이전트의 응답**\n")
        for answer in self.all_answers:
            report.append(answer._to_report_text())
        return "\n\n".join(report) if report else "모든 에이전트의 결과 도출에 실패했습니다."

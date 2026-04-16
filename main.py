# FastAPI 서버 모아서 실행

from fastapi import FastAPI
from src.schemas import UserInput, AgentResponse, FinalResponse
from src.core.kanana_pipeline import get_kanana_pipeline, call_kanana, call_kanana_structured





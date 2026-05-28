# Kanana Orchestrator API

from __future__ import annotations

import uuid
from typing import Any, Dict

import dotenv
dotenv.load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from orchestrator.graph import orchestrator_graph
from orchestrator.states import OrchestratorState
from orchestrator.schemas import FinalResponse, UserInput
from utils.kanana_pipeline import ensure_kanana_loaded

app = FastAPI(
    title = "Kanana Orchestrator API",
    description = "질문 라우팅 및 하위 에이전트 오케스트레이션",
    version = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

jobs: Dict[str, Any] = {}
graph = orchestrator_graph()

@app.on_event("startup")
async def startup_event() -> None:
    print("🔄 Orchestrator startup: Kanana 모델 선로드 중...")
    ensure_kanana_loaded()
    print("✅ Kanana 모델 선로드 완료")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=FinalResponse)
async def ask(user_input: UserInput) -> FinalResponse:
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"job_id": job_id, "status": "pending", "input": user_input.model_dump()}

    try:
        jobs[job_id]["status"] = "processing"
        initial_state = OrchestratorState(
            user_input = user_input,
            job_id = job_id
        )
        result = await graph.ainvoke(initial_state) 

        final_response = result.get("final_response")
        if final_response is None:
            raise ValueError("오케스트레이터가 최종 응답을 생성하지 못했습니다.")
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = final_response._to_final_report()
        return final_response

    except ValueError as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        raise HTTPException(status_code = 400, detail = str(e)) from e


@app.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    if job_id not in jobs:
        raise HTTPException(status_code = 404, detail = f"job_id '{job_id}'를 찾을 수 없습니다.")
    return jobs[job_id]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host = "0.0.0.0", port = 8000, reload = False)

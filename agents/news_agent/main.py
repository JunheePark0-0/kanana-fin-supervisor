import sys

from tavily import TavilyClient

from config import (
    AGENT_LOG_NAME,
    COLLECTION_NAME,
    EMBEDDING_MODEL_DIR,
    ENABLE_LOCAL_LOGGING,
    QDRANT_PATH,
    SKIP_QDRANT,
    TAVILY_API_KEY,
)
from embeddings import get_embeddings
from graph.graph import build_graph_app
from graph.nodes import init_runtime
from utils.kanana_pipeline import get_kanana_model
from utils.log_paths import get_agent_log_run_dir
from utils.qa_log import append_qa_log


def main():
    if SKIP_QDRANT:
        from verify_setup import run_checks

        print(
            "SKIP_QDRANT=1 — Qdrant에 연결하지 않습니다. "
            "적재 완료 후 SKIP_QDRANT를 끄고 실행하세요.\n"
        )
        sys.exit(run_checks())
    embeddings = get_embeddings(
        model_name_or_path=EMBEDDING_MODEL_DIR,
        local_files_only=True,
    )
    from vectorstore import init_vectorstore

    model, tokenizer = get_kanana_model()
    try:
        _, vector_db, _ = init_vectorstore(
            qdrant_path=QDRANT_PATH,
            collection_name=COLLECTION_NAME,
            embeddings=embeddings,
        )
    except RuntimeError as exc:
        msg = str(exc)
        if "already accessed by another instance" in msg:
            print("\n[Qdrant 잠금 감지]")
            print(f"- 현재 경로: {QDRANT_PATH}")
            print("- 다른 프로세스(예: 코랩/다른 파이썬)가 DB를 사용 중입니다.")
            print("- 해당 프로세스를 종료한 뒤 다시 실행해 주세요.")
            print("- 또는 qdrant_db 복제본 경로를 QDRANT_PATH로 지정하면 병렬 테스트가 가능합니다.")
            return
        raise
    tavily = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else TavilyClient(api_key="")

    search_log_path = None
    qa_log_path = None
    if ENABLE_LOCAL_LOGGING:
        log_run_dir = get_agent_log_run_dir(AGENT_LOG_NAME)
        search_log_path = str(log_run_dir / "news_search_log.jsonl")
        qa_log_path = str(log_run_dir / "news_qa_log.jsonl")
        print(f"로컬 로깅 활성화: {log_run_dir}")
    else:
        print("로컬 로깅 비활성화 — 검색/QA 로그 파일을 생성하지 않습니다.")

    init_runtime(
        model=model,
        tokenizer=tokenizer,
        vector_db=vector_db,
        tavily=tavily,
        search_log_path=search_log_path,
    )
    app = build_graph_app()

    print("KR 금융 뉴스 RAG 시작. 종료하려면 exit 입력")
    while True:
        q = input("\n질문> ").strip()
        if q.lower() in {"exit", "quit"}:
            break
        result = app.invoke({"question": q})
        answer = result.get("final_answer", "답변이 생성되지 않았습니다.")
        if qa_log_path:
            append_qa_log(
                qa_log_path,
                q,
                answer,
                extra={
                    "question_type": result.get("question_type"),
                    "final_check_route": result.get("final_check_route"),
                },
            )
        print("\n" + answer)


_news_app = None


def _get_news_app():
    global _news_app
    if _news_app is not None:
        return _news_app

    embeddings = get_embeddings(
        model_name_or_path=EMBEDDING_MODEL_DIR,
        local_files_only=True,
    )
    from vectorstore import init_vectorstore

    model, tokenizer = get_kanana_model()
    _, vector_db, _ = init_vectorstore(
        qdrant_path=QDRANT_PATH,
        collection_name=COLLECTION_NAME,
        embeddings=embeddings,
    )
    tavily = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else TavilyClient(api_key="")

    init_runtime(
        model=model,
        tokenizer=tokenizer,
        vector_db=vector_db,
        tavily=tavily,
        search_log_path=None,
    )
    _news_app = build_graph_app()
    return _news_app


async def news_agent_main(query: str) -> dict:
    """상위 오케스트레이터가 호출할 최종 진입점"""
    app = _get_news_app()

    qa_log_path = None
    if ENABLE_LOCAL_LOGGING:
        log_run_dir = get_agent_log_run_dir(AGENT_LOG_NAME, new_folder=True)
        qa_log_path = str(log_run_dir / "news_qa_log.jsonl")

    result = await app.ainvoke({"question": query})
    if qa_log_path:
        append_qa_log(
            qa_log_path,
            query,
            result.get("final_answer", "답변이 생성되지 않았습니다."),
            extra={
                "question_type": result.get("question_type"),
                "final_check_route": result.get("final_check_route"),
            },
        )
    return result


if __name__ == "__main__":
    main()

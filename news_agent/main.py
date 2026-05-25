import sys

from tavily import TavilyClient

from config import (
    COLLECTION_NAME,
    EMBEDDING_MODEL_DIR,
    MODEL_DIR,
    QA_LOG_PATH,
    QDRANT_PATH,
    SEARCH_LOG_PATH,
    SKIP_QDRANT,
    TAVILY_API_KEY,
)
from embeddings import get_embeddings, load_kanana_model
from graph.graph import build_graph_app
from graph.nodes import init_runtime
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

    tokenizer, model = load_kanana_model(MODEL_DIR)
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

    init_runtime(
        model=model,
        tokenizer=tokenizer,
        vector_db=vector_db,
        tavily=tavily,
        search_log_path=SEARCH_LOG_PATH,
    )
    app = build_graph_app()

    print("KR 금융 뉴스 RAG 시작. 종료하려면 exit 입력")
    while True:
        q = input("\n질문> ").strip()
        if q.lower() in {"exit", "quit"}:
            break
        result = app.invoke({"question": q})
        answer = result.get("final_answer", "답변이 생성되지 않았습니다.")
        append_qa_log(
            QA_LOG_PATH,
            q,
            answer,
            extra={
                "question_type": result.get("question_type"),
                "final_check_route": result.get("final_check_route"),
            },
        )
        print("\n" + answer)


if __name__ == "__main__":
    main()

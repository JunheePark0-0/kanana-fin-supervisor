from typing import List, TypedDict

from langchain_core.documents import Document


class GraphState(TypedDict, total=False):
    question: str
    rewritten_question: str
    question_type: str
    metadata_extract: dict
    internal_docs: List[Document]
    internal_context: str
    internal_answer: str
    internal_ok: bool
    internal_attempt: int
    external_docs: List[dict]
    external_context: str
    has_finance_results: bool
    final_answer: str
    all_contexts: List[str]
    check_reason: str
    final_check_reason: str
    final_check_route: str
    failed_claims: List[str]
    ragas_scores: dict
    final_attempt: int

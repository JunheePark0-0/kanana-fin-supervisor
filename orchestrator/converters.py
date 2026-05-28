# Agent의 Raw Response를 AgentResponse 형식으로 변환

from typing import Any, List

from orchestrator.schemas import AgentResponse


def _doc_metadata(doc: Any) -> dict:
    """News/Trend Agent의 출처 메타데이터 추출"""
    if hasattr(doc, "metadata"):
        return dict(getattr(doc, "metadata") or {})
    if isinstance(doc, dict):
        return dict(doc.get("metadata") or doc)
    return {}

def _unique_sources(sources: List[dict]) -> List[dict]:
    """Stock Agent의 출처 중복 제거 (뉴스: url, 공시: form+filed_date 기준)"""
    seen: set = set()
    unique: List[dict] = []
    for source in sources:
        if source.get("source_type") == "news":
            key = ("news", source.get("url") or source.get("title"))
        else:
            key = ("filing", source.get("form"), source.get("filed_date"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(source)
    return unique

def _unique_str_list(items: List[str]) -> List[str]:
    return list(dict.fromkeys(item for item in items if item))

def legal_raw_to_agent_response(raw: Any) -> AgentResponse:
    """Legal Agent 결과를 AgentResponse 형식으로 변환"""
    if isinstance(raw, Exception):
        return AgentResponse(
            agent_name = "Legal Agent",
            answer = f"오류: {raw}",
            sources = [],
        )
    try:
        # 최종 답변
        answer_output = raw.get("answer")
        answer = answer_output.answer if answer_output else ""
        
        # 사용 컨텍스트
        reranked_contexts = raw.get("reranked_contexts", [])
        sources = [str(context.source) for context in reranked_contexts] if reranked_contexts else []

        if not sources and answer_output and getattr(answer_output, "source", None):
            source = answer_output.source
            if isinstance(source, list):
                sources = [str(s) for s in source]
            elif source:
                sources = [str(source)]

    except Exception:
        answer = str(raw)
        sources = []
    
    return AgentResponse(agent_name = "Legal Agent", answer = answer, sources = sources)

def news_raw_to_agent_response(raw: Any) -> AgentResponse:
    """News Agent graph.invoke 결과를 AgentResponse 형식으로 변환"""
    if isinstance(raw, Exception):
        return AgentResponse(
            agent_name = "News Agent",
            answer = f"오류: {raw}",
            sources = [],
        )
    try:
        answer = raw.get("final_answer") or raw.get("internal_answer") or "답변이 생성되지 않았습니다."
        sources: List[str] = []

        for doc in raw.get("internal_docs") or []:
            meta = _doc_metadata(doc)
            title = meta.get("title", "")
            press = meta.get("press", "")
            date = meta.get("date", "")
            url = meta.get("url", "")
            if url:
                sources.append(url)
            elif title:
                label = f"{title} ({press} | {date})".strip()
                sources.append(label.rstrip(" ()|"))

        for doc in raw.get("external_docs") or []:
            if not isinstance(doc, dict):
                continue
            url = doc.get("url", "")
            title = doc.get("title", "")
            if url:
                sources.append(url)
            elif title:
                sources.append(title)

        sources = _unique_str_list(sources)

    except Exception:
        answer = str(raw)
        sources = []

    return AgentResponse(agent_name = "News Agent", answer = answer, sources = sources)

def report_raw_to_agent_response(raw: Any) -> AgentResponse:
    """Report Agent report_agent_main() / ReportResult.to_dict() 결과 변환"""
    if isinstance(raw, Exception):
        return AgentResponse(
            agent_name = "Report Agent",
            answer = f"오류: {raw}",
            sources = [],
        )
    try:
        answer = raw.get("report_text") or "보고서 생성에 실패했습니다."

        meta_lines: List[str] = []
        now_period = raw.get("now_period")
        ref_period = raw.get("ref_period")
        compare = raw.get("compare")
        unit = raw.get("unit")
        if now_period:
            meta_lines.append(f"당기: {now_period}")
        if ref_period:
            meta_lines.append(f"비교 기간: {ref_period} ({compare})")
        if unit:
            meta_lines.append(f"단위: {unit}")
        if meta_lines:
            answer = "\n".join(meta_lines) + "\n\n" + answer

        warnings = raw.get("warnings") or []
        if warnings:
            answer += "\n\n[경고]\n" + "\n".join(f"- {warning}" for warning in warnings)

        sources: List[str] = []
        source_pdf = raw.get("source_pdf")
        effective_pdf = raw.get("effective_pdf")
        if source_pdf:
            sources.append(str(source_pdf))
        if effective_pdf and effective_pdf != source_pdf:
            sources.append(str(effective_pdf))

    except Exception:
        answer = str(raw)
        sources = []

    return AgentResponse(agent_name="Report Agent", answer=answer, sources=sources)

def stock_raw_to_agent_response(raw: Any) -> AgentResponse:
    if isinstance(raw, Exception):
        return AgentResponse(
            agent_name = "Stock Agent",
            answer = f"오류: {raw}",
            sources = [],
        )
    try:
        # 최종 답변
        answer = raw.get("final_report") or "최종 결론 도출에 실패했습니다."

        # 사용 컨텍스트
        raw_sources = raw.get("sources", [])
        unique_sources = _unique_sources(raw_sources)

        sources = []
        for source in unique_sources:
            if source.get("source_type") == "news" and source.get("url"):
                sources.append(source.get("url"))
            elif source.get("source_type") == "filing":
                sources.append(f"{source.get('form', '')} ({source.get('filed_date', '')})")

    except Exception:
        answer = str(raw)
        sources = []
    
    return AgentResponse(agent_name = "Stock Agent", answer = answer, sources = sources)

def trend_raw_to_agent_response(raw: Any) -> AgentResponse:
    """Trend Agent graph.invoke / trend_agent_main() 결과 변환"""
    if isinstance(raw, Exception):
        return AgentResponse(
            agent_name = "Trend Agent",
            answer = f"오류: {raw}",
            sources = [],
        )
    try:
        answer = raw.get("answer") or "(답변 없음)"
        elapsed = raw.get("elapsed")
        if elapsed:
            answer = f"{answer}\n\n[소요시간] {elapsed}"

        sources: List[str] = []
        for doc in raw.get("retrieved_docs") or []:
            meta = _doc_metadata(doc)
            url = meta.get("url", "")
            date = meta.get("date", "")
            item = meta.get("item", "")
            section = meta.get("section", "")
            if url:
                sources.append(url)
            else:
                label = " | ".join(part for part in [date, section, item] if part)
                if label:
                    sources.append(label)

        sources = _unique_str_list(sources)

    except Exception:
        answer = str(raw)
        sources = []

    return AgentResponse(agent_name = "Trend Agent", answer = answer, sources = sources)


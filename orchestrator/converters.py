# Agent의 Raw Response를 AgentResponse 형식으로 변환

import re
from typing import Any, List

from orchestrator.schemas import AgentResponse

_SOURCE_SEP = "||"  # Streamlit: "제목||URL" 형식


def _doc_metadata(doc: Any) -> dict:
    if hasattr(doc, "metadata"):
        return dict(getattr(doc, "metadata") or {})
    if isinstance(doc, dict):
        return dict(doc.get("metadata") or doc)
    return {}


def _unique_str_list(items: List[str]) -> List[str]:
    return list(dict.fromkeys(item for item in items if item))


def _link_source(label: str, url: str | None = None) -> str:
    label = (label or "").strip()
    url = (url or "").strip()
    if url:
        return f"{label or url}{_SOURCE_SEP}{url}"
    return label


def _unique_stock_sources(sources: List[dict]) -> List[dict]:
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


def _strip_stock_references(answer: str) -> str:
    marker = "\n## 참고자료"
    return answer.split(marker, 1)[0].strip() if marker in answer else answer


def legal_raw_to_agent_response(raw: Any) -> AgentResponse:
    if isinstance(raw, Exception):
        return AgentResponse(
            agent_name = "Legal Agent",
            answer = f"오류: {raw}",
            sources = [],
        )
    if not isinstance(raw, dict):
        return AgentResponse(
            agent_name = "Legal Agent",
            answer = "답변을 가져올 수 없습니다.",
            sources = [],
        )
    
    answer_output = raw.get("answer")
    if answer_output is None:
        return AgentResponse(
            agent_name = "Legal Agent",
            answer = raw.get("error_message") or "답변이 생성되지 않았습니다.",
            sources = [],
        )

    answer = (getattr(answer_output, "answer", None) or (answer_output.get("answer") if isinstance(answer_output, dict) else "") or "").strip()
    risk = (getattr(answer_output, "risk_summary", None) or (answer_output.get("risk_summary") if isinstance(answer_output, dict) else "") or "").strip()
    if risk and risk not in answer:
        answer = f"{answer}\n\n[리스크 요약]\n{risk}"

    cited = getattr(answer_output, "source", None) or (answer_output.get("source") if isinstance(answer_output, dict) else []) or []
    cited_list = cited if isinstance(cited, list) else ([cited] if cited else [])
    sources = [str(s) for s in cited_list if str(s).strip()]
    if not sources:
        reranked_contexts = raw.get("reranked_contexts", [])
        if reranked_contexts:
            sources = [str(context.source) for context in reranked_contexts]

    return AgentResponse(agent_name = "Legal Agent", answer = answer, sources = sources)


def news_raw_to_agent_response(raw: Any) -> AgentResponse:
    if isinstance(raw, Exception):
        return AgentResponse(agent_name = "News Agent", answer = f"오류: {raw}", sources = [])
    try:
        answer = raw.get("final_answer") or raw.get("internal_answer") or "답변이 생성되지 않았습니다."
        sources: List[str] = []

        for doc in raw.get("internal_docs") or []:
            meta = _doc_metadata(doc)
            title, press, date, url = meta.get("title", ""), meta.get("press", ""), meta.get("date", ""), meta.get("url", "")
            if url:
                label = title or url
                if press or date:
                    label = f"{label} ({press} | {date})".strip().rstrip(" ()|")
                sources.append(_link_source(label, url))
            elif title:
                sources.append(f"{title} ({press} | {date})".strip().rstrip(" ()|"))

        for doc in raw.get("external_docs") or []:
            if not isinstance(doc, dict):
                continue
            url, title = doc.get("url", ""), doc.get("title", "")
            if url:
                sources.append(_link_source(title or url, url))
            elif title:
                sources.append(title)

        sources = _unique_str_list(sources)
    except Exception:
        answer, sources = str(raw), []

    return AgentResponse(agent_name = "News Agent", answer = answer, sources = sources)


def report_raw_to_agent_response(raw: Any) -> AgentResponse:
    if isinstance(raw, Exception):
        return AgentResponse(agent_name = "Report Agent", answer = f"오류: {raw}", sources = [])
    try:
        answer = raw.get("report_text") or "보고서 생성에 실패했습니다."
        meta_lines: List[str] = []
        for key, label in [("now_period", "당기"), ("ref_period", "비교 기간"), ("unit", "단위")]:
            val = raw.get(key)
            if val and key == "ref_period":
                meta_lines.append(f"{label}: {val} ({raw.get('compare')})")
            elif val:
                meta_lines.append(f"{label}: {val}")
        if meta_lines:
            answer = "\n".join(meta_lines) + "\n\n" + answer
        warnings = raw.get("warnings") or []
        if warnings:
            answer += "\n\n[경고]\n" + "\n".join(f"- {w}" for w in warnings)

        sources = []
        for key in ("source_pdf", "effective_pdf"):
            path = raw.get(key)
            if path and path not in sources:
                sources.append(str(path))
    except Exception:
        answer, sources = str(raw), []

    return AgentResponse(agent_name = "Report Agent", answer = answer, sources = sources)


def stock_raw_to_agent_response(raw: Any) -> AgentResponse:
    if isinstance(raw, Exception):
        return AgentResponse(agent_name = "Stock Agent", answer = f"오류: {raw}", sources = [])
    try:
        answer = _strip_stock_references(raw.get("final_report") or "최종 결론 도출에 실패했습니다.")
        sources: List[str] = []
        for source in _unique_stock_sources(raw.get("sources", [])):
            if source.get("source_type") == "news" and source.get("url"):
                sources.append(_link_source(source.get("title") or source["url"], source["url"]))
            elif source.get("source_type") == "filing":
                label = f"{source.get('form', '')} ({source.get('filed_date', '')})".strip()
                if label and label != "()":
                    sources.append(label)
        sources = _unique_str_list(sources)
    except Exception:
        answer, sources = str(raw), []

    return AgentResponse(agent_name = "Stock Agent", answer = answer, sources = sources)


def trend_raw_to_agent_response(raw: Any) -> AgentResponse:
    if isinstance(raw, Exception):
        return AgentResponse(agent_name = "Trend Agent", answer = f"오류: {raw}", sources = [])
    try:
        answer = re.sub(r"\n*\[소요시간\][^\n]*", "", raw.get("answer") or "(답변 없음)").strip()
        sources: List[str] = []
        for doc in raw.get("retrieved_docs") or []:
            meta = _doc_metadata(doc)
            url = meta.get("url", "")
            label = " | ".join(p for p in [meta.get("date"), meta.get("section"), meta.get("item")] if p)
            if url:
                sources.append(_link_source(label or url, url))
            elif label:
                sources.append(label)
        sources = _unique_str_list(sources)
    except Exception:
        answer, sources = str(raw), []

    return AgentResponse(agent_name = "Trend Agent", answer = answer, sources = sources)

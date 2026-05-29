from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from legal_src.Agent.schemas import AnswerOutput


def _format_source_rmd(index: int, source: str) -> str:
    source = source.strip()
    if source.startswith(("http://", "https://")):
        return f"{index}. [{source}]({source})"
    return f"{index}. {source}"


def _split_answer_body(answer_text: str) -> str:
    main, _, _ = answer_text.partition("\n## 참고자료")
    return main.strip() or answer_text.strip()


def _format_references_rmd(sources: list[str], answer_text: str) -> str:
    cleaned = [s.strip() for s in sources if s and s.strip()]
    if cleaned:
        return "\n".join(_format_source_rmd(i, src) for i, src in enumerate(cleaned, 1))

    _, _, refs = answer_text.partition("\n## 참고자료")
    return refs.strip() or "_출처 없음_"


def build_legal_final_report_rmd(
    *,
    query: str | None,
    document_path: str | None,
    answer: AnswerOutput,
    generated_at: str | None = None,
) -> str:
    """Legal Agent 최종 답변과 출처를 R Markdown 문서로 조합"""
    generated_at = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = "Legal Agent — Final Response"

    yaml_header = yaml.safe_dump(
        {
            "title": title,
            "date": generated_at,
            "lang": "ko-KR",
            "query": query or "",
            "document_path": document_path or "",
            "input_type": answer.input_type,
            "confidence_score": answer.confidence_score,
            "output": {
                "html_document": {
                    "toc": True,
                    "toc_float": True,
                }
            },
        },
        allow_unicode = True,
        sort_keys = False,
    ).strip()

    body = _split_answer_body(answer.answer)
    references = _format_references_rmd(answer.source, answer.answer)

    sections = [
        "---",
        yaml_header,
        "---",
        "",
        f"# {title}",
        "",
        f"**Generated At:** {generated_at}  ",
    ]
    if query:
        sections.append(f"**Query:** {query}  ")
    if document_path:
        sections.append(f"**Document:** `{document_path}`  ")
    sections.extend(
        [
            "",
            "---",
            "",
            "## 답변",
            "",
            body,
            "",
            "## 참고자료",
            "",
            references,
        ]
    )

    if answer.risk_summary and answer.risk_summary.strip():
        sections.extend(["", "## 리스크 요약", "", answer.risk_summary.strip()])

    return "\n".join(sections).rstrip() + "\n"


def save_legal_final_report_rmd(
    *,
    query: str | None,
    document_path: str | None,
    answer: AnswerOutput,
    log_run_dir: Path | str,
    filename: str = "final_response.rmd",
) -> Path:
    content = build_legal_final_report_rmd(
        query = query,
        document_path = document_path,
        answer = answer,
    )
    output_path = Path(log_run_dir) / filename
    output_path.write_text(content, encoding = "utf-8")
    return output_path

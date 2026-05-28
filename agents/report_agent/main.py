from __future__ import annotations

import logging
import os
import sys

_KANANA_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_REPORT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _KANANA_ROOT)
sys.path.insert(0, _REPORT_ROOT)

from typing import Literal

from nodes import analyze_pdf
from logger_setting import configure_report_logging
from router import RouterAgent

CompareMode = Literal["QoQ", "YoY"]

_router_agent: RouterAgent | None = None


def _get_router_agent() -> RouterAgent:
    global _router_agent
    if _router_agent is None:
        _router_agent = RouterAgent()
    return _router_agent


async def report_agent_main(
    pdf_path: str,
    task: str = "",
    compare: CompareMode = "YoY",
    top_k: int = 5,
    use_reasoning: bool = True,
    slice_financial_statement: bool = True,
) -> dict:
    """상위 오케스트레이터가 in-process로 호출하는 진입점."""
    log_run_dir = configure_report_logging(new_folder=True)
    if log_run_dir is not None:
        logging.info("report_agent 로그 디렉터리: %s", log_run_dir)
    work_dir = os.path.dirname(os.path.abspath(pdf_path))

    if task:
        result = _get_router_agent().route(
            task=task,
            pdf_path=pdf_path,
            compare=compare,
            top_k=int(top_k),
            use_reasoning=bool(use_reasoning),
            slice_financial_statement=bool(slice_financial_statement),
            work_dir=work_dir,
        )
    else:
        result = analyze_pdf(
            pdf_path=pdf_path,
            compare=compare,
            top_k=int(top_k),
            use_reasoning=bool(use_reasoning),
            slice_financial_statement=bool(slice_financial_statement),
            work_dir=work_dir,
        )

    return result.to_dict()

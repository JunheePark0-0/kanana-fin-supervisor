"""질문·답변 세션 로그 (JSONL, 한 줄 = 한 턴)."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, Optional


def append_qa_log(
    path: str,
    question: str,
    answer: str,
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {
        "ts": datetime.datetime.now().isoformat(),
        "question": question,
        "answer": answer,
    }
    if extra:
        record["extra"] = extra
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

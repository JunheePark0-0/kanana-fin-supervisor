import datetime
import re
from typing import Optional
from urllib.parse import urlparse

import pandas as pd


def to_list(raw) -> list:
    if pd.isna(raw) or str(raw).strip() in ("", "nan"):
        return []
    return list(dict.fromkeys(x.strip() for x in str(raw).split(",") if x.strip()))


def to_date_int(raw) -> Optional[int]:
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def resolve_date_hint(hint, today: datetime.datetime):
    if not hint:
        return None, None
    hint = str(hint).replace(" ", "").strip()
    if hint in ("최근", "요즘", "지금", "현재", "최신"):
        year_start = today.replace(month=1, day=1)
        return year_start.strftime("%Y%m%d"), today.strftime("%Y%m%d")
    if re.match(r"^\d{8}$", hint):
        return hint, hint
    if re.match(r"^\d{4}-\d{2}-\d{2}$", hint):
        d = hint.replace("-", "")
        return d, d

    m = re.match(r"최근(\d+)일", hint)
    if m:
        n = int(m.group(1))
        start = today - datetime.timedelta(days=n)
        return start.strftime("%Y%m%d"), today.strftime("%Y%m%d")

    m = re.match(r"최근(\d+)개?월", hint)
    if m:
        n = int(m.group(1))
        start = today - datetime.timedelta(days=n * 30)
        return start.strftime("%Y%m%d"), today.strftime("%Y%m%d")

    m = re.match(r"(\d)분기", hint)
    if m:
        q = int(m.group(1))
        year = today.year
        q_start = datetime.datetime(year, (q - 1) * 3 + 1, 1)
        q_end_month = q * 3
        q_end_day = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][q_end_month - 1]
        q_end = datetime.datetime(year, q_end_month, q_end_day)
        return q_start.strftime("%Y%m%d"), q_end.strftime("%Y%m%d")

    mapping = {
        "오늘": (today, today),
        "어제": (today - datetime.timedelta(days=1), today - datetime.timedelta(days=1)),
        "그제": (today - datetime.timedelta(days=2), today - datetime.timedelta(days=2)),
        "이번주": (today - datetime.timedelta(days=today.weekday()), today),
        "지난주": (
            today - datetime.timedelta(days=today.weekday() + 7),
            today - datetime.timedelta(days=today.weekday() + 1),
        ),
        "한달": (today - datetime.timedelta(days=30), today),
        "이번달": (today.replace(day=1), today),
        "지난달": (
            (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1),
            today.replace(day=1) - datetime.timedelta(days=1),
        ),
        "올해": (today.replace(month=1, day=1), today),
        "작년": (
            today.replace(year=today.year - 1, month=1, day=1),
            today.replace(year=today.year - 1, month=12, day=31),
        ),
    }
    if hint in mapping:
        s, e = mapping[hint]
        return s.strftime("%Y%m%d"), e.strftime("%Y%m%d")
    return None, None


def clean_fake_urls(text, valid_urls):
    pattern = r"\[(\d번 문서)\]\((https?://[^\)]+)\)"

    def replace(m):
        label, url = m.group(1), m.group(2)
        if any(url in v for v in valid_urls):
            return m.group(0)
        return label

    return re.sub(pattern, replace, text)


def clean_report_phrases(text: str) -> str:
    patterns = [
        r"\d{4}년 \d{1,2}월 \d{1,2}일에 보도된 기사에 따르면[,.]?\s*",
        r"\d{4}년 \d{1,2}월 \d{1,2}일에 보도된 기사를 토대로\s*",
        r"\d{4}년 \d{1,2}월 \d{1,2}일 기준으로\s*",
        r"\d{4}년 \d{1,2}월 \d{1,2}일에 보도된 내용에 따른 것입니다[.]?\s*",
        r"\d{4}년 \d{1,2}월 \d{1,2}일 .{0,10}에 보도된 [^\n]{0,30}에 따르면[,.]?\s*",
        r"에 보도된 기사에 따르면[,.]?\s*",
        r"에 보도된 내용에 따르면[,.]?\s*",
        r"\d{4}년 \d{1,2}월 \d{1,2}일에 보도된 기사로서[,.]?\s*",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text)
    return text


def extract_domain(url: str) -> str:
    if not url:
        return ""
    return urlparse(url).netloc.replace("www.", "")


def score_source_reliability(url: str, content: str = "") -> dict:
    domain = extract_domain(url)
    if any(trusted in domain for trusted in ("hankyung.com", "mk.co.kr", "yna.co.kr", ".go.kr", ".or.kr")):
        return {"score": 1.0, "label": "공식 보도 및 기관 자료"}
    if any(x in domain for x in ("tistory", "blog.naver", "blogspot", "naver.com")):
        return {"score": 0.3, "label": "일부 블로그 및 커뮤니티 의견"}
    return {"score": 0.5, "label": "미확인 외부 출처"}

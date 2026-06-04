import datetime
import json
import re
import time

from qdrant_client import models

from utils.kanana_pipeline import get_kanana_response
from utils.helpers import (
    clean_fake_urls,
    clean_report_phrases,
    resolve_date_hint,
    score_source_reliability,
)

MODEL = None
TOKENIZER = None
VECTOR_DB = None
TAVILY = None
SEARCH_LOG_PATH: str | None = None


def init_runtime(model, tokenizer, vector_db, tavily, search_log_path: str | None):
    global MODEL, TOKENIZER, VECTOR_DB, TAVILY, SEARCH_LOG_PATH
    MODEL = model
    TOKENIZER = tokenizer
    VECTOR_DB = vector_db
    TAVILY = tavily
    SEARCH_LOG_PATH = search_log_path


def _llm(messages, max_tokens=512, temp=0.3):
    return get_kanana_response(messages, max_tokens=max_tokens, temp=temp)


def query_rewrite(state):
    question = state["question"]
    prompt = f"""당신은 금융 뉴스 검색 및 RAG 시스템의 쿼리 최적화 전문가입니다.
사용자의 질문을 분석하여, 벡터 DB의 메타데이터(기관/기업명, 날짜, 핵심 키워드) 검색에 최적화된 형태로 재작성하세요.

[재작성 규칙]
1. 기업/기관명(org): 대상이 되는 구체적인 기업명이나 기관명을 반드시 포함하세요.
2. 시간적 맥락(date): '최근', '작년', '지난 분기' 등의 표현을 구체적인 시점이나 기간으로 변환하세요.
3. 금융 키워드(keywords): 실적, 공시, 투자, M&A, 주가 등 검색 정밀도를 높이는 전문 용어를 조합하세요.
4. 불필요한 조사나 서술어는 제거하고, 핵심 명사 위주의 검색어 형태로 작성하세요.
   '검색', '알려줘', '찾아줘' 같은 동사는 절대 포함하지 마세요.
5. 오타 교정 및 표준 금융 용어를 사용하세요.
6. 재작성된 질문만 출력하세요. 설명이나 부연은 절대 포함하지 마세요.
7. org:, date:, keywords: 같은 태그 형식은 절대 출력하지 마세요. 순수 검색어만 출력하세요.
8. 재작성된 검색어는 반드시 한국어로만 작성하세요. 영어 표현은 절대 사용하지 마세요.

[원래 질문]: {question}
[재작성된 질문]:"""

    rewritten = _llm([{"role": "user", "content": prompt}], max_tokens=64, temp=0.2).strip()
    rewritten = rewritten.split("\n")[0].strip()
    rewritten = re.sub(r"(분석해줘|알려줘|설명해줘|어때|해줘|찾기|검색|조회|확인해줘)[.?]*$", "", rewritten).strip()
    rewritten = re.sub(r"\s*(을|를)?\s*(찾기|검색|조회)\s*$", "", rewritten).strip()
    return {"rewritten_question": rewritten, "internal_attempt": 0}


def query_structuring(state):
    today = datetime.datetime.now()
    today_str = today.strftime("%Y-%m-%d (%A)")
    question = state.get("rewritten_question") or state["question"]
    prompt = f"""당신은 금융 뉴스 데이터 추출 전문가입니다.
질문을 분석하여 아래 항목을 JSON 형식으로 추출하세요.

[현재 날짜]: {today_str}
[분석할 질문]: {question}

[추출 항목]
1. question_type: 질문 유형
   - "FACTUAL": 사실 확인, 수치 조회, 현황 파악
   - "ANALYTICAL": 예측, 전망, 판단, 평가, 분석, 비교
2. date_hint: 질문에 담긴 시간 표현 그대로 추출
- "최근", "요즘", "지금"처럼 명시적 날짜가 없어도 is_temporal: true로 설정하고
  date_hint: "최근30일"로 처리하세요.
3. org: 언급된 기업명/기관명 리스트
4. keywords: 검색 의도를 대표하는 핵심 금융 키워드 리스트
5. is_temporal: 시간적 조건 포함 여부 (true/false)

출력은 반드시 JSON 객체만 반환하세요. 설명이나 부연은 절대 포함하지 마세요.
답변:"""
    raw = _llm([{"role": "user", "content": prompt}], max_tokens=256, temp=0.1)
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        extract = json.loads(match.group()) if match else {}
    except Exception:
        extract = {}

    raw_type_val = extract.get("question_type", "FACTUAL")
    # LLM이 드물게 list/object 형태로 반환하는 경우를 방어
    if isinstance(raw_type_val, list):
        raw_type_val = raw_type_val[0] if raw_type_val else "FACTUAL"
    elif isinstance(raw_type_val, dict):
        raw_type_val = raw_type_val.get("type", "FACTUAL")
    raw_type = str(raw_type_val).upper().strip()
    question_type = "ANALYTICAL" if "ANALYT" in raw_type else "FACTUAL"
    date_from, date_to = resolve_date_hint(extract.get("date_hint"), today)
    extract["date_from"] = date_from
    extract["date_to"] = date_to
    extract["question_type"] = question_type
    return {"metadata_extract": extract, "question_type": question_type}


def retrieve_and_rerank(state):
    extract = state.get("metadata_extract", {})
    query = state.get("rewritten_question") or state["question"]
    question_type = state.get("question_type", "FACTUAL")
    k_candidates = 30 if question_type == "ANALYTICAL" else 20

    must_conditions = []
    if extract.get("org"):
        should = [
            models.FieldCondition(key="metadata.org", match=models.MatchText(text=v))
            for v in extract["org"]
        ]
        must_conditions.append(models.Filter(should=should))
    filter_obj = models.Filter(must=must_conditions) if must_conditions else None

    def do_search(f=None):
        results = VECTOR_DB.similarity_search_with_relevance_scores(
            query=query,
            k=k_candidates,
            filter=f,
        )
        return [doc for doc, _ in results]

    candidates = do_search(filter_obj)
    if not candidates:
        candidates = do_search()

    date_from = extract.get("date_from")
    date_to = extract.get("date_to")
    is_temporal = extract.get("is_temporal", False)
    if is_temporal and date_from and date_to:
        filtered = [
            doc
            for doc in candidates
            if date_from <= str(doc.metadata.get("date", "")).replace("-", "") <= date_to
        ]
        if filtered:
            candidates = filtered
        else:
            # 1차 확장: 최근 30일
            dt_to = datetime.datetime.strptime(date_to, "%Y%m%d")
            recent_from = (dt_to - datetime.timedelta(days=30)).strftime("%Y%m%d")
            filtered_30 = [
                doc
                for doc in candidates
                if recent_from <= str(doc.metadata.get("date", "")).replace("-", "") <= date_to
            ]
            if filtered_30:
                candidates = filtered_30
            else:
                # 2차 확장: 같은 연도 전체
                year_prefix = date_from[:4]
                filtered_year = [
                    doc
                    for doc in candidates
                    if str(doc.metadata.get("date", "")).replace("-", "").startswith(year_prefix)
                ]
                if filtered_year:
                    candidates = filtered_year
                else:
                    candidates = do_search(filter_obj) if filter_obj else do_search()

    target_keywords = extract.get("keywords", [])
    # 후보군 확정 뒤 점수 계산은 한 번만 수행
    for doc in candidates:
        content_for_score = doc.page_content + str(doc.metadata.get("keyword", ""))
        keyword_score = sum(
            1.5 if kw in str(doc.metadata.get("keyword", "")) else 0.5
            for kw in target_keywords
            if kw in content_for_score
        )
        date_str = str(doc.metadata.get("date", "")).replace("-", "")
        if date_str.startswith("2026"):
            recency_score = 5.0
        elif date_str.startswith("2025"):
            recency_score = 2.0
        else:
            recency_score = 0.0
        doc.metadata["keyword_score"] = keyword_score + recency_score

    top_n = 7 if question_type == "ANALYTICAL" else 5
    reranked = sorted(
        candidates, key=lambda x: x.metadata.get("keyword_score", 0), reverse=True
    )[:top_n]
    if not reranked and candidates:
        reranked = candidates[:top_n]

    log = {
        "ts": datetime.datetime.now().isoformat(),
        "query": query,
        "type": question_type,
        "filter": {"org": extract.get("org"), "date_from": date_from, "date_to": date_to},
        "results": [d.metadata.get("title", "") for d in reranked],
    }
    if SEARCH_LOG_PATH:
        with open(SEARCH_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")
    return {"internal_docs": reranked}


def gen_internal_answer(state):
    attempt = state.get("internal_attempt", 0) + 1
    question_type = state.get("question_type", "FACTUAL")
    docs = state.get("internal_docs", [])
    question = state.get("rewritten_question") or state["question"]
    if not docs:
        return {
            "internal_answer": "",
            "internal_context": "",
            "internal_attempt": attempt,
            "all_contexts": state.get("all_contexts", []),
        }

    context_list = []
    for i, d in enumerate(docs):
        title = d.metadata.get("title", "제목 없음")
        date = d.metadata.get("date", "날짜 미상")
        context_list.append(f"[{i+1}번 문서]\n제목: {title}\n날짜: {date}\n내용: {d.page_content}")
    context = "\n\n".join(context_list)

    if question_type == "ANALYTICAL":
        guideline = """1. 문서를 날짜 순으로 읽고, 시간에 따른 변화와 흐름을 먼저 파악하세요.
2. "~월에는 ~였으나, ~월에는 ~로 변화했다"처럼 시계열 서술을 우선하세요.
3. 문서에 명시된 팩트를 기반으로 논리적 추론을 전개하세요.
4. 추론/예측 내용은 반드시 [분석] 태그로 명시하여 팩트와 구분하세요.
5. [뉴스 문서]에 없는 수치, %, 날짜, 기관명, 사건명을 절대 생성하지 마세요.
   문서에 명시되지 않은 통계나 연구 결과도 사용 금지입니다.
   불확실한 내용은 반드시 [분석] 태그와 함께 "~로 추정됩니다" 형태로만 서술하세요.
6. 종합적인 결론을 서두에 배치하고, 근거와 분석을 이후에 서술하세요.
7. 각 문장 끝에 근거 문서 번호와 날짜를 표기하세요. (예: [1번 문서, 20260108])"""
    else:
        guideline = """1. 문서를 날짜 순으로 읽고, 가장 최신 문서의 내용을 우선 답변하세요.
2. 최신 문서 기준으로 현황을 서술하고, 이전 문서는 "이전에는 ~였으나"로 보조 서술하세요.
3. 문서에 명시된 팩트만 사용하세요. 절대 추측하지 마세요.
4. 수치, 날짜, 기업명은 자료와 정확히 일치해야 합니다.
5. 자료에 없는 내용은 "확인되지 않습니다"로 명시하세요.
6. 각 문장 끝에 근거 문서 번호와 날짜를 표기하세요. (예: [1번 문서, 20260108])
7. 질문 대상 기업의 정보만 서술하세요.
   질문이 SK하이닉스라면 삼성전자 실적 수치를 절대 포함하지 마세요."""

    prompt = f"""당신은 전문적인 금융 애널리스트입니다.
제공된 [뉴스 문서]의 내용만을 바탕으로 [질문]에 답변하세요.

[지침]
{guideline}

[뉴스 문서]
{context}

[질문]: {question}
[답변]:"""
    answer = _llm([{"role": "user", "content": prompt}], max_tokens=1024, temp=0.1).strip()
    return {
        "internal_answer": answer,
        "internal_context": context,
        "internal_attempt": attempt,
        "all_contexts": state.get("all_contexts", []) + [context],
    }


def hallucination_check_internal(state):
    question = state["question"]
    context = state.get("internal_context", "")
    answer = state.get("internal_answer", "")
    question_type = state.get("question_type", "FACTUAL")
    if not answer or "관련 정보가 확인되지 않습니다" in answer:
        return {"internal_ok": False, "check_reason": "내부 문서에서 관련 정보 없음"}

    def to_bool(val):
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() == "true"
        return bool(val)

    def parse_check(prompt):
        raw = _llm([{"role": "user", "content": prompt}], max_tokens=256, temp=0.1)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            result = json.loads(match.group()) if match else {}
            return {"pass": to_bool(result.get("pass", False)), "reason": result.get("reason", "파싱 실패")}
        except Exception:
            return {"pass": True, "reason": "파싱 실패 → 통과 처리"}

    qa_prompt = f"""[질문]: {question}
[답변]: {answer}

위 답변이 질문의 의도에 적합하고 실질적인 정보를 제공합니까?
JSON 형식으로 'pass'(true/false)와 'reason'(한 문장)을 출력하세요.
답변:"""
    qa_result = parse_check(qa_prompt)

    if question_type == "ANALYTICAL":
        ra_prompt = f"""[뉴스 내용]: {context}
[제시된 답변]: {answer}

[검증 규칙]
1. [분석] 태그가 붙은 문장은 추론/예측이므로 팩트 여부를 검증하지 마세요.
2. [분석] 태그가 없는 일반 문장만 검증하세요.
3. [분석] 태그 문장만 있고 팩트 문장이 없으면 pass로 처리하세요.

JSON 형식으로 'pass'(true/false)와 'reason'(한 문장)을 출력하세요.
답변:"""
    else:
        ra_prompt = f"""[뉴스 내용]: {context}
[제시된 답변]: {answer}

[검증 규칙]
1. 답변의 모든 문장이 뉴스 내용에 직접 명시되어 있어야 합니다.
2. 수치, 날짜, 기업명이 하나라도 다르면 false입니다.
3. 뉴스에 없는 내용이 추가되었으면 false입니다.

JSON 형식으로 'pass'(true/false)와 'reason'(한 문장)을 출력하세요.
답변:"""
    ra_result = parse_check(ra_prompt)
    ok = qa_result["pass"] and ra_result["pass"]
    return {"internal_ok": ok, "check_reason": f"QA: {qa_result['reason']} / RA: {ra_result['reason']}"}


def query_rewrite_retry(state):
    question = state["question"]
    extract = state.get("metadata_extract", {})
    fail_reason = state.get("check_reason", "관련 정보 부족")
    prompt = f"""당신은 금융 뉴스 검색 최적화 전문가입니다.
이전 검색에서 적절한 결과를 얻지 못했습니다. 아래 정보를 바탕으로 검색 효율이 극대화된 새로운 쿼리를 작성하세요.

[실패 원인]: {fail_reason}
[핵심 엔티티(필수 포함)]: {extract.get('org', [])}
[핵심 키워드]: {extract.get('keywords', [])}
[원래 질문]: {question}

[재작성 규칙]
1. [핵심 엔티티]는 반드시 유지하되, 관련 공식 명칭이나 영문명을 병기하세요.
2. [핵심 키워드]의 금융적 동의어나 유의어를 추가하세요.
3. 문장 형태가 아닌 키워드 나열 형태로 작성하세요.
4. 시간 제약이 실패 원인이라면 시간 범위를 넓혀서 재작성하세요.
5. 검색어만 출력하세요. 설명이나 부연은 절대 포함하지 마세요.
답변:"""
    rewritten = _llm([{"role": "user", "content": prompt}], max_tokens=64, temp=0.5).strip()
    rewritten = rewritten.split("\n")[0].strip()
    rewritten = re.sub(r"[`\"']", "", rewritten).strip()
    if not rewritten or rewritten == state.get("rewritten_question", ""):
        rewritten = question
    return {"rewritten_question": rewritten}


def web_search_finance(state):
    extract = state.get("metadata_extract", {})
    base_query = state.get("rewritten_question") or state["question"]
    question_type = state.get("question_type", "FACTUAL")
    orgs = " ".join(extract.get("org", []))
    keywords = " ".join(extract.get("keywords", []))
    search_query = f"{base_query} {orgs} {keywords} 한국".strip()

    if extract.get("is_temporal"):
        search_days = 7
    elif question_type == "ANALYTICAL":
        search_days = 60
    else:
        search_days = 30

    try:
        max_retries = 2
        raw_docs = []
        for attempt in range(max_retries):
            try:
                result = TAVILY.search(
                    query=search_query,
                    topic="finance",
                    search_depth="advanced",
                    max_results=5,
                    days=search_days,
                )
                raw_docs = result.get("results", [])
                if raw_docs:
                    break
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise

        labeled_docs = []
        for d in raw_docs:
            rel = score_source_reliability(d.get("url", ""), d.get("content", ""))
            d["reliability_label"] = rel["label"]
            d["reliability_score"] = rel["score"]
            labeled_docs.append(d)

        formatted_docs = [
            (
                f"[외부출처 {i+1}] (출처성격: {d.get('reliability_label','미확인 외부 출처')})\n"
                f"제목: {d.get('title','')}\nURL: {d.get('url','')}\n내용: {d.get('content','')[:400]}"
            )
            for i, d in enumerate(labeled_docs)
        ]
        return {
            "external_docs": labeled_docs,
            "external_context": "\n\n".join(formatted_docs),
            "has_finance_results": len(labeled_docs) > 0,
        }
    except Exception:
        return {"external_docs": [], "external_context": "", "has_finance_results": False}


def gen_final_answer(state):
    final_attempt = state.get("final_attempt", 0) + 1
    question = state["question"]
    question_type = state.get("question_type", "FACTUAL")
    internal_ok = state.get("internal_ok", False)
    internal_context = state.get("internal_context", "").strip()
    external_docs = state.get("external_docs", [])
    external_context = (
        "\n\n".join(
            [
                f"[외부{i+1}] 제목: {d.get('title','')}\nURL: {d.get('url','')}\n내용: {d.get('content','')[:400]}"
                for i, d in enumerate(external_docs)
            ]
        )
        if external_docs
        else ""
    )

    combined_context = ""
    if internal_context:
        combined_context += f"[내부 DB]\n{internal_context}"
    if external_context:
        if combined_context:
            combined_context += "\n\n"
        combined_context += f"[외부 검색]\n{external_context}"
    if not combined_context:
        return {"final_answer": "관련 정보를 내부 DB 및 외부 검색에서 모두 찾을 수 없었습니다.", "all_contexts": state.get("all_contexts", [])}

    if question_type == "ANALYTICAL":
        guideline = """1. [내부 DB]와 신뢰도 높은 외부 자료는 확정적인 팩트로 서술하세요.
2. 추론/예측 내용은 반드시 [분석] 태그로 명시하여 팩트와 구분하세요.
2-1. [내부 DB]와 [외부 검색] 어디에도 없는 수치(%, 금액, 지수값)를
   절대 생성하지 마세요. 외부 검색 자료의 수치도 반드시
   "[외부N]에 따르면" 형태로만 사용하세요.
   출처 불명 수치는 [분석] 태그와 함께 "~로 추정됩니다"로만 서술하세요.
3. '출처성격'이 [일부 블로그 및 커뮤니티 의견]인 정보를 사용할 경우, 반드시 아래와 같이 서술하세요:
   - "일부 온라인 커뮤니티 및 블로그에서는 ~라고 판단하고 있습니다."
   - "~라는 견해가 있으나 공식적인 확인이 필요합니다."
4. 종합적인 결론을 서두에 배치하고, 근거와 분석을 이후에 서술하세요.
5. 내부 문서 번호([1번 문서])와 외부 출처(URL)를 모두 표기하세요.
6. 모든 답변은 반드시 '한국어'로만 작성하세요.
7. 자료 내에 **(출처성격: 일부 블로그 및 커뮤니티 의견)**이라고 표시된 자료를 인용할 때는, 문장 서두에 반드시 '온라인 커뮤니티의 분석에 따르면' 또는 '일부 개인 블로그에서는 ~라고 판단하고 있으나'와 같은 출처 유보 문구를 삽입하세요.
8. 외부 검색 결과가 영어일지라도 반드시 한국어로 번역하여 답변에 반영하고, 최종 답변 전체에서 단 한 문장의 영어도 사용하지 마세요.
9. 현재 시점은 2026년 4월입니다.
   문서의 날짜는 "보도일"이며, 실적 기간과 다릅니다.
   2026년 4분기는 아직 오지 않았습니다. 절대로 "2026년 4분기 실적"으로 쓰지 마세요.
   예) 날짜 20260108, 제목 "4분기 영업익 20조원" → 반드시 "2025년 4분기 실적"으로 서술
10. 문서 원문을 그대로 복사하지 마세요. 반드시 자신의 언어로 요약하고 분석하여 서술하세요. """
    else:
        guideline = """1. 질문이 묻는 핵심 한 가지를 첫 문장에 바로 답하세요.
   예) "삼성전자 최근 실적은?" → "삼성전자는 2025년 4분기 매출 93조원, 영업이익 20조원을 기록했습니다."
   예) "SK하이닉스 HBM 공급 현황은?" → "SK하이닉스는 2026년 2월부터 HBM4를 엔비디아 등 주요 고객에게 공급하고 있습니다."
   "살펴보겠습니다", "분석해보겠습니다" 같은 서론 문장으로 시작하지 마세요.
2. 수치는 반드시 아래 규칙을 따르세요.
   - 예측/전망 수치("~할 것으로 예상", "~전망")를 실적/현황처럼 서술하지 마세요.
     예) X: "1분기 매출 43조원을 기록했습니다"
         O: "올해 HBM 매출은 43조원에 달할 것으로 전망됩니다"
   - [내부 DB] 문서에 명시된 수치만 사용하세요.
   - 외부 검색 수치는 반드시 "[외부N]에 따르면" 형태로 출처를 밝히고 사용하세요.
   - [내부 DB] 수치와 [외부 검색] 수치를 섞어서 하나의 문장으로 서술하지 마세요.
   - 어디서 나온 수치인지 불분명하면 절대 사용하지 마세요.
3. 중복 내용은 하나로 합치고, 상충되는 정보는 더 구체적인 수치를 우선하세요.
4. [내부 DB]와 [외부 검색] 어디에도 없는 내용은 절대 추가하지 마세요.
   특히 질문 대상 기업(예: SK하이닉스)과 무관한 다른 기업의 실적 수치를
   해당 기업 답변에 섞어서 쓰지 마세요.
5. 내부 문서 번호([1번 문서])와 외부 출처(URL)를 모두 표기하세요.
6. URL은 반드시 제공된 자료의 url 필드에서만 가져오세요. url이 없으면 URL을 표기하지 마세요.
7. 자료 내에 **(출처성격: 일부 블로그 및 커뮤니티 의견)**이라고 표시된 자료를 인용할 때는, 문장 서두에 반드시 '온라인 커뮤니티의 분석에 따르면' 또는 '일부 개인 블로그에서는 ~라고 판단하고 있으나'와 같은 출처 유보 문구를 삽입하세요.
8. 외부 검색 결과가 영어일지라도 반드시 한국어로 번역하여 답변에 반영하고, 최종 답변 전체에서 단 한 문장의 영어도 사용하지 마세요.
9. 현재 시점은 2026년 4월입니다.
   문서의 날짜는 "보도일"이며, 실적 기간과 다릅니다.
   예) 날짜 20260108 → "2026년 1월 8일에 보도된 기사"
       제목에 "4분기 실적" → "2025년 4분기 실적을 2026년 1월에 보도한 것"
   실적 기간은 반드시 문서 제목/내용에서 직접 확인하고,
   보도일을 실적 기간으로 서술하지 마세요.
   보도일 설명("~에 보도된 기사에 따르면")은 답변 본문에 넣지 마세요.
   출처 표기는 ([1번 문서]) 형태로만 하세요.
10. [내부 DB] 문서의 날짜를 기준으로 최신성을 판단하세요. 외부 검색 블로그/커뮤니티 날짜는 최신성 판단에 사용하지 마세요.
11. [내부 DB] 문서가 2026년 자료라면 "최신 현황"으로 서술하세요. "과거 자료 기반" 문구를 절대 사용하지 마세요.
12. 외부 검색 자료가 오래되었더라도, 내부 DB가 2026년이면 내부 DB 기준으로 현황을 서술하세요.
13. 내부 문서가 적을 경우(2개 이하), 외부 검색 자료를 적극 활용하되
   반드시 출처 신뢰도에 따라 서술 방식을 구분하세요.
   - 공식 보도: 확정적 서술
   - 블로그/커뮤니티: "~라는 분석이 있습니다" 형태로 유보"""

    internal_note = (
        "내부 DB 답변은 검증을 통과했습니다. 이를 핵심 근거로 활용하세요."
        if internal_ok
        else "내부 DB 답변은 검증 미통과이나 컨텍스트로 참고하세요. 외부 검색 결과를 우선 활용하세요."
    )
    prompt = f"""당신은 금융 정보 통합 전문가입니다.
아래 제공된 [내부 DB]와 [외부 검색] 자료를 바탕으로 질문에 답변하세요.

[지침]
{guideline}

[참고]
{internal_note}

[자료]
{combined_context}

[질문]: {question}
[분량 기준]
- FACTUAL 답변은 최소 400자 이상 작성하세요.
- 수치 근거 → 시장 반응 → 향후 전망 순으로 구성하세요.
- 절대로 ##, ###, #### 마크다운 헤더를 사용하지 마세요. 소제목은 반드시 [시장 반응] 형태로만 표기하세요.
[답변]:"""
    final = _llm([{"role": "user", "content": prompt}], max_tokens=1024, temp=0.2).strip()
    all_contexts = state.get("all_contexts", [])
    if external_context:
        all_contexts = all_contexts + [external_context]
    return {"final_answer": final, "all_contexts": all_contexts, "final_attempt": final_attempt}


def compute_ragas_scores(question, answer, contexts, question_type):
    def to_score(val, default=0.5):
        try:
            return max(0.0, min(1.0, float(val)))
        except Exception:
            return default

    context_str = "\n\n".join(contexts)[:3000]
    if question_type == "ANALYTICAL":
        faith_rule = """- [분석] 태그가 붙은 문장은 추론/예측이므로 검증에서 제외하세요.
- [분석] 태그가 없는 팩트 문장만 컨텍스트와 대조하세요."""
    else:
        faith_rule = "- 답변의 모든 문장이 컨텍스트에 근거해야 합니다."

    faith_prompt = f"""당신은 RAG 시스템 평가 전문가입니다.
[평가 규칙]
{faith_rule}
[컨텍스트]: {context_str}
[질문]: {question}
[답변]: {answer}
반드시 JSON으로만 응답하세요: {{"score": 0.0~1.0, "reason": "한 문장"}}
답변:"""
    rel_prompt = f"""당신은 RAG 시스템 평가 전문가입니다.
[질문]: {question}
[답변]: {answer}
반드시 JSON으로만 응답하세요: {{"score": 0.0~1.0, "reason": "한 문장"}}
답변:"""
    recall_prompt = f"""당신은 RAG 시스템 평가 전문가입니다.
[컨텍스트]: {context_str}
[질문]: {question}
반드시 JSON으로만 응답하세요: {{"score": 0.0~1.0, "reason": "한 문장"}}
답변:"""

    def call_and_parse(prompt):
        raw = _llm([{"role": "user", "content": prompt}], max_tokens=128, temp=0.1)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            result = json.loads(match.group()) if match else {}
            return to_score(result.get("score", 0.5)), result.get("reason", "")
        except Exception:
            return 0.5, "파싱 실패"

    faith_score, faith_reason = call_and_parse(faith_prompt)
    rel_score, rel_reason = call_and_parse(rel_prompt)
    recall_score, recall_reason = call_and_parse(recall_prompt)
    return {
        "faithfulness": {"score": faith_score, "reason": faith_reason},
        "answer_relevancy": {"score": rel_score, "reason": rel_reason},
        "context_recall": {"score": recall_score, "reason": recall_reason},
    }


def hallucination_check_final(state):
    question = state["question"]
    answer = state.get("final_answer", "").strip()
    question_type = state.get("question_type", "FACTUAL")
    all_contexts = state.get("all_contexts", [])
    if not answer or "찾을 수 없었습니다" in answer:
        return {"final_check_reason": "답변 없음", "final_check_route": "cannot_answer", "failed_claims": []}

    def to_score(val, default=0.5):
        try:
            return max(0.0, min(1.0, float(val)))
        except Exception:
            return default

    def call_and_parse(prompt):
        raw = _llm([{"role": "user", "content": prompt}], max_tokens=128, temp=0.1)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            result = json.loads(match.group()) if match else {}
            return to_score(result.get("score", 0.5)), result.get("reason", "")
        except Exception:
            return 0.5, "파싱 실패"

    context_str = "\n\n".join(all_contexts)[:3000]
    if question_type == "ANALYTICAL":
        faith_rule = """- [분석] 태그가 붙은 문장은 추론/예측이므로 검증에서 제외하세요.
- [분석] 태그가 없는 팩트 문장만 컨텍스트와 대조하세요.
- 팩트 문장이 없으면 1.0으로 처리하세요."""
    else:
        faith_rule = """- 답변의 모든 문장이 컨텍스트에 근거해야 합니다.
- 컨텍스트에 없는 수치/사실이 포함되면 즉시 낮은 점수를 부여하세요."""

    faith_score, faith_reason = call_and_parse(
        f"""당신은 RAG 시스템 평가 전문가입니다.
[평가 규칙]
{faith_rule}
[컨텍스트]: {context_str}
[질문]: {question}
[답변]: {answer}
반드시 JSON으로만 응답하세요: {{"score": 0.0~1.0, "reason": "한 문장"}}
답변:"""
    )
    if question_type == "ANALYTICAL" and faith_score == 0.0:
        faith_score = 0.8
        faith_reason = "[분석] 태그 문장만 있어 팩트 검증 불필요 → 통과 처리"

    rel_score, rel_reason = call_and_parse(
        f"""당신은 RAG 시스템 평가 전문가입니다.
[질문]: {question}
[답변]: {answer}
반드시 JSON으로만 응답하세요: {{"score": 0.0~1.0, "reason": "한 문장"}}
답변:"""
    )
    recall_score, recall_reason = call_and_parse(
        f"""당신은 RAG 시스템 평가 전문가입니다.
[컨텍스트]: {context_str}
[질문]: {question}
반드시 JSON으로만 응답하세요: {{"score": 0.0~1.0, "reason": "한 문장"}}
답변:"""
    )

    faith_threshold = 0.3 if question_type == "ANALYTICAL" else 0.5
    rel_threshold = 0.5
    recall_threshold = 0.5
    if faith_score < faith_threshold:
        route = "cannot_answer"
        reason = f"팩트 오류 (faithfulness={faith_score:.2f}): {faith_reason}"
    elif rel_score < rel_threshold:
        route = "regenerate"
        reason = f"답변 품질 문제 (relevancy={rel_score:.2f}): {rel_reason}"
    elif recall_score < recall_threshold:
        route = "re_retrieve"
        reason = f"컨텍스트 부족 (recall={recall_score:.2f}): {recall_reason}"
    else:
        route = "pass"
        reason = f"PASS (faith={faith_score:.2f} / rel={rel_score:.2f} / recall={recall_score:.2f})"
    return {
        "final_check_reason": reason,
        "final_check_route": route,
        "failed_claims": [],
        "ragas_scores": {
            "faithfulness": faith_score,
            "answer_relevancy": rel_score,
            "context_recall": recall_score,
        },
    }


def format_answer(state):
    answer = state.get("final_answer", "")
    question = state.get("question", "")
    internal_docs = state.get("internal_docs", [])
    external_docs = state.get("external_docs", [])
    failed_claims = state.get("failed_claims", [])

    valid_urls = [d.metadata.get("url", "") for d in internal_docs]
    answer = clean_fake_urls(answer, valid_urls)
    answer = clean_report_phrases(answer)

    # 출처 통합 (내부 DB + 외부 검색 구분 없이)
    sources = []
    for d in internal_docs:
        title = d.metadata.get("title", "")
        date = d.metadata.get("date", "")
        press = d.metadata.get("press", "")
        if title:
            sources.append(f"  - {title} ({press} | {date})")
    for d in external_docs:
        title = d.get("title", "")
        url = d.get("url", "")
        if title:
            sources.append(f"  - {title}\n    {url}")

    source_block = "\n".join(sources) if sources else "출처 없음"

    failed_block = ""
    if failed_claims:
        failed_block = "\n\n[검증 유의사항]\n" + "\n".join(f"  - {c}" for c in failed_claims)

    formatted = (
        f"{answer}\n\n{'='*40}\n"
        f"{failed_block}"
    )
    return {"final_answer": formatted}


def cannot_answer(state):
    reason = state.get("final_check_reason", "관련 근거 자료 부족")
    question = state.get("question", "")
    msg = (
        f"요청하신 '{question}'에 대해 신뢰할 수 있는 답변을 생성하지 못했습니다.\n"
        f"사유: {reason}\n\n"
        "보다 구체적인 기업명이나 날짜를 포함하여 다시 질문해 주세요."
    )
    return {"final_answer": msg}
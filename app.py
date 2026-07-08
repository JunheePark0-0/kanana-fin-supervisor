import html
import streamlit as st
import requests
import os
from pathlib import Path
from datetime import datetime
import json
import re
import tempfile
import markdown as md_lib

from orchestrator.schemas import FinalResponse

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title = "Kanana Agent",
    page_icon = "🤖",
    layout = "centered",
)

# ── 스타일 ───────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── 전체 배경: 밝은 회색 ── */
    .stApp { background-color: #f5f6fa; }
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e4ed;
    }

    /* ── 글자 크기 축소 ── */
    html, body, [class*="css"] { font-size: 13px !important; }
    h1 { font-size: 1.4rem !important; color: #1a1d2e !important; font-weight: 700 !important; }
    h2 { font-size: 1.15rem !important; color: #1a1d2e !important; }
    h3 { font-size: 1rem !important; color: #374151 !important; }
    p, label, .stMarkdown { color: #4b5563 !important; font-size: 0.82rem !important; }

    /* ── 입력창 ── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 7px !important;
        color: #1a1d2e !important;
        font-size: 0.82rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #4f6ef7 !important;
        box-shadow: 0 0 0 2px rgba(79,110,247,0.12) !important;
    }

    /* ── 파일 업로더 ── */
    .stFileUploader > div {
        background: #ffffff !important;
        border: 1px dashed #d1d5db !important;
        border-radius: 7px !important;
        font-size: 0.8rem !important;
    }

    /* ── 버튼 (기본 스타일: 색/모양만 지정, 글자는 각 버튼 코드에서 직접 지정) ── */
    .stButton > button {
        background: #6b7280 !important;
        border: none !important;
        border-radius: 7px !important;
        padding: 0.45rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        width: 100%;
        color: #ffffff !important;
    }
    .stButton > button p,
    .stButton > button span,
    .stButton > button div {
        color: #ffffff !important;
    }

    .stSidebar .stButton > button,
    .stSidebar .stButton > button p,
    .stSidebar .stButton > button span,
    .stSidebar .stButton > button div {
        background: transparent !important;
        color: #4b5563 !important;
    }

    /* ── 응답 박스 ── */
    .response-box {
        background: #ffffff;
        border: 1px solid #e2e4ed;
        border-radius: 9px;
        padding: 1rem 1.2rem;
        color: #1a1d2e;
        font-size: 0.82rem;
        line-height: 1.7;
        white-space: pre-wrap;
        margin-top: 0.4rem;
    }
    .agent-box {
        background: #f9fafb;
        border: 1px solid #e2e4ed;
        border-left: 3px solid #4f6ef7;
        border-radius: 7px;
        padding: 0.85rem 1rem;
        margin-top: 0.6rem;
        color: #1a1d2e;
        font-size: 0.82rem;
        line-height: 1.6;
    }
    .agent-name {
        color: #4f6ef7;
        font-weight: 700;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.4rem;
    }
    .source-tag {
        display: inline-block;
        background: #eef0fb;
        color: #4f6ef7;
        border-radius: 4px;
        padding: 0.1rem 0.45rem;
        font-size: 0.7rem;
        margin: 0.15rem 0.15rem 0 0;
        word-break: break-all;
    }
    a.source-tag {
        text-decoration: none;
    }
    a.source-tag:hover {
        text-decoration: underline;
    }
    .error-box {
        background: #fff5f5;
        border: 1px solid #fecaca;
        border-radius: 7px;
        padding: 0.75rem 1rem;
        color: #dc2626;
        font-size: 0.8rem;
        margin-top: 0.4rem;
    }

    /* ── 히스토리 카드 ── */
    .history-card {
        background: #ffffff;
        border: 1px solid #e2e4ed;
        border-radius: 9px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
    }
    .history-meta { font-size: 0.72rem; color: #4f6ef7; margin-bottom: 0.2rem; }
    .history-query { color: #1a1d2e; font-size: 0.82rem; font-weight: 500; }
    .history-preview {
        color: #9ca3af; font-size: 0.75rem; margin-top: 0.2rem;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }

    /* ── 구분선 ── */
    hr { border-color: #e2e4ed !important; }

    /* ── 사이드바 탭 버튼 간격 ── */
    .stSidebar .stButton > button {
        background: transparent !important;
        color: #4b5563 !important;
        border: 1px solid transparent !important;
        text-align: left !important;
        padding: 0.4rem 0.7rem !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        margin-bottom: 0.1rem;
    }
    .stSidebar .stButton > button:hover {
        background: #f0f2ff !important;
        color: #4f6ef7 !important;
        opacity: 1 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── 상수 ─────────────────────────────────────────────────────
FASTAPI_URL = "http://localhost:8000"
HISTORY_DIR = Path("./kanana_history")
HISTORY_DIR.mkdir(exist_ok = True)

# ── 탭 정의: (이름, 아이콘, target_agent, 필수필드, 선택필드) ──
TABS = [
    ("Orchestrator", "🧠", None,               [],          ["query", "ticker", "file"]),
    ("Legal Agent",  "⚖️",  "Legal Agent",    ["query"],   ["file"]),
    ("News Agent",   "📰", "News Agent",      ["query"],   []),
    ("Report Agent", "📄", "Report Agent",    ["file"],    []),
    ("Stock Agent",  "📈", "Stock Agent",     ["ticker"],  []),
    ("Trend Agent",  "🔍", "Trend Agent",     ["query"],   []),
    ("History",      "🕓", "HISTORY",           [],           []),
]

# ── 세션 상태 ────────────────────────────────────────────────
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "history_detail" not in st.session_state:
    st.session_state.history_detail = None


# ── 헬퍼 함수들 ──────────────────────────────────────────────
def normalize_tilde(text: str) -> str:
    """물결표(~)가 여러 개 연속되어도 항상 1개로 통일 (마크다운 취소선 오작동 방지)"""
    if not text:
        return text
    return re.sub(r"~+", "~", text)

def markdown_to_html(text: str) -> str:
    """마크다운 텍스트(##, **, - 등)를 HTML로 변환"""
    if not text:
        return text
    return md_lib.markdown(text, extensions=["extra"])

def save_history(tab_name, query, ticker, result):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    record = {
        "timestamp": datetime.now().isoformat(),
        "tab": tab_name,
        "query": query,
        "ticker": ticker,
        "summary": result.get("summary", ""),
        "all_answers": result.get("all_answers", []),
    }
    path = HISTORY_DIR / f"{ts}_{tab_name.replace(' ', '_')}.json"
    with open(path, "w", encoding = "utf-8") as f:
        json.dump(record, f, ensure_ascii = False, indent = 2)


def load_history():
    records = []
    for p in sorted(HISTORY_DIR.glob("*.json"), reverse = True):
        try:
            with open(p, encoding="utf-8") as f:
                records.append(json.load(f))
        except Exception:
            pass
    return records


def save_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return None
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="kanana_upload_") as tmp:
        tmp.write(uploaded_file.getvalue())
        return tmp.name


def result_to_final_report(result: dict) -> str:
    """터미널 print(final_report)와 동일한 텍스트 형식."""
    return FinalResponse.model_validate(result)._to_final_report()


def _format_source_tag(source) -> str:
    """'제목||URL' 또는 URL/텍스트 문자열을 출처 태그로 변환."""
    if isinstance(source, dict):
        label = (source.get("label") or "").strip()
        url = (source.get("url") or "").strip()
        s = f"{label}||{url}" if url else label
    else:
        s = str(source).strip()
    if "||" in s:
        label, url = s.split("||", 1)
        label, url = label.strip(), url.strip()
    elif s.startswith(("http://", "https://")):
        label, url = s, s
    else:
        label, url = s, None

    esc_label = html.escape(label or url or "")
    if url:
        esc_url = html.escape(url)
        return (
            f'<a class="source-tag" href="{esc_url}" '
            f'target="_blank" rel="noopener noreferrer">🔗 {esc_label}</a>'
        )
    return f'<span class="source-tag">{esc_label}</span>'


def render_sources(result: dict):
    """에이전트별 출처를 하단에 모아 표시."""
    agents_with_sources = [
        a for a in result.get("all_answers", [])
        if a.get("sources")
    ]
    if not agents_with_sources:
        return

    st.markdown("### 📎 출처")
    for agent in agents_with_sources:
        name = html.escape(str(agent.get("agent_name", "")))
        tags = "".join(_format_source_tag(s) for s in agent["sources"])
        st.markdown(
            f"""
            <div class="agent-box">
                <div class="agent-name">🤖 {name}</div>
                <div style="display:flex; flex-wrap:wrap; gap:0.3rem; margin-top:0.3rem;">{tags}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_response(result: dict):
    summary = normalize_tilde(result.get("summary", "")) 
    summary = markdown_to_html(summary)
    all_answers = result.get("all_answers", [])

    # 요약 박스
    st.markdown(
        f'<div class="response-box">📋 <strong>요약</strong><br><br>{summary}</div>',
        unsafe_allow_html=True,
    )

    # 에이전트별 상세 응답
    if all_answers:
        st.markdown("<br>**에이전트별 상세 응답**", unsafe_allow_html=True)
        for agent in all_answers:
            name = html.escape(str(agent.get("agent_name", "")))
            body = agent.get("answer", "") or "_답변 없음_"
            body = normalize_tilde(body)
            body = markdown_to_html(body)
            st.markdown(
                f"""
                <div class="agent-box">
                    <div class="agent-name">🤖 {name}</div>
                    <div style="white-space: pre-wrap;">{body}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 출처 별도 섹션
    render_sources(result)

def call_api(query, ticker, document_path, target_agent):
    if document_path == "None":
        document_path = None
    print(f"📤 document_path 변환 후: {repr(document_path)}")
    payload = {
        "query": query,
        "ticker": ticker or None,
        "document_path": document_path,
        "target_agent": target_agent,
    }
    response = requests.post(f"{FASTAPI_URL}/ask", json = payload, timeout = 600)
    response.raise_for_status()
    return response.json()


# ── 사이드바 ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**🤖 Kanana**")
    st.markdown("---")
    for i, (name, icon, _, _req, _opt) in enumerate(TABS):
        if st.button(f"{icon}  {name}", key = f"tab_{i}"):
            st.session_state.active_tab = i
            st.session_state.history_detail = None
            st.rerun()
    st.markdown("---")
    st.markdown(
        f'<p style="font-size:0.72rem; color:#9ca3af;">서버: <code style="color:#4f6ef7">{FASTAPI_URL}</code></p>',
        unsafe_allow_html = True,
    )


# ── 메인 ─────────────────────────────────────────────────────
tab_name, tab_icon, target_agent, required_fields, optional_fields = TABS[st.session_state.active_tab]

# ════════════════════════════════════════════════════════
# 히스토리 탭
# ════════════════════════════════════════════════════════
if target_agent == "HISTORY":
    st.title("🕓 History")
    st.markdown("과거 분석 기록을 날짜/시간 순으로 확인합니다.")
    st.markdown("---")
    records = load_history()

    if not records:
        st.markdown(
            '<div class="response-box" style="color:#9ca3af; font-style:italic;">아직 기록이 없습니다.</div>',
            unsafe_allow_html = True,
        )
    elif st.session_state.history_detail is not None:
        record = st.session_state.history_detail
        dt = datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        if st.button("← 목록으로"):
            st.session_state.history_detail = None
            st.rerun()
        st.markdown(f"**{dt}** &nbsp;|&nbsp; `{record['tab']}`", unsafe_allow_html=True)
        st.markdown(f"**질문:** {record['query']}")
        if record.get("ticker"):
            st.markdown(f"**Ticker:** `{record['ticker']}`")
        st.markdown("---")
        render_response(record)
    else:
        from itertools import groupby
        def date_key(r):
            return datetime.fromisoformat(r["timestamp"]).strftime("%Y년 %m월 %d일")
        for date_label, group in groupby(records, key=date_key):
            st.markdown(f"#### 📅 {date_label}")
            for record in group:
                dt_str  = datetime.fromisoformat(record["timestamp"]).strftime("%H:%M:%S")
                preview = (record.get("summary", "")[:80] + "...") if record.get("summary") else ""
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"""
                    <div class="history-card">
                        <div class="history-meta">{dt_str} · {record.get('tab','')}</div>
                        <div class="history-query">{record.get('query','(쿼리 없음)')}</div>
                        <div class="history-preview">{preview}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button("🔍 결과 확인", key=f"detail_{record['timestamp']}"):
                        st.session_state.history_detail = record
                        st.rerun()

# ════════════════════════════════════════════════════════
# 에이전트 탭
# ════════════════════════════════════════════════════════
else:
    st.title(f"{tab_icon} {tab_name}")
    if target_agent is None:
        st.markdown("질문을 입력하면 적절한 에이전트를 자동으로 선택하여 분석합니다.")
    else:
        st.markdown(f"`{target_agent}` 만 실행합니다.")
    st.markdown("---")

    st.markdown("### 📝 입력")

    # ── 탭별 입력 필드 렌더링 ────────────────────────────
    query         = ""
    ticker        = ""
    uploaded_file = None

    all_fields    = required_fields + optional_fields
    needs_query   = "query"  in all_fields
    needs_ticker  = "ticker" in all_fields
    needs_file    = "file"   in all_fields
    opt_ticker    = "ticker" in optional_fields
    opt_file      = "file"   in optional_fields

    tab_key = st.session_state.active_tab  # 탭마다 위젯 key 분리

    if needs_query:
        query = st.text_area(
            "Query (질문)",
            placeholder="예: 엔비디아의 최근 실적과 전망을 분석해줘",
            height=90,
            key=f"query_{tab_key}",
        )

    # ticker & file: 같이 나올 때는 2열, 단독이면 1열
    ticker_label = f"Ticker (종목코드)" + (" (선택)" if opt_ticker else "")
    file_label   = "Document" + (" (선택)" if opt_file else "")

    if needs_ticker and needs_file:
        col1, col2 = st.columns(2)
        with col1:
            ticker = st.text_input(ticker_label, placeholder="예: NVDA", key=f"ticker_{tab_key}")
        with col2:
            uploaded_file = st.file_uploader(file_label, type=["pdf", "txt", "csv", "docx"], key=f"file_{tab_key}")
    elif needs_ticker:
        ticker = st.text_input(ticker_label, placeholder="예: NVDA", key=f"ticker_{tab_key}")
    elif needs_file:
        uploaded_file = st.file_uploader(file_label, type=["pdf", "txt", "csv", "docx"], key=f"file_{tab_key}")

    st.markdown("---")
    st.markdown('<div class="run-btn">', unsafe_allow_html=True)
    run = st.button("🚀 분석 실행", key=f"run_{tab_key}")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 응답 섹션 ────────────────────────────────────────
    st.markdown("### 💬 응답")

    if run:
        errors = []
        if needs_query and not query.strip():
            errors.append("Query를 입력해주세요.")
        if needs_ticker and not opt_ticker and not ticker.strip():
            errors.append("Ticker를 입력해주세요.")
        if needs_file and not opt_file and uploaded_file is None:
            errors.append("문서 파일을 업로드해주세요.")

        if errors:
            for err in errors:
                st.markdown(f'<div class="error-box">⚠️ {err}</div>', unsafe_allow_html=True)
        else:
            with st.spinner("에이전트가 분석 중입니다..."):
                document_path = save_uploaded_file(uploaded_file)
                try:
                    result = call_api(
                        query=query,
                        ticker=ticker.strip() if ticker.strip() else None,
                        document_path=document_path,
                        target_agent=target_agent,
                    )
                    render_response(result)
                    save_history(tab_name, query, ticker.strip() or None, result)

                except requests.exceptions.ConnectionError:
                    st.markdown(
                        f'<div class="error-box">🔌 FastAPI 서버에 연결할 수 없습니다. <code>{FASTAPI_URL}</code></div>',
                        unsafe_allow_html=True,
                    )
                except requests.exceptions.Timeout:
                    st.markdown('<div class="error-box">⏱️ 응답 시간이 초과됐습니다.</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f'<div class="error-box">❌ 오류: {str(e)}</div>', unsafe_allow_html=True)
                finally:
                    if document_path and os.path.exists(document_path):
                        os.unlink(document_path)
    else:
        st.markdown(
            '<div class="response-box" style="color:#9ca3af; font-style:italic;">분석 결과가 여기에 표시됩니다.</div>',
            unsafe_allow_html=True,
        )
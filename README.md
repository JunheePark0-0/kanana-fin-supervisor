# Kanana Agent

**Kanana Agent**는 카카오의 경량 LLM `kanana-1.5-2.1b-instruct`를 핵심 추론 엔진으로 사용하는 **금융·법률 멀티 에이전트 시스템**입니다.
LangGraph 기반의 오케스트레이터가 사용자 질문을 분석하여 적합한 하위 에이전트를 자동으로 선택·호출하고, 각 에이전트의 결과를 통합하여 최종 인사이트를 제공합니다.

---

## 목차

- [시스템 구성 개요](#시스템-구성-개요)
- [사용 모델](#사용-모델)
- [오케스트레이터](#오케스트레이터-orchestrator)
- [하위 에이전트](#하위-에이전트)
- [API 스펙](#api-스펙)
- [사용 예시](#사용-예시)
- [환경 변수 설정](#환경-변수-설정-env)
- [하드웨어 요구사항](#하드웨어-요구사항)
- [실행 가이드](#실행-가이드)
- [프론트엔드 탭 구성](#프론트엔드-탭-구성)
- [프로젝트 구조](#프로젝트-구조)
- [주요 기술 스택](#주요-기술-스택)
- [트러블슈팅](#트러블슈팅)
- [라이선스](#라이선스)

---

## 시스템 구성 개요

```
사용자 (Streamlit UI)
        │
        ▼
  FastAPI 백엔드 (main.py)
        │
        ▼
  Orchestrator (LangGraph)
   ┌────────────────────────────────────┐
   │  Routing → Run Agents → Summarize  │
   └────┬───────────────────────────────┘
        │ 병렬 실행 (asyncio.gather)
   ┌────┴──────────────────────────────────────────┐
   │                                               │
   ▼        ▼         ▼          ▼         ▼
Legal    News      Report     Stock     Trend
Agent    Agent     Agent      Agent     Agent
```

| 구성 요소 | 역할 |
|-----------|------|
| **Streamlit** (`app.py`) | 사용자 인터페이스 (탭별 에이전트 선택, 결과 렌더링, 히스토리) |
| **FastAPI** (`main.py`) | REST API 서버 (`POST /ask`), 비동기 LangGraph 그래프 실행 |
| **Orchestrator** (`orchestrator/`) | 질문 라우팅 → 에이전트 병렬 실행 → 통합 요약 |
| **5개 하위 에이전트** (`agents/`) | 각 도메인 전문 분석 |

---

## 사용 모델

| 모델 | 용도 | 저장 경로 |
|------|------|-----------|
| `kakaocorp/kanana-1.5-2.1b-instruct-2505` | 추론·생성 (전 에이전트 공유) | `./models/Kanana` |
| `BAAI/bge-m3` | 임베딩 (News, Legal, Trend Agent) | `./models/bge-m3` |

---

## 오케스트레이터 (`orchestrator/`)

LangGraph `StateGraph`로 구성된 3단계 워크플로우입니다.

```
START → [Routing] → [Run Agents] → [Summarize] → END
```

### 주요 노드

| 노드 | 설명 |
|------|------|
| **Routing** | 사용자 질문·ticker·문서 첨부 여부를 분석하여 호출할 에이전트 목록을 결정합니다. Kanana LLM의 구조화 출력으로 에이전트를 선택하며, 키워드 기반 하드 제약(Legal/Stock 제한)도 적용합니다. 사용자가 프론트엔드 탭에서 직접 에이전트를 선택한 경우 라우팅을 생략합니다. |
| **Run Agents** | 선택된 에이전트들을 `asyncio.gather`로 **병렬 실행**합니다. ticker 없이 Stock Agent가 선택된 경우, 문서 없이 Report Agent가 선택된 경우 등 사전 조건 불충족 시 해당 에이전트를 스킵하고 안내 메시지를 반환합니다. |
| **Summarize** | 모든 에이전트 응답을 통합하여 Kanana LLM으로 **핵심 요약 + 최종 결론**을 생성합니다. 수석 전략 컨설턴트 역할로 재무·법률·시장 트렌드의 상호작용을 관계 중심적으로 분석합니다. |

### 라우팅 규칙 요약

| 조건 | 선택 에이전트 |
|------|--------------|
| 문서 첨부 + 질문 있음 | Legal Agent |
| 문서 첨부 + 질문 없음 | Report Agent |
| ticker만 입력 | Stock Agent |
| 기업명/인물 언급 | News Agent 필수 포함 |
| 거시경제(금리·환율·업황) 질문 | Trend Agent |
| 법률·계약·소송 키워드 | Legal Agent |
| 아무것도 해당 없음 | News Agent (기본값) |

---

## 하위 에이전트

### 1. Legal Agent (`agents/legal_agent/`)

**역할**: 법률·계약·소송·규제·판례 관련 질의 응답
**데이터 소스**: 로컬 법률 DB (벡터 DB) + Tavily 웹 검색
**임베딩 모델**: BGE-M3

**내부 LangGraph 워크플로우**:

```
input_router → query_rewriter
    │
    ├─ Query_Only ──────────────────→ rag_searcher
    └─ Hybrid ──→ document_parser ──→ issue_extractor → rag_searcher
                                                              │
                                               context_evaluator
                                                    │
                             ENOUGH ←──────────────┤
                               │               NOT_ENOUGH → web_searcher → context_filter
                               │                                              → context_reranker
                               ▼                                              → context_evaluator
                        answer_generator → answer_evaluator
                                                  │
                               ENOUGH ──→ END    NOT_ENOUGH → answer_regenerator ──→ answer_evaluator
```

---

### 2. News Agent (`agents/news_agent/`)

**역할**: 특정 기업·인물·사건에 대한 최신 금융 뉴스 검색 및 요약
**데이터 소스**: Qdrant 벡터 DB (한국 금융 뉴스 코퍼스) + Tavily 웹 검색
**임베딩 모델**: BGE-M3

**내부 LangGraph 워크플로우**:

```
query_rewrite → query_structuring → retrieve_and_rerank → gen_internal_answer
                                                                     │
                                                    hallucination_check_internal
                                                           │
                             retry ←──────────────────────┤
                               │                      to_external ↓
                         query_rewrite_retry        web_search_finance
                               │                          │
                         query_structuring         has_results → gen_final_answer → hallucination_check_final
                                                                                           │
                                                  pass → format_answer → END    regenerate → gen_final_answer
                                                                                re_retrieve → retrieve_and_rerank
                                                  cannot_answer → END
```

---

### 3. Report Agent (`agents/report_agent/`)

**역할**: 첨부된 PDF 재무제표 분석 (포괄손익계산서 등 수치 분석)
**데이터 소스**: 사용자 업로드 PDF
**외부 API**: Upstage Document AI (PDF → 구조화 데이터 파싱)

**내부 LangGraph 워크플로우**:

```
              ┌──────────────────────────┐
              │      RouterAgent          │
              │ (task 유형에 따라 분기)   │
              └────────────┬──────────────┘
                            ▼
node_upstage_parse → node_select_metrics → node_llm_extract
                                                  │
                                       node_merge_and_normalize
                                                  │
                                         node_compute_moves
                                            (CompareMode: YoY / QoQ)
                                                  │
                                       node_optional_reasoning → END
```

---

### 4. Stock Agent (`agents/stock_agent/`)

**역할**: 특정 종목의 최신 공시 데이터 기반 투자 의견(Buy/Sell/Hold) 도출
**데이터 소스**: 공시 정보 실시간 크롤링 (Selenium 활용)

**2단계 파이프라인**:

```
[1단계] 크롤링 (stock_src/Crawling/)
    │  티커 기반 공시 데이터 수집 및 로컬 DB 업데이트
    ▼
[2단계] Multi-Agent Debate (stock_src/Agent/, agent_debate_graph)

   Optimist Agent ──┐
   (낙관론 제시)      │
                     ├─→ 토론 (최대 6턴, 번갈아 발언) ─→ 합의 노드 ─→ END
   Pessimist Agent ──┘                                (최종 투자 리포트 생성)
   (비관론 제시)
```

---

### 5. Trend Agent (`agents/trend_agent/`)

**역할**: 금리·환율·업황 등 거시경제 및 국제 금융시장 트렌드 분석
**데이터 소스**: Chroma 벡터 DB (국제금융시장 데이터, 종합뉴스) + Tavily 웹 검색

**내부 LangGraph 워크플로우**:

```
input_router
    │
    ├─ finance ──→ multi_query_generator → check_availability → rag_searcher
    │                                                                    │
    └─ general/off_topic ──→ direct_answer ──→ END                      │
                                                              context_evaluator
                                                                    │
                                              Enough ─────────────┤
                                                │             Not_Enough → web_searcher
                                                │                                │
                                                │                        context_filter
                                                │                                │
                                                │                        context_reranker
                                                │                                │
                                                └───────── (병합) ────────────────┘
                                                                    │
                                                        answer_generator
                                                                    │
                                                        hallucination_grader
                                                                    │
                                              Faithful ──→ END    Hallucination_Detected
                                                                    │
                                                        answer_regenerator (최대 2회 루프)
                                                                    │
                                                          → hallucination_grader
```

---

## API 스펙

### `POST /ask`

**Request Body**

```json
{
  "question": "삼성전자 최근 실적 발표 요약해줘",
  "ticker": "005930",
  "agents": ["news_agent"],
  "document_base64": null,
  "compare_mode": null
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `question` | string | 조건부 | 사용자 질문 (Report/Stock 단독 탭에서는 생략 가능) |
| `ticker` | string | 조건부 | 종목 코드 (Stock Agent 사용 시 필수) |
| `agents` | string[] | 선택 | 직접 지정 시 오케스트레이터 라우팅을 생략하고 해당 에이전트만 실행 |
| `document_base64` | string | 선택 | 첨부 문서(PDF) base64 인코딩 데이터 |
| `compare_mode` | `"YoY"` \| `"QoQ"` \| null | 선택 | Report Agent 증감 비교 기준 |

> 실제 필드명은 `orchestrator/schemas.py`의 Pydantic 모델을 최신 기준으로 확인하세요.

---

## 사용 예시

### Orchestrator 탭 (자동 라우팅)
```
입력: "카카오 최근 소송 이슈랑 관련 뉴스 같이 알려줘" + 첨부 문서 없음
→ 라우팅 결과: Legal Agent, News Agent 병렬 실행
→ 출력: 두 에이전트 결과를 종합한 요약 + 각 에이전트 상세 답변
```

### Legal Agent 탭
```
입력 질문: "계약 해지 조항에 손해배상 청구가 가능한가요?"
첨부 문서: 계약서.pdf
→ 흐름: Hybrid 경로 (document_parser → issue_extractor → rag_searcher …)
→ 출력: 관련 조문·판례 인용 + 법률 자문 형태의 답변
```

### Stock Agent 탭
```
입력 Ticker: "005930" (삼성전자)
→ 흐름: 공시 크롤링 → Optimist/Pessimist 최대 6턴 토론 → 합의
→ 출력: Buy/Sell/Hold 의견 + 근거 요약 + 리스크 요인
```

### Report Agent 탭
```
첨부 문서: 2026_1Q_재무제표.pdf
Compare Mode: YoY
→ 흐름: Upstage 파싱 → 지표 추출 → 전년 대비 증감 계산 → 변동 원인 추론
→ 출력: 주요 지표 표 + YoY 증감률 + 변동 원인 요약
```

---

## 환경 변수 설정 (`.env`)

```env
TAVILY_API_KEY=your_tavily_api_key        # News, Legal, Trend Agent 웹 검색
UPSTAGE_API_KEY=your_upstage_api_key      # Report Agent PDF 파싱
USER_EMAIL=your_email@example.com         # Selenium 크롤링 인증 (Stock Agent)
```

> `.env.example` 파일을 참고하여 `.env` 파일을 생성하세요.

---

## 하드웨어 요구사항

| 항목 | 최소 사양 | 권장 사양 |
|------|-----------|-----------|
| GPU | 없음 (CPU 추론 가능, 속도 저하) | NVIDIA GPU, VRAM 8GB 이상 |
| RAM | 16GB | 32GB |
| 디스크 | 20GB 여유 공간 (모델·벡터 DB 포함) | 50GB 이상 |
| Python | 3.10 이상 | 3.11 |
| 브라우저(Selenium용) | Chrome 설치 필요 (Stock Agent 크롤링) | 최신 버전 Chrome |

> Kanana 1.5-2.1b는 경량 모델이지만, 여러 에이전트가 병렬로 모델을 호출할 경우 GPU 메모리 사용량이 누적될 수 있습니다. 동시 요청이 많은 환경에서는 VRAM 여유를 넉넉히 확보하는 것을 권장합니다.

---

## 실행 가이드

### 방법 1: 자동 설치 스크립트 (처음 실행 시)

저장소를 클론하고 전체 환경을 자동으로 설정합니다.

```bash
chmod +x setup_and_run.sh
./setup_and_run.sh
```

**스크립트 실행 순서:**

1. **저장소 클론** — GitHub에서 프로젝트를 `app/` 디렉터리로 클론
2. **가상환경 생성** — Python `venv` 생성 및 활성화
3. **패키지 설치** — `requirements.txt` 기반 의존성 설치
4. **`.env` 파일 확인** — 없으면 `.env.example`을 복사 후 사용자 입력 대기
5. **모델·데이터 준비** — `agent_setup.py` 실행 (아래 참고)
6. **서버 실행** — `run.sh` 호출 (백엔드 + 프론트엔드)

### 방법 2: 이미 클론된 경우 (재실행)

```bash
# 가상환경 활성화
source venv/bin/activate

# 모델/데이터 초기화 (최초 1회)
python agent_setup.py

# 서버 실행
chmod +x run.sh
./run.sh
```

### `agent_setup.py` 역할

최초 실행 시 필요한 모델과 데이터를 자동으로 다운로드합니다.

| 항목 | 다운로드 위치 | Hugging Face 소스 |
|------|--------------|-------------------|
| Kanana LLM | `./models/Kanana` | `kakaocorp/kanana-1.5-2.1b-instruct-2505` |
| BGE-M3 임베딩 | `./models/bge-m3` | `BAAI/bge-m3` |
| 에이전트 데이터 | `./data/` | `munchkincat/Kanana_Agent-data` |

이미 다운로드된 경우 재다운로드를 건너뜁니다.

### `run.sh` 실행 내용

```bash
# FastAPI 백엔드 (포트 8000, 백그라운드)
uvicorn main:app --reload --port 8000 &

# Streamlit 프론트엔드 (포어그라운드)
streamlit run app.py

# Streamlit 종료 시 백엔드도 자동 종료
```

- **백엔드**: `http://localhost:8000` (FastAPI, `/ask` 엔드포인트)
- **프론트엔드**: `http://localhost:8501` (Streamlit UI)

---

## 프론트엔드 탭 구성

| 탭 | 에이전트 | 필수 입력 | 선택 입력 |
|----|---------|---------|---------|
| 🧠 Orchestrator | 자동 선택 | — | 질문, Ticker, 문서 |
| ⚖️ Legal Agent | Legal Agent | 질문 | 문서 |
| 📰 News Agent | News Agent | 질문 | — |
| 📄 Report Agent | Report Agent | 문서 | — |
| 📈 Stock Agent | Stock Agent | Ticker | — |
| 🔍 Trend Agent | Trend Agent | 질문 | — |
| 🕓 History | — | — | — |

---

## 프로젝트 구조

```
Kanana_Agent/
├── app.py                  # Streamlit 프론트엔드
├── main.py                 # FastAPI 백엔드
├── config.py               # 전역 설정 (BaseConfig)
├── agent_setup.py          # 모델·데이터 초기화
├── setup_and_run.sh        # 원클릭 설치·실행 스크립트
├── run.sh                  # 서버 실행 스크립트
├── requirements.txt        # Python 의존성
├── .env.example             # 환경변수 예시
│
├── orchestrator/            # 오케스트레이터
│   ├── graph.py             # LangGraph 그래프 정의
│   ├── nodes.py              # Routing / Run Agents / Summarize 노드
│   ├── prompts.yaml          # 라우팅·요약 프롬프트
│   ├── schemas.py            # Pydantic 스키마
│   ├── states.py             # LangGraph 상태 정의
│   ├── functions.py          # 헬퍼 함수
│   └── converters.py         # 에이전트 출력 변환기
│
├── agents/
│   ├── legal_agent/          # 법률·계약 에이전트
│   │   ├── main.py
│   │   ├── legal_config.py
│   │   ├── legal_src/
│   │   │   ├── Agent/        # graph, nodes, prompts, schemas, states, tools
│   │   │   └── RAG/          # 벡터 DB, 임베딩, 검색
│   │   └── legal_utils/
│   │
│   ├── news_agent/           # 뉴스 검색 에이전트
│   │   ├── main.py
│   │   ├── news_config.py
│   │   ├── graph/             # graph, nodes, edges, state
│   │   ├── embeddings.py
│   │   └── vectorstore.py
│   │
│   ├── report_agent/         # 재무제표 분석 에이전트
│   │   ├── main.py
│   │   ├── nodes.py           # LangGraph 노드 + UpstageDocumentParseClient
│   │   ├── classes.py         # 데이터 클래스
│   │   ├── router.py          # RouterAgent
│   │   └── report_config.py
│   │
│   ├── stock_agent/          # 주식 투자 분석 에이전트
│   │   ├── main.py
│   │   ├── stock_config.py
│   │   └── stock_src/
│   │       ├── Agent/          # 토론 그래프, Optimist/Pessimist 노드
│   │       └── Crawling/       # 공시 크롤러
│   │
│   └── trend_agent/          # 거시경제 트렌드 에이전트
│       ├── main.py            # 전체 LangGraph 워크플로우 포함
│       ├── trend_config.py
│       └── database.py
│
├── utils/                    # 공유 유틸리티
│   ├── kanana_pipeline.py     # Kanana 모델 싱글턴 로더·추론 래퍼
│   ├── ticker_map.py          # 기업명 → Ticker 매핑
│   ├── agent_keywords.py      # 에이전트별 라우팅 키워드
│   ├── logger.py              # 로깅 유틸리티
│   ├── log_paths.py           # 로그 경로 관리
│   ├── selenium_runtime.py    # Selenium 런타임 설정
│   └── config_bootstrap.py    # 에이전트별 설정 부트스트랩
│
├── models/                   # 다운로드된 모델 (자동 생성)
│   ├── Kanana/
│   └── bge-m3/
│
├── data/                      # 에이전트 데이터 (자동 다운로드)
│   ├── legal_data/
│   ├── news_data/
│   ├── stock_data/
│   └── trend_data/
│
├── logs/                      # 실행 로그 (자동 생성)
└── kanana_history/            # 분석 히스토리 JSON (자동 생성)
```

---

## 주요 기술 스택

| 분류 | 기술 |
|------|------|
| LLM | Kanana 1.5-2.1b (kakao, 로컬 추론) |
| 임베딩 | BGE-M3 (BAAI) |
| 에이전트 프레임워크 | LangGraph |
| 백엔드 | FastAPI + Uvicorn |
| 프론트엔드 | Streamlit |
| 벡터 DB | Qdrant (News), Chroma (Trend), 커스텀 DB (Legal) |
| PDF 파싱 | Upstage Document AI |
| 웹 검색 | Tavily Search API |
| 크롤링 | Selenium |

---

## 트러블슈팅

| 증상 | 원인 | 해결 방법 |
|------|------|----------|
| `TAVILY_API_KEY` 관련 에러로 웹 검색 실패 | `.env`에 키 미설정 또는 만료 | `.env` 파일의 `TAVILY_API_KEY` 값을 확인하고 Tavily 대시보드에서 키 유효성 재확인 |
| Report Agent에서 PDF 파싱 실패 | `UPSTAGE_API_KEY` 미설정, 또는 Upstage API 요청 한도 초과 | 키 재확인 후 Upstage 콘솔에서 사용량 확인 |
| Stock Agent 크롤링 단계에서 멈춤/에러 | Chrome/Chromedriver 버전 불일치, 또는 `USER_EMAIL` 인증 실패 | 로컬 Chrome 버전과 Selenium 드라이버 버전 확인, `.env`의 `USER_EMAIL` 값 확인 |
| 모델 로딩 시 OOM(메모리 부족) 에러 | GPU VRAM 부족, 여러 에이전트 동시 실행 | 동시 실행 에이전트 수를 줄이거나 CPU 모드로 전환 (속도 저하 감수) |
| `agent_setup.py` 실행 시 다운로드 멈춤 | 네트워크 불안정 또는 Hugging Face 접속 제한 | 네트워크 재시도, 또는 Hugging Face 미러/프록시 설정 |
| Streamlit 종료 후에도 FastAPI 프로세스가 남아있음 | `run.sh`의 백그라운드 프로세스 정리 실패 | `lsof -i :8000` 등으로 프로세스 확인 후 수동 종료 |
| 첫 실행 시 응답이 매우 느림 | 모델 최초 로딩 및 워밍업 시간 | 정상적인 현상이며, 이후 요청부터는 속도가 개선됨 |

> 위 목록에 없는 문제는 `logs/` 디렉터리의 로그를 먼저 확인하세요.

---

## 라이선스

이 프로젝트의 라이선스는 저장소 루트의 `LICENSE` 파일을 따릅니다. 사용된 모델(Kanana, BGE-M3)과 외부 API(Upstage, Tavily)는 각 제공사의 별도 라이선스 및 이용약관이 적용되므로, 상업적 이용 전 반드시 해당 조건을 확인하시기 바랍니다.
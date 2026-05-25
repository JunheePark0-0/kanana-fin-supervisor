# 한국 금융 뉴스 RAG 에이전트 (news_rag)

한국 금융 뉴스 데이터 기반으로 답변을 생성하는 RAG 에이전트입니다.  
질의 재작성/구조화, 검색+재랭킹, 내부/최종 이중 검증, 외부 검색 결합 라우팅을 통해 답변 신뢰도를 높입니다.

## 주요 기능

1. **질의 전처리 파이프라인**: `query_rewrite`와 `query_structuring`으로 검색 친화적 질의 생성
2. **2단계 문서 필터링**: Qdrant `org` 필터 + Python 날짜 필터 후처리
3. **최신성 반영 재랭킹**: 키워드 점수 + 연도 가중치 결합
4. **입구/출구 이중 검증**: 내부 할루시네이션 체크 + 최종 RAGAS 품질 체크
5. **안전 라우팅**: `pass / regenerate / re_retrieve / cannot_answer` 분기, 최대 2회 재시도 제한

## 에이전트 아키텍처

```text
query_rewrite → query_structuring → retrieve_and_rerank
→ gen_internal_answer → hallucination_check_internal
        ↓ (FAIL 2회) or (PASS)
  query_rewrite_retry ←┘
        ↓
  web_search_finance
        ↓
  gen_final_answer → hallucination_check_final
        ↓ pass / regenerate / re_retrieve / cannot_answer
  format_answer or cannot_answer → END
```

## 핵심 설계 포인트

1. **외부 검색은 항상 실행**
   - 내부 검증 통과 여부와 무관하게 `web_search_finance`는 항상 실행됩니다.
   - 내부 PASS 결과는 핵심 근거, FAIL 결과는 보조 근거로 사용됩니다.

2. **문서 선택은 2단계 필터**
   - 1차: Qdrant `org` 필터로 후보 추출
   - 2차: Python 날짜 필터 적용
   - 0건일 경우: 최근 30일 → 연도 전체로 단계적 확장

3. **재랭킹 점수 = 키워드 매칭 + 최신성 가중치**
   - 예: 2026년 `+5.0`, 2025년 `+2.0`
   - 후보군 확정 후 점수 계산은 1회만 수행

4. **검증은 내부/최종 두 번 수행**
   - 내부 검증: FACTUAL 팩트 일치, ANALYTICAL `[분석]` 태그 분리
   - 최종 검증: RAGAS 3지표(`faithfulness`, `relevancy`, `recall`)

5. **최종 검증 라우팅은 4방향**
   - `pass` → `format_answer`
   - `regenerate` → 답변 재생성
   - `re_retrieve` → 검색 재시도
   - `cannot_answer` → 실패 메시지 반환

## 프로젝트 구조

```text
kr_news_rag/
├── README.md
├── config.py                 # 에이전트 구동 환경설정
├── main.py                   # 에이전트 실행 엔트리포인트
├── setup.py                  # 사전 준비/환경 점검 엔트리포인트
├── verify_setup.py           # 실제 점검 로직
├── requirements.txt
├── .gitignore
├── .env.example
├── embeddings.py
├── vectorstore.py
├── graph/
│   ├── state.py
│   ├── nodes.py
│   ├── edges.py
│   └── graph.py
├── ingest/
└── utils/
```

## 설치 및 실행

### 1) 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) 환경변수 설정

```bash
cp .env.example .env
```

주요 환경변수:

- `QDRANT_PATH`: 로컬 Qdrant 저장 경로
- `COLLECTION_NAME`: 컬렉션 이름
- `TAVILY_API_KEY`: Tavily API 키
- `MODEL_DIR`: 로컬 Kanana 모델 경로
- `SEARCH_LOG_PATH`: 검색 로그 경로
- `QA_LOG_PATH`: 질의/응답 로그(JSONL)
- `EMBEDDING_MODEL_DIR`: 로컬 BGE-M3 폴더
- `SKIP_QDRANT`: `1`이면 Qdrant 연결 없이 사전 점검 모드 실행

### 3) 사전 점검

```bash
python setup.py
```

또는:

```bash
SKIP_QDRANT=1 python main.py
```

### 4) 에이전트 실행

```bash
python main.py
```

## 파일 기반 기사 수집(옵션)

```bash
python ingest/crawl_from_folder.py \
  --input-dir "/absolute/path/to/input_folder" \
  --output-dir "./ingest_output"
```

## Qdrant DB 공유/병합 절차 (팀원용)

DB를 통째로 Git 커밋하지 않고, 압축 파일(`zip`)로 공유한 뒤 로컬에서 병합하는 방식을 권장합니다.

### 1) DB 받기 및 압축 해제

- 공유받은 예시 파일: `qdrant_db_20260417.zip`
- 프로젝트 루트 기준 `./data/` 아래로 압축 해제

예시:

```bash
mkdir -p ./data
unzip qdrant_db_20260417.zip -d ./data
```

압축 해제 후 경로 예시:

- `./data/qdrant_db_teamA`
- `./data/qdrant_db_teamB`

### 2) 기준 DB 선택

- 병합 결과를 저장할 기준 DB를 하나 정합니다. (예: `qdrant_db_teamA`)
- 병합 전 반드시 백업본을 만듭니다.

```bash
cp -R ./data/qdrant_db_teamA ./data/qdrant_db_teamA_backup
```

### 3) 컬렉션 단위 병합 원칙

- 서로 다른 팀 DB를 병합할 때는 **컬렉션 이름 충돌 여부**를 먼저 확인합니다.
- 동일 컬렉션으로 합칠 경우:
  - 문서 고유 ID 중복 정책(덮어쓰기/건너뛰기)을 사전에 합의
  - 메타데이터(`org`, `date`, `source`) 스키마를 동일하게 유지
- 충돌 위험이 크면 컬렉션을 분리한 뒤 검색 단계에서 멀티 컬렉션 조회 전략을 사용합니다.

### 4) 실행 경로 지정

`.env`의 `QDRANT_PATH`를 병합 완료 DB 경로로 지정합니다.

```env
QDRANT_PATH=./data/qdrant_db_teamA
```

### 5) 점검 후 실행

```bash
python setup.py
python main.py
```


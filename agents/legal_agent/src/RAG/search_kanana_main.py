"""
생성된 VectorDB를 활용해서 검색 기능을 구현
- Naive RAG 기반 검색 기능
- Hybrid RAG 기반 검색 기능
- Kanana 활용하여 답변 생성
"""
import os
import sys

_LEGAL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_LEGAL_ROOT))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# ChromaDB 텔레메트리 비활성화 (오류 방지)
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# posthog 텔레메트리 오류 방지를 위한 패치
try:
    import posthog
    def dummy_capture(*args, **kwargs):
        pass
    posthog.capture = dummy_capture
except ImportError:
    pass

import chromadb
import re, math, pickle, sys 
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
from collections import Counter, defaultdict
import torch    
from utils.kanana_pipeline import get_kanana_pipeline

from src.RAG.naive_search import NaiveSearchEngine
from src.RAG.embedding import LawEmbeddings
from legal_config import LegalConfig

import asyncio 

# 문서 필터링 진행
class NaiveSearchWithAnswer():
    def __init__(self, collection, query : str, pipeline=None):
        self.collection = collection
        self.query = query
        if pipeline is not None:
            self.pipeline = pipeline
            self.tokenizer = None
        else:
            self.pipeline, self.tokenizer = get_kanana_pipeline()
        self.query_embedding = LawEmbeddings().create_query_embedding(query)
        self.search_engine = NaiveSearchEngine(
            collection,
            self.query_embedding,
            top_k = 10,
            save_path = LegalConfig.FILTERED_DB_PATH,
        )

    def search(self, where : Optional[Dict] = None):
        return self.search_engine.search(self.query_embedding, where = where)

if __name__ == "__main__":
    query = input("검색할 쿼리를 입력해주세요: ")

    # ChromaDB 경로 설정
    lawdb_path = LegalConfig.LAW_DB_PATH
    client = chromadb.PersistentClient(path = lawdb_path)
    collection = client.get_or_create_collection("laws")

    # NaiveSearchWithAnswer 객체 생성 (파이프라인은 클래스 내부에서 로드)
    naive_search_with_answer = NaiveSearchWithAnswer(collection, query)

    # 검색 결과 생성
    docs = naive_search_with_answer.search()

    print("--------------------------------")
    print(f"Query : {query}")
    print("--------------------------------")
    print(f"검색 결과 개수 : {len(docs)}")
    print("--------------------------------")
    print(f"Top-3 Docs : \n\n {docs[:3]}")
    print("--------------------------------")

    # 필터링된 결과 저장
    naive_search_with_answer.search_engine.save_filtered(query)


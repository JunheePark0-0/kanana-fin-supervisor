"""
Qdrant 클라이언트를 열지 않고, 경로·파일 구조만 점검합니다.
적재 중에는 이 스크립트만 사용하고 main.py는 실행하지 마세요.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 프로젝트 루트에서 config 로드
from config import (
    COLLECTION_NAME,
    EMBEDDING_MODEL_DIR,
    MODEL_DIR,
    QDRANT_PATH,
)


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _warn(msg: str) -> None:
    print(f"  [!!] {msg}")


def _fail(msg: str) -> None:
    print(f"  [XX] {msg}")


def check_dir(path: str, label: str) -> bool:
    p = Path(path)
    if not p.exists():
        _fail(f"{label}: 경로 없음 → {path}")
        return False
    if not p.is_dir():
        _fail(f"{label}: 디렉터리가 아님 → {path}")
        return False
    _ok(f"{label}: {path}")
    return True


def check_file(path: Path, label: str) -> bool:
    if not path.is_file():
        _fail(f"{label}: 없음 → {path}")
        return False
    _ok(f"{label}: {path.name}")
    return True


def run_checks() -> int:
    print("=== 경로 점검 (Qdrant 연결 없음) ===\n")

    errors = 0

    print("[1] Kanana (MODEL_DIR)")
    if not check_dir(MODEL_DIR, "MODEL_DIR"):
        errors += 1
    else:
        for name in ("config.json", "tokenizer.json", "tokenizer_config.json"):
            p = Path(MODEL_DIR) / name
            if not check_file(p, name):
                errors += 1
        w = Path(MODEL_DIR)
        if not (w / "model.safetensors").is_file() and not (w / "pytorch_model.bin").is_file():
            _warn("가중치 파일(model.safetensors 또는 pytorch_model.bin) 없음")
            errors += 1

    print("\n[2] 임베딩 (EMBEDDING_MODEL_DIR)")
    if not check_dir(EMBEDDING_MODEL_DIR, "EMBEDDING_MODEL_DIR"):
        errors += 1
    else:
        emb = Path(EMBEDDING_MODEL_DIR)
        for rel in ("config.json", "modules.json", "tokenizer.json"):
            if not check_file(emb / rel, rel):
                errors += 1
        pool = emb / "1_Pooling" / "config.json"
        if not check_file(pool, "1_Pooling/config.json"):
            errors += 1
        norm = emb / "2_Normalize"
        if not norm.is_dir():
            _fail("2_Normalize 폴더 없음 (비어 있어도 폴더는 있어야 함)")
            errors += 1
        else:
            _ok("2_Normalize/ (폴더 존재)")

    print("\n[3] Qdrant (경로만 확인, DB 미오픈)")
    print(f"  COLLECTION_NAME={COLLECTION_NAME}")
    if not check_dir(QDRANT_PATH, "QDRANT_PATH"):
        errors += 1
    else:
        coll_sql = Path(QDRANT_PATH) / "collection" / COLLECTION_NAME / "storage.sqlite"
        if coll_sql.is_file():
            _ok(f"컬렉션 데이터 파일 존재: .../{COLLECTION_NAME}/storage.sqlite")
        else:
            _warn(
                "storage.sqlite 없음 (적재 중이거나 경로/컬렉션명 불일치일 수 있음). "
                "이 메시지는 DB를 열지 않은 상태의 파일 존재 여부만 봅니다."
            )

    print("\n=== 요약 ===")
    if errors:
        print(f"누락/문제: {errors}건 — 위 [XX] 항목을 확인하세요.")
        return 1
    print("구조 점검 통과 (Qdrant는 열지 않았습니다).")
    return 0


if __name__ == "__main__":
    sys.exit(run_checks())

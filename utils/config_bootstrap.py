"""
config_bootstrap.py: 각 에이전트 config에서 공통으로 쓰는 부트스트랩
(각 에이전트에서 필요한 공통 경로 미리 설정, 절대경로로 변환)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, NamedTuple

from dotenv import load_dotenv


DotenvMode = Literal["agent", "project", "none"]


class ConfigBootstrapContext(NamedTuple):
    project_root: Path
    module_root: Path
    base_config: type


def _project_root_from_file(current_file: str) -> Path:
    return Path(current_file).resolve().parent.parent


def ensure_project_root_on_syspath(current_file: str) -> Path:
    project_root = _project_root_from_file(current_file)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root


def bootstrap_config(
    current_file: str,
    *,
    dotenv_mode: DotenvMode = "agent",
) -> ConfigBootstrapContext:
    """
    각 에이전트 config에서 공통으로 쓰는 부트스트랩:
    1) 프로젝트 루트를 sys.path에 추가
    2) 에이전트 루트(module_root)를 sys.path에 추가
       → 에이전트 내부 파일들이 `from config import Config`로 에이전트 config.py를 찾을 수 있음
    3) 지정된 범위의 .env 로드
    4) BaseConfig import
    """
    project_root = ensure_project_root_on_syspath(current_file)
    module_root = Path(current_file).resolve().parent

    # 에이전트 루트도 sys.path에 추가 (에이전트 내부 파일들이 `from config import Config` 가능하도록)
    if str(module_root) not in sys.path:
        sys.path.insert(0, str(module_root))

    if dotenv_mode == "agent":
        load_dotenv(dotenv_path=module_root / ".env")
    elif dotenv_mode == "project":
        load_dotenv(dotenv_path=project_root / ".env")
    elif dotenv_mode != "none":
        raise ValueError(f"Unsupported dotenv_mode: {dotenv_mode}")

    from config_base import BaseConfig

    return ConfigBootstrapContext(
        project_root=project_root,
        module_root=module_root,
        base_config=BaseConfig,
    )


def resolve_from_module_root(module_root: Path, path_value: str) -> str:
    """각 모듈 폴더를 기준으로 절대경로 변환"""
    path = Path(path_value)
    if path.is_absolute():
        return str(path)
    return str((module_root / path).resolve())

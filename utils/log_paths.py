"""에이전트별 로그 경로: logs/{agent_name}/{YYYYMMDD_HHMMSS}/"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config import BaseConfig

LOG_RUN_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
DEFAULT_AGENT_LOG_FILENAME = "agent.log"

_run_dirs: dict[str, Path] = {}


def agent_log_root(agent_name: str) -> Path:
    return Path(BaseConfig.agent_log_root(agent_name))


def create_agent_log_run_dir(
    agent_name: str,
    timestamp: str | None = None,
) -> Path:
    """실행마다 logs/{agent_name}/{timestamp}/ 디렉터리를 생성합니다."""
    ts = timestamp or datetime.now().strftime(LOG_RUN_TIMESTAMP_FORMAT)
    run_dir = agent_log_root(agent_name) / ts
    run_dir.mkdir(parents = True, exist_ok = True)
    return run_dir.resolve()


def get_agent_log_run_dir(agent_name: str, *, new_folder: bool = False) -> Path:
    """프로세스 내 동일 에이전트는 같은 run 디렉터리를 재사용합니다."""
    if new_folder or agent_name not in _run_dirs:
        _run_dirs[agent_name] = create_agent_log_run_dir(agent_name)
    return _run_dirs[agent_name]


def agent_log_file(agent_name: str, filename: str = DEFAULT_AGENT_LOG_FILENAME, *, new_folder: bool = False) -> Path:
    return get_agent_log_run_dir(agent_name, new_folder = new_folder) / filename

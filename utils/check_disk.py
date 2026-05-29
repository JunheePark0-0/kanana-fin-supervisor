"""디스크 사용량 확인 유틸."""

from __future__ import annotations

import shutil
from pathlib import Path


def format_bytes(size_bytes: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    size = float(size_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def get_dir_sizes(path: str | Path = ".", *, top_n: int = 10) -> list[tuple[str, int, str]]:
    """하위 항목별 디스크 사용량 (큰 순)."""
    root = Path(path).resolve()
    sizes: list[tuple[str, int]] = []

    for child in root.iterdir():
        if child.is_file():
            size = child.stat().st_size
        else:
            size = sum(f.stat().st_size for f in child.rglob("*") if f.is_file())
        sizes.append((child.name, size))

    sizes.sort(key=lambda item: item[1], reverse=True)
    return [(name, size, format_bytes(size)) for name, size in sizes[:top_n]]


def get_disk_usage(path: str | Path = ".") -> dict[str, str | float | int]:
    """지정 경로가 있는 디스크의 사용량을 반환합니다."""
    resolved = Path(path).resolve()
    usage = shutil.disk_usage(resolved)

    used_ratio = usage.used / usage.total if usage.total else 0.0
    return {
        "path": str(resolved),
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
        "used_percent": round(used_ratio * 100, 1),
        "total_human": format_bytes(usage.total),
        "used_human": format_bytes(usage.used),
        "free_human": format_bytes(usage.free),
    }


def print_disk_usage(path: str | Path = ".", *, show_breakdown: bool = True, top_n: int = 10) -> None:
    info = get_disk_usage(path)
    print(f"경로: {info['path']}")
    print(f"전체: {info['total_human']}")
    print(f"사용: {info['used_human']} ({info['used_percent']}%)")
    print(f"남음: {info['free_human']}")

    if show_breakdown:
        print(f"\n[용량 큰 항목 top {top_n}]")
        for name, _, human in get_dir_sizes(path, top_n=top_n):
            print(f"  {human:>8}  {name}")


if __name__ == "__main__":
    print_disk_usage(".")

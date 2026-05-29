"""Linux Selenium/Chrome 런타임 설치 (Stock Agent 뉴스 크롤링용)."""

from __future__ import annotations

import shutil
import subprocess
import sys


def _run_cmd(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def ensure_linux_selenium_runtime() -> None:
    """Linux에서 Selenium 실행에 필요한 브라우저/라이브러리를 설치합니다."""
    if not sys.platform.startswith("linux"):
        print("Linux 환경이 아니므로 Selenium 런타임 설치를 건너뜁니다.")
        return

    print("Linux Selenium 런타임 점검을 시작합니다.")

    if not shutil.which("apt-get"):
        print("apt-get이 없어 시스템 패키지 설치를 건너뜁니다.")
    else:
        _run_cmd(["apt-get", "update"])

        try:
            _run_cmd([
                "apt-get", "install", "-y",
                "libatk1.0-0", "libatk-bridge2.0-0", "libcups2", "libdrm2", "libxkbcommon0",
                "libxcomposite1", "libxdamage1", "libxfixes3", "libxrandr2", "libgbm1", "libgtk-3-0",
                "libasound2t64",
            ])
        except subprocess.CalledProcessError:
            _run_cmd(["apt-get", "install", "-y", "libasound2"])

        try:
            _run_cmd(["apt-get", "install", "-y", "chromium-browser", "libnss3", "libnspr4"])
        except subprocess.CalledProcessError:
            _run_cmd(["apt-get", "install", "-y", "chromium", "libnss3", "libnspr4"])

    _run_cmd([sys.executable, "-m", "pip", "install", "-U", "selenium", "webdriver-manager"])
    print("✅ Linux Selenium 런타임 설치 완료")

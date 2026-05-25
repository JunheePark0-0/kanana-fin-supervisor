import re
import time

import requests
from bs4 import BeautifulSoup

from ingest.crawlers.base import SeleniumArticleCrawler


def remove_emojis(text: str) -> str:
    if not text:
        return ""
    return re.sub(
        r"[^\uAC00-\uD7A30-9a-zA-Z\s.,!?\"\'\(\)\[\]\%\-\:\/\;\&]",
        "",
        text,
    )


class MoneyTodayCrawler(SeleniumArticleCrawler):
    # requests 우선 추출용 선택자
    request_selectors = [
        ("id", "articleView"),
        ("id", "textBody"),
        ("css", "[itemprop='articleBody']"),
        ("css", ".view_text"),
        ("css", ".article_view"),
    ]
    selectors = [
        ("ID", "articleView"),
        ("ID", "textBody"),
        ("CSS_SELECTOR", "[itemprop='articleBody']"),
    ]

    def __init__(
        self,
        wait_seconds: int = 15,
        page_load_timeout: int = 25,
        timeout: int = 10,
        retry_max: int = 2,
        delay: float = 0.3,
    ):
        super().__init__(wait_seconds=wait_seconds, page_load_timeout=page_load_timeout)
        self.timeout = timeout
        self.retry_max = retry_max
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "ko-KR,ko;q=0.9",
                "Referer": "https://news.mt.co.kr/",
            }
        )

    def clean_text(self, text: str) -> str:
        text = remove_emojis(text)
        lines = text.split("\n")
        cleaned_lines = [
            line.strip()
            for line in lines
            if line.strip() and "/사진" not in line and "ADVERTISEMENT" not in line
        ]
        text = "\n".join(cleaned_lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _extract_by_requests(self, url: str):
        for attempt in range(1, self.retry_max + 1):
            try:
                time.sleep(self.delay)
                resp = self.session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                target = None
                for kind, selector in self.request_selectors:
                    if kind == "id":
                        target = soup.find(id=selector)
                    else:
                        target = soup.select_one(selector)
                    if target is not None:
                        break

                if target is None:
                    continue

                raw = target.get_text("\n", strip=True)
                if not raw:
                    continue
                clean = self.clean_text(raw)
                if clean:
                    return raw, clean, "성공(requests)"
            except Exception:
                if attempt < self.retry_max:
                    time.sleep(self.delay * 2)
        return "", "", "실패(requests)"

    def crawl(self, url: str):
        raw, clean, status = self._extract_by_requests(url)
        if status.startswith("성공"):
            from ingest.crawlers.base import CrawlResult

            return CrawlResult(raw, clean, status)

        # requests 실패 시 Selenium fallback
        result = super().crawl(url)
        if result.status == "성공":
            result.status = "성공(selenium_fallback)"
        return result

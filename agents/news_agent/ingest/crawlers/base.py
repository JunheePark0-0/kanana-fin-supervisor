import re
from dataclasses import dataclass
from typing import List, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


@dataclass
class CrawlResult:
    content_raw: str
    content_clean: str
    status: str


class SeleniumArticleCrawler:
    selectors: List[Tuple[str, str]] = []

    def __init__(self, wait_seconds: int = 15, page_load_timeout: int = 25):
        self.wait_seconds = wait_seconds
        self.page_load_timeout = page_load_timeout

    def create_driver(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(self.page_load_timeout)
        return driver

    def clean_text(self, text: str) -> str:
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def crawl(self, url: str) -> CrawlResult:
        driver = None
        try:
            driver = self.create_driver()
            driver.get(url)
            # WebDriverWait(driver, self.wait_seconds)

            found = None
            for by, selector in self.selectors:
                try:
                    found = driver.find_element(getattr(By, by), selector)
                    if found:
                        break
                except Exception:
                    continue

            if not found:
                return CrawlResult("", "", "실패(요소미발견)")

            raw = (found.text or "").strip()
            if not raw:
                return CrawlResult("", "", "실패(내용없음)")

            clean = self.clean_text(raw)
            if not clean:
                return CrawlResult(raw, "", "실패(정제후내용없음)")
            return CrawlResult(raw, clean, "성공")
        except Exception as exc:
            return CrawlResult("", "", f"실패({type(exc).__name__})")
        finally:
            if driver:
                driver.quit()

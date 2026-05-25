from ingest.crawlers.base import SeleniumArticleCrawler


class HankyungCrawler(SeleniumArticleCrawler):
    # 이후 한국경제 전용 로직을 제공받으면 여기서 clean_text/selector를 교체
    selectors = [
        ("ID", "articletxt"),
        ("CSS_SELECTOR", "[itemprop='articleBody']"),
    ]

from ingest.crawlers.hankyung import HankyungCrawler
from ingest.crawlers.moneytoday import MoneyTodayCrawler


def get_crawler_by_press(press: str):
    p = (press or "").strip().lower()
    if "머니투데이" in p or "moneytoday" in p:
        return MoneyTodayCrawler()
    if "한국경제" in p or "hankyung" in p:
        return HankyungCrawler()
    return None

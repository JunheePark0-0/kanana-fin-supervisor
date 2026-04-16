import sys
import os

# Stock_Agent 전용 패키지 경로만 추가 (루트 `src`와 이름 충돌 방지)
_STOCK_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _STOCK_ROOT)

import argparse
import asyncio

from src.Crawling.crawling_main import main as run_crawling
from src.Agent.agent_main import main as run_agent_debate


async def stock_agent_main(ticker: str):
    """상위 에이전트가 호출할 최종 진입 지점"""
    ticker = ticker.upper()

    print("\n" + "=" * 60)
    print(f"🚀 [{ticker}] 통합 파이프라인 시작 (Crawling + Debate)")
    print("=" * 60)

    print("\n[1/2] 데이터 크롤링 및 DB 업데이트 시작")
    crawling_result = await run_crawling(ticker)

    print("\n[2/2] Multi Agent 토론 시작")
    final_report = await run_agent_debate(ticker)

    print("\n" + "=" * 60)
    print(f"✅ [{ticker}] 통합 파이프라인 완료")
    print("=" * 60 + "\n")
    
    return{
        "ticker": ticker,
        "crawling_summary": crawling_result,
        "final_report": final_report
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", type = str, required = True)
    args = parser.parse_args()

    asyncio.run(stock_agent_main(args.ticker))

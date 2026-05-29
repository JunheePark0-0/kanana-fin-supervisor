import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.Agent.graph import agent_debate_graph
from stock_config import StockConfig
from utils.kanana_pipeline import get_kanana_pipeline
from utils.log_paths import get_agent_log_run_dir
from utils.logger import setup_logger
import argparse
import traceback
import asyncio

async def main(ticker : str):
    log_run_dir = get_agent_log_run_dir(StockConfig.AGENT_LOG_NAME, new_folder = True)
    if StockConfig.ENABLE_LOCAL_LOGGING:
        setup_logger(log_run_dir = log_run_dir)

    # 모델 초기화 로그를 먼저 보여주기 위해 배너 출력 전에 선로딩
    # 상위) 이미 로드되어 있다면 즉시 반환되어 다음 단계로 넘어가게 됨
    get_kanana_pipeline()

    print(f"{'='*60}")
    print(f"🔍 [Multi Agent] {ticker} 분석 시작")
    print(f"{'='*60}")

    # 초기 상태 설정 
    initial_state = {
        "ticker" : ticker.upper(),
        "context" : "", # 에이전트가 tool로 업데이트할 공간
        "optimist_initial" : "",
        "pessimist_initial" : "",
        "debate_history" : [],
        "sources" : [],
        "tool_calls" : [],
        "turn_count" : 0,
        "max_turns" : 6,
        "current_agent" : "start",
        "final_consensus" : None
    }

    # 그래프 생성 및 실행
    print("--- 🚀 Multi Agent Debate 시작 ---")
    graph = agent_debate_graph()
    try:
        result = await graph.ainvoke(initial_state)

        # 결과 출력
        print("\n" + "="*50)
        print(f"🏆 {ticker} 투자 분석 최종 합의안")
        print("="*50)

        return result.get("final_consensus", "합의안 도출에 실패했습니다..")

    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {repr(e)}")
        print(traceback.format_exc())
        return f"에러 발생: {str(e)}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Multi Agent Debate")
    parser.add_argument("--ticker", type = str, required = True, help = "타겟 기업명 (Ticker)")
    args = parser.parse_args()

    asyncio.run(main(args.ticker.upper()))
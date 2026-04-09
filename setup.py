import subprocess
import sys
from pathlib import Path

from config import Config

### Kanana 모델 다운로드 (최초 1회 실행) 
def download_kanana(model_name: str, save_dir: Path) -> None:
    """
    Hugging Face에서 Kanana 모델을 다운로드하는 함수 (최초 1회 실행).
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer

    save_dir.mkdir(parents = True, exist_ok = True)

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)

    tokenizer.save_pretrained(str(save_dir))
    model.save_pretrained(str(save_dir))

    print(f"✅ 모델과 토크나이저가 `{save_dir}`에 저장되었습니다.")

def has_local_kanana(save_dir: Path) -> bool:
    """
    로컬 모델 폴더에 필수 파일이 있는지 확인합니다.
    """
    required_files = [
        save_dir / "config.json",
        save_dir / "tokenizer_config.json",
    ]
    return all(path.exists() for path in required_files)

def ensure_kanana_model() -> None:
    """
    Config에서 model_name, save_dir를 가져와 로컬 모델 존재 여부를 확인하고 필요 시 다운로드합니다.
    """
    model_name = Config.KANANA_MODEL_NAME
    save_dir = Path(Config.KANANA_MODEL_PATH)

    print("Kanana 모델 확인 중..")
    if has_local_kanana(save_dir):
        print("✅ 모델 확인 완료")
        return

    print("로컬 모델이 없어 다운로드를 시작합니다..")
    download_kanana(model_name, save_dir)
    print("✅ 모델 준비 완료")

### 각 Agent 설정 확인
def check_all_agents():
    for agent_id, url in Config.get_agent_ports().items():
        try:
            res = requests.get(f"{url}/health", timeout = 2)
            if res.status_code == 200:
                print(f"✅ {agent_id} Agent Setup 완료: {url}")
        except Exception as e:
            print(f"❌ {agent_id} Agent Setup 실패: {url} - {e}")


def main() -> None:
    print("초기 환경 점검을 시작합니다.")
    ensure_kanana_model()
    check_all_agents()
    print("모든 초기 설정이 완료되었습니다.")

if __name__ == "__main__":
    main()
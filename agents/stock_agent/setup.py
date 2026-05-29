from pathlib import Path

from stock_config import StockConfig
from utils.selenium_runtime import ensure_linux_selenium_runtime


def download_kanana(model_name: str, save_dir: Path) -> None:
    """
    Hugging Face에서 Kanana 모델을 다운로드하는 함수 (최초 1회 실행)
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
    로컬 모델 폴더에 필수 파일이 있는지 확인
    """
    required_files = [
        save_dir / "config.json",
        save_dir / "tokenizer_config.json",
    ]
    return all(path.exists() for path in required_files)


def ensure_kanana_model() -> None:
    """
    Config에서 model_name, save_dir를 가져와 로컬 모델 존재 여부를 확인하고 필요 시 다운로드
    """
    model_name = StockConfig.KANANA_MODEL_NAME
    save_dir = Path(StockConfig.KANANA_MODEL_PATH)

    print("Kanana 모델 확인 중..")
    if has_local_kanana(save_dir):
        print("✅ 모델 확인 완료")
        return

    print("로컬 모델이 없어 다운로드를 시작합니다..")
    download_kanana(model_name, save_dir)
    print("✅ 모델 준비 완료")

def ensure_env_file() -> None:
    """루트 .env에 SEC 크롤링용 USER_EMAIL이 설정되어 있는지 확인"""
    from stock_config import StockConfig

    if not StockConfig.USER_EMAIL:
        raise ValueError(
            "USER_EMAIL이 설정되어 있지 않습니다. "
            "프로젝트 루트 .env 파일에 USER_EMAIL을 설정해주세요."
        )


def main() -> None:
    print("초기 환경 점검을 시작합니다.")
    ensure_linux_selenium_runtime()
    ensure_kanana_model()
    print("모든 초기 설정이 완료되었습니다.")


if __name__ == "__main__":
    main()
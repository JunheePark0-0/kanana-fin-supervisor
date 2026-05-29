import argparse
from pathlib import Path

import pandas as pd

from news_config import NewsConfig
from ingest.crawlers import get_crawler_by_press


def _detect_column(df: pd.DataFrame, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def process_file(path: Path, output_dir: Path):
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    url_col = _detect_column(df, ["URL", "url", "link"])
    press_col = _detect_column(df, ["언론사", "press", "source"])
    if not url_col or not press_col:
        print(f"[SKIP] {path.name} (URL/언론사 컬럼 없음)")
        return

    contents = []
    cleaned = []
    statuses = []

    total = len(df)
    for idx, row in df.iterrows():
        url = str(row.get(url_col, "")).strip()
        press = str(row.get(press_col, "")).strip()
        if not url:
            contents.append("")
            cleaned.append("")
            statuses.append("실패(URL없음)")
            continue

        crawler = get_crawler_by_press(press)
        if crawler is None:
            contents.append("")
            cleaned.append("")
            statuses.append("건너뜀(미지원언론사)")
            continue

        result = crawler.crawl(url)
        contents.append(result.content_raw)
        cleaned.append(result.content_clean)
        statuses.append(result.status)
        if (idx + 1) % 20 == 0 or idx + 1 == total:
            print(f"  - {path.name}: {idx+1}/{total} 처리")

    df["본문_수집"] = contents
    df["본문_정제"] = cleaned
    df["성공여부"] = statuses

    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"{path.stem}_crawled{path.suffix}"
    if out.suffix.lower() in {".xlsx", ".xls"}:
        df.to_excel(out, index=False)
    else:
        df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"[DONE] {path.name} -> {out.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        required=True,
        help="예: /Users/hyeonjinlee/Downloads/NewsResult_20260114-20260414",
    )
    parser.add_argument(
        "--output-dir",
        default=NewsConfig.INGEST_OUTPUT_DIR,
        help="크롤링 결과 저장 폴더",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    files = sorted(
        [
            *input_dir.glob("*.csv"),
            *input_dir.glob("*.xlsx"),
            *input_dir.glob("*.xls"),
        ]
    )
    if not files:
        print("입력 파일이 없습니다.")
        return

    print(f"파일 {len(files)}개 처리 시작")
    for f in files:
        process_file(f, output_dir)
    print("모든 파일 처리 완료")


if __name__ == "__main__":
    main()

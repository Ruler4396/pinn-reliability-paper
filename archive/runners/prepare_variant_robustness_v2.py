from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT / "results" / "variant_robustness"
BASE_SUITE = BASE_DIR / "variant_robustness_v1"
FISHER_SUITE = BASE_DIR / "variant_robustness_fisher_v1"
OUTPUT_SUITE = BASE_DIR / "variant_robustness_v2"


def merge_csvs(paths: list[Path], output_path: Path) -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in paths if path.exists()]
    if not frames:
        raise FileNotFoundError(f"No input CSVs found for {output_path}")
    merged = pd.concat(frames, ignore_index=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    return merged


def main() -> None:
    OUTPUT_SUITE.mkdir(parents=True, exist_ok=True)
    point_runs = merge_csvs(
        [
            BASE_SUITE / "point_runs.csv",
            FISHER_SUITE / "point_runs.csv",
        ],
        OUTPUT_SUITE / "point_runs.csv",
    )
    point_summary = merge_csvs(
        [
            BASE_SUITE / "point_summary.csv",
            FISHER_SUITE / "point_summary.csv",
        ],
        OUTPUT_SUITE / "point_summary.csv",
    )

    summary = {
        "source_suites": [
            str(BASE_SUITE),
            str(FISHER_SUITE),
        ],
        "n_point_runs": int(len(point_runs)),
        "n_point_summary_rows": int(len(point_summary)),
        "cases": sorted(point_runs["case"].unique().tolist()),
    }
    with (OUTPUT_SUITE / "merge_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(f"[done] output_dir={OUTPUT_SUITE}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

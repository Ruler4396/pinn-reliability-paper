from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import NormalDist
from typing import Dict, List

import pandas as pd


def wilson_interval(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    phat = k / n
    denom = 1.0 + (z * z) / n
    center = (phat + (z * z) / (2.0 * n)) / denom
    margin = (
        z
        * math.sqrt((phat * (1.0 - phat) / n) + (z * z) / (4.0 * n * n))
        / denom
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def main() -> None:
    parser = argparse.ArgumentParser(description="Add Wilson confidence intervals to a multi-seed probability matrix.")
    parser.add_argument("--summary-csv", required=True, help="Path to multiseed_summary.csv.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional explicit output directory. Defaults to the summary file parent.",
    )
    parser.add_argument("--confidence", type=float, default=0.95, help="Confidence level, default 0.95.")
    args = parser.parse_args()

    summary_csv = Path(args.summary_csv).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else summary_csv.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(summary_csv)
    out_rows: List[Dict[str, float | int | str]] = []
    for row in df.to_dict(orient="records"):
        n_seed = int(row["n_seed"])
        k = int(row["crosses_threshold_count"])
        lo, hi = wilson_interval(k, n_seed, confidence=float(args.confidence))
        out = dict(row)
        out["cross_rate_ci_low"] = lo
        out["cross_rate_ci_high"] = hi
        out["cross_rate_ci_width"] = hi - lo
        out_rows.append(out)

    out_df = pd.DataFrame(out_rows)
    out_csv = output_dir / "multiseed_summary_with_ci.csv"
    out_df.to_csv(out_csv, index=False)

    by_noise = (
        out_df.groupby("noise_std", as_index=False)
        .agg(
            mean_cross_rate=("crosses_threshold_rate", "mean"),
            mean_ci_width=("cross_rate_ci_width", "mean"),
            max_ci_width=("cross_rate_ci_width", "max"),
        )
        .sort_values("noise_std")
    )
    by_noise.to_csv(output_dir / "cross_rate_ci_by_noise.csv", index=False)

    summary_json = {
        "summary_csv": str(summary_csv),
        "confidence": float(args.confidence),
        "n_points": int(len(out_df)),
        "n_seed_values": sorted(int(v) for v in out_df["n_seed"].unique()),
        "mean_ci_width": float(out_df["cross_rate_ci_width"].mean()),
        "max_ci_width": float(out_df["cross_rate_ci_width"].max()),
        "rows": out_rows,
    }
    with (output_dir / "multiseed_summary_with_ci.json").open("w", encoding="utf-8") as fh:
        json.dump(summary_json, fh, ensure_ascii=False, indent=2)

    print(json.dumps(summary_json, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

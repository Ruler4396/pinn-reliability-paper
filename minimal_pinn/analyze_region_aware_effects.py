from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


METRICS = [
    "rel_l2",
    "reliability_raw_recal",
    "physics_consistency_recal",
    "training_stability_recal",
    "numerical_accuracy_recal",
    "structural_stability_recal",
]


def bootstrap_ci(values: np.ndarray, n_boot: int = 5000, seed: int = 123) -> tuple[float, float]:
    if len(values) == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(n_boot, len(values)))
    samples = values[idx].mean(axis=1)
    low, high = np.percentile(samples, [2.5, 97.5])
    return float(low), float(high)


def cohens_dz(values: np.ndarray) -> float:
    if len(values) < 2:
        return float("nan")
    std = float(np.std(values, ddof=1))
    if std == 0.0:
        return float("nan")
    return float(np.mean(values) / std)


def analyze_compare(input_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(input_dir / "run_metrics.csv")
    rows: List[Dict[str, float | int | str]] = []
    for (case_name, label), grp in df.groupby(["case", "label"], sort=False):
        base = grp[grp["strategy"] == "baseline"].set_index("seed")
        for strategy_name in sorted(set(grp["strategy"]) - {"baseline"}):
            strat = grp[grp["strategy"] == strategy_name].set_index("seed")
            common = sorted(base.index.intersection(strat.index))
            if not common:
                continue
            for metric in METRICS:
                diff = strat.loc[common, metric].to_numpy() - base.loc[common, metric].to_numpy()
                ci_low, ci_high = bootstrap_ci(diff)
                rows.append(
                    {
                        "case": case_name,
                        "label": label,
                        "strategy": strategy_name,
                        "metric": metric,
                        "n_seed": len(common),
                        "baseline_mean": float(base.loc[common, metric].mean()),
                        "strategy_mean": float(strat.loc[common, metric].mean()),
                        "delta_mean": float(diff.mean()),
                        "delta_std": float(diff.std(ddof=0)),
                        "bootstrap_ci_low": ci_low,
                        "bootstrap_ci_high": ci_high,
                        "cohens_dz": cohens_dz(diff),
                        "ci_crosses_zero": int(ci_low <= 0.0 <= ci_high),
                    }
                )
    return pd.DataFrame(rows)


def build_note(summary_df: pd.DataFrame) -> str:
    lines = [
        "# Region-aware 干预效应量与置信区间分析",
        "",
        "本分析对 `baseline` 与各干预策略做 seed 配对差值统计，报告均值差、bootstrap 95% CI 与 Cohen's dz，用于避免只根据均值作过强推断。",
        "",
    ]
    for case_name in summary_df["case"].drop_duplicates():
        lines.append(f"## {case_name}")
        lines.append("")
        case_df = summary_df[(summary_df["case"] == case_name) & (summary_df["metric"].isin(["rel_l2", "reliability_raw_recal"]))]
        for _, row in case_df.iterrows():
            lines.append(
                f"- `{row['label']}` / `{row['strategy']}` / `{row['metric']}`: "
                f"`delta={row['delta_mean']:.4f}`, "
                f"`95% CI=[{row['bootstrap_ci_low']:.4f}, {row['bootstrap_ci_high']:.4f}]`, "
                f"`dz={row['cohens_dz']:.3f}`, "
                f"`crosses_zero={bool(row['ci_crosses_zero'])}`"
            )
        lines.append("")
    lines.append("如果区间跨 0，则主文应将该策略效果降为 tentative evidence，而不写成稳定提升。")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze paired effects for region-aware comparisons.")
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Region-aware comparison result directory containing run_metrics.csv",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = input_dir
    summary_df = analyze_compare(input_dir)
    summary_df.to_csv(output_dir / "effect_summary.csv", index=False)
    with (output_dir / "effect_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary_df.to_dict(orient="records"), fh, ensure_ascii=False, indent=2)

    note = build_note(summary_df)
    (Path(__file__).resolve().parent.parent / "notes" / "region_aware_effects_results.md").write_text(
        note,
        encoding="utf-8",
    )
    print(f"[done] output_dir={output_dir}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()

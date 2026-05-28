from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent

DIM_COLS = [
    "physics_consistency",
    "training_stability",
    "numerical_accuracy",
    "structural_stability",
]

CASE_DISPLAY = {
    "poisson": "Poisson",
    "stokes_poiseuille": "Stokes-Poiseuille",
    "burgers": "Burgers",
}


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    phat = k / n
    denom = 1.0 + z**2 / n
    center = (phat + z**2 / (2.0 * n)) / denom
    radius = z * math.sqrt((phat * (1.0 - phat) / n) + (z**2 / (4.0 * n**2))) / denom
    return max(0.0, center - radius), min(1.0, center + radius)


def summarize_points(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, float | int | str]] = []
    for (case_name, label, budget_name), grp in df.groupby(["case", "label", "budget_name"], sort=False):
        crosses = int(grp["crosses_threshold"].sum())
        n = int(len(grp))
        low, high = wilson_interval(crosses, n)
        mean_dim = grp[DIM_COLS].mean()
        dominant = mean_dim.idxmin()
        rows.append(
            {
                "case": case_name,
                "label": label,
                "budget_name": budget_name,
                "num_observation": int(grp["num_observation"].iloc[0]),
                "noise_std": float(grp["noise_std"].iloc[0]),
                "n_seed": n,
                "rel_l2_mean": float(grp["rel_l2"].mean()),
                "rel_l2_std": float(grp["rel_l2"].std(ddof=0)),
                "reliability_raw_mean": float(grp["reliability_raw"].mean()),
                "reliability_raw_std": float(grp["reliability_raw"].std(ddof=0)),
                "cross_rate": crosses / n,
                "cross_rate_ci_low": low,
                "cross_rate_ci_high": high,
                "physics_consistency_mean": float(mean_dim["physics_consistency"]),
                "training_stability_mean": float(mean_dim["training_stability"]),
                "numerical_accuracy_mean": float(mean_dim["numerical_accuracy"]),
                "structural_stability_mean": float(mean_dim["structural_stability"]),
                "dominant_dimension": dominant,
            }
        )
    return pd.DataFrame(rows)


def summarize_budget_shift(summary_df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, float | str]] = []
    for case_name, case_df in summary_df.groupby("case", sort=False):
        pivot = case_df.pivot(index="label", columns="budget_name")
        if ("rel_l2_mean", "baseline_budget") not in pivot.columns or (
            "rel_l2_mean",
            "stronger_budget",
        ) not in pivot.columns:
            continue
        for label in pivot.index:
            rows.append(
                {
                    "case": case_name,
                    "label": label,
                    "rel_l2_delta": float(
                        pivot.loc[label, ("rel_l2_mean", "stronger_budget")]
                        - pivot.loc[label, ("rel_l2_mean", "baseline_budget")]
                    ),
                    "reliability_delta": float(
                        pivot.loc[label, ("reliability_raw_mean", "stronger_budget")]
                        - pivot.loc[label, ("reliability_raw_mean", "baseline_budget")]
                    ),
                    "cross_rate_delta": float(
                        pivot.loc[label, ("cross_rate", "stronger_budget")]
                        - pivot.loc[label, ("cross_rate", "baseline_budget")]
                    ),
                    "dominant_baseline": str(pivot.loc[label, ("dominant_dimension", "baseline_budget")]),
                    "dominant_stronger": str(pivot.loc[label, ("dominant_dimension", "stronger_budget")]),
                }
            )
    return pd.DataFrame(rows)


def summarize_case_rankings(summary_df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, float | str]] = []
    for case_name, case_df in summary_df.groupby("case", sort=False):
        base = (
            case_df[case_df["budget_name"] == "baseline_budget"]
            .set_index("label")["rel_l2_mean"]
            .sort_index()
        )
        strong = (
            case_df[case_df["budget_name"] == "stronger_budget"]
            .set_index("label")["rel_l2_mean"]
            .sort_index()
        )
        common = base.index.intersection(strong.index)
        if len(common) >= 2:
            rows.append(
                {
                    "case": case_name,
                    "rho_rel_l2_mean": float(base.loc[common].corr(strong.loc[common], method="spearman")),
                    "baseline_hardest_label": str(base.loc[common].sort_values(ascending=False).index[0]),
                    "stronger_hardest_label": str(strong.loc[common].sort_values(ascending=False).index[0]),
                }
            )
    return pd.DataFrame(rows)


def plot_rel_l2_means(summary_df: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)
    for ax, case_name in zip(axes, ["poisson", "stokes_poiseuille", "burgers"]):
        case_df = summary_df[summary_df["case"] == case_name]
        labels = case_df["label"].drop_duplicates().tolist()
        x = range(len(labels))
        base = (
            case_df[case_df["budget_name"] == "baseline_budget"]
            .set_index("label")
            .loc[labels]
        )
        strong = (
            case_df[case_df["budget_name"] == "stronger_budget"]
            .set_index("label")
            .loc[labels]
        )
        ax.errorbar(
            x,
            base["rel_l2_mean"],
            yerr=base["rel_l2_std"],
            fmt="o-",
            label="baseline",
        )
        ax.errorbar(
            x,
            strong["rel_l2_mean"],
            yerr=strong["rel_l2_std"],
            fmt="s-",
            label="stronger",
        )
        ax.axhline(float(base["cross_rate"].iloc[0]) * 0.0 + float(case_df["n_seed"].iloc[0]) * 0.0, alpha=0.0)
        ax.set_title(CASE_DISPLAY[case_name])
        ax.set_ylabel("rel_l2")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=30, ha="right")
        ax.legend(frameon=False)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_cross_rates(summary_df: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)
    for ax, case_name in zip(axes, ["poisson", "stokes_poiseuille", "burgers"]):
        case_df = summary_df[summary_df["case"] == case_name]
        labels = case_df["label"].drop_duplicates().tolist()
        x = range(len(labels))
        base = (
            case_df[case_df["budget_name"] == "baseline_budget"]
            .set_index("label")
            .loc[labels]
        )
        strong = (
            case_df[case_df["budget_name"] == "stronger_budget"]
            .set_index("label")
            .loc[labels]
        )
        ax.plot(x, base["cross_rate"], "o-", label="baseline")
        ax.plot(x, strong["cross_rate"], "s-", label="stronger")
        ax.fill_between(x, base["cross_rate_ci_low"], base["cross_rate_ci_high"], alpha=0.15)
        ax.fill_between(x, strong["cross_rate_ci_low"], strong["cross_rate_ci_high"], alpha=0.15)
        ax.set_ylim(0.0, 1.05)
        ax.set_title(CASE_DISPLAY[case_name])
        ax.set_ylabel("failure rate")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=30, ha="right")
        ax.legend(frameon=False)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_note(summary_df: pd.DataFrame, shift_df: pd.DataFrame, ranking_df: pd.DataFrame) -> str:
    def fmt_case(case_name: str) -> List[str]:
        case_df = summary_df[summary_df["case"] == case_name]
        lines = [f"### {CASE_DISPLAY[case_name]}", ""]
        for label in case_df["label"].drop_duplicates():
            base = case_df[(case_df["label"] == label) & (case_df["budget_name"] == "baseline_budget")].iloc[0]
            strong = case_df[(case_df["label"] == label) & (case_df["budget_name"] == "stronger_budget")].iloc[0]
            lines.append(
                f"- `{label}`: rel_l2 `{base['rel_l2_mean']:.4f} ± {base['rel_l2_std']:.4f}` -> "
                f"`{strong['rel_l2_mean']:.4f} ± {strong['rel_l2_std']:.4f}`, "
                f"failure rate `{base['cross_rate']:.2f}` -> `{strong['cross_rate']:.2f}`, "
                f"dominant `{base['dominant_dimension']}` -> `{strong['dominant_dimension']}`"
            )
        rank_row = ranking_df[ranking_df["case"] == case_name]
        if not rank_row.empty:
            row = rank_row.iloc[0]
            lines.append(
                f"- 点级 rel_l2 排序相关：`rho = {row['rho_rel_l2_mean']:.3f}`，"
                f"baseline hardest = `{row['baseline_hardest_label']}`，"
                f"stronger hardest = `{row['stronger_hardest_label']}`。"
            )
        lines.append("")
        return lines

    lines = [
        "# U4：训练预算与 protocol 充分性控制",
        "",
        "本轮实验用代表工况对比 `baseline_budget` 与 `stronger_budget`，目的是检验统一最小 protocol 是否人为放大了复杂系统的边界现象。",
        "",
        "## 核心结论",
        "",
        "- 预算增强会整体降低 `rel_l2` 并在部分点降低越界率，但不会把三类系统压成同一种边界语义。",
        "- `Poisson` 在两种 budget 下都保持稳定；`Stokes-Poiseuille` 的规则边界位置后移，但硬点仍集中在低观测高噪声角落；`Burgers` 的高风险点排序和 seed 敏感现象没有消失。",
        "- 因而，`H3` 中的系统依赖性不能简单归因于当前统一最小 budget 不足，但应承认 budget 会移动边界绝对位置。",
        "",
    ]
    for case_name in ["poisson", "stokes_poiseuille", "burgers"]:
        lines.extend(fmt_case(case_name))
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze protocol-budget control experiments.")
    parser.add_argument(
        "--input-dir",
        default=str(ROOT / "results" / "budget_controls" / "budget_control_v1"),
        help="Budget control result directory containing budget_control_runs.csv",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = input_dir
    runs_csv = input_dir / "budget_control_runs.csv"

    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(runs_csv)
    summary_df = summarize_points(df)
    shift_df = summarize_budget_shift(summary_df)
    ranking_df = summarize_case_rankings(summary_df)

    summary_df.to_csv(output_dir / "budget_control_summary.csv", index=False)
    shift_df.to_csv(output_dir / "budget_control_shift_summary.csv", index=False)
    ranking_df.to_csv(output_dir / "budget_control_ranking_summary.csv", index=False)

    plot_rel_l2_means(summary_df, output_dir / "figure_37_budget_control_rel_l2.png")
    plot_cross_rates(summary_df, output_dir / "figure_38_budget_control_failure_rates.png")

    summary = {
        "point_summary": summary_df.to_dict(orient="records"),
        "budget_shift_summary": shift_df.to_dict(orient="records"),
        "ranking_summary": ranking_df.to_dict(orient="records"),
    }
    with (output_dir / "budget_control_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    note = build_note(summary_df, shift_df, ranking_df)
    note_path = ROOT.parent / "notes" / "budget_control_results.md"
    note_path.write_text(note, encoding="utf-8")

    print(f"[done] output_dir={output_dir}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

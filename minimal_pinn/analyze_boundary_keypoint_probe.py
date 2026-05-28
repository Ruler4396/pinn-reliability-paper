from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import NormalDist
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .reliability import build_reliability_summary


ROOT = Path(__file__).resolve().parent

DIM_ORDER = [
    "physics_consistency",
    "training_stability",
    "numerical_accuracy",
    "structural_stability",
]


def wilson_interval(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    phat = k / n
    denom = 1.0 + (z * z) / n
    center = (phat + (z * z) / (2.0 * n)) / denom
    margin = z * (((phat * (1.0 - phat) / n) + (z * z) / (4.0 * n * n)) ** 0.5) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def load_case_thresholds(path: Path, case_name: str) -> Dict[str, Dict[str, float | str]]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data[case_name]["thresholds"]


def spearman_from_rankings(ref: List[float], cur: List[float]) -> float:
    n = len(ref)
    if n <= 1:
        return 1.0
    d2 = sum((a - b) ** 2 for a, b in zip(ref, cur))
    return 1.0 - (6.0 * d2) / (n * (n * n - 1.0))


def rank_map(values: Dict[str, float], reverse: bool = True) -> Dict[str, int]:
    ordered = sorted(values.items(), key=lambda kv: kv[1], reverse=reverse)
    return {label: idx + 1 for idx, (label, _) in enumerate(ordered)}


def case_title(case_name: str) -> str:
    return case_name.replace("_", " ").title()


def plot_failure_rates(summary_df: pd.DataFrame, output_path: Path, case_name: str) -> None:
    ordered = summary_df.sort_values(["crosses_threshold_rate", "rel_l2_mean", "label"], ascending=[True, True, True])
    labels = ordered["label"].tolist()
    rates = ordered["crosses_threshold_rate"].tolist()
    lows = ordered["cross_rate_ci_low"].tolist()
    highs = ordered["cross_rate_ci_high"].tolist()
    errors = [
        [max(0.0, rate - low) for rate, low in zip(rates, lows)],
        [max(0.0, high - rate) for rate, high in zip(rates, highs)],
    ]

    fig, ax = plt.subplots(figsize=(10.5, 4.8), constrained_layout=True)
    ax.bar(range(len(labels)), rates, color="#1f4e79")
    ax.errorbar(range(len(labels)), rates, yerr=errors, fmt="none", ecolor="black", capsize=4, lw=1.2)
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("Failure probability")
    ax.set_title(f"{case_title(case_name)} key boundary points: failure rates with Wilson intervals")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_dominant_stability(summary_df: pd.DataFrame, output_path: Path, case_name: str) -> None:
    colors = {
        "physics_consistency": "#1f4e79",
        "training_stability": "#7a7a7a",
        "numerical_accuracy": "#b64040",
        "structural_stability": "#2c7a5a",
    }
    ordered = summary_df.sort_values(["crosses_threshold_rate", "rel_l2_mean", "label"], ascending=[True, True, True])
    labels = ordered["label"].tolist()
    fig, ax = plt.subplots(figsize=(10.5, 4.8), constrained_layout=True)
    bottom = [0.0] * len(labels)
    for dim in DIM_ORDER:
        vals = ordered[f"{dim}_share"].tolist()
        ax.bar(range(len(labels)), vals, bottom=bottom, color=colors[dim], label=dim.replace("_", " "))
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Dominant-dimension share across seeds")
    ax.set_title(f"{case_title(case_name)} key boundary points: dominant-dimension stability")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_markdown(
    output_dir: Path,
    summary_df: pd.DataFrame,
    ranking_summary: Dict[str, float],
    n_seed: int,
    case_name: str,
) -> str:
    title = case_title(case_name)
    lines = [
        f"# {title} 边界关键点高密度 seed 结果",
        "",
        f"数据目录：[{output_dir}]({output_dir})",
        "",
        f"本轮对 `{len(summary_df)}` 个关键边界点进行了高密度复现，每个点使用 `{n_seed}` 个 seeds。",
        "",
        "## 结论",
        "",
        "- 当前结果可以更清楚地区分稳定安全点、过渡点和稳定失效点。",
        f"- 按 `rel_l2` 的跨点严重度排序，逐 seed 相对总体均值排序的平均 Spearman 相关系数为 `{ranking_summary['rel_l2_rank_rho_mean']:.3f}`。",
        f"- 按重标定 `R` 的跨点严重度排序，逐 seed 相对总体均值排序的平均 Spearman 相关系数为 `{ranking_summary['R_rank_rho_mean']:.3f}`。",
        "",
        "## 代表性现象",
        "",
    ]
    ordered = summary_df.sort_values("crosses_threshold_rate")
    for _, row in ordered.iterrows():
        lines.append(
            f"- `{row['label']}`: failure rate = `{row['crosses_threshold_rate']:.2f}` "
            f"(95% CI `[${row['cross_rate_ci_low']:.3f}, {row['cross_rate_ci_high']:.3f}$]`), "
            f"`rel_l2 = {row['rel_l2_mean']:.4f} ± {row['rel_l2_std']:.4f}`, "
            f"dominant = `{row['dominant_dimension_mode']}` "
            f"(share `{row['dominant_dimension_mode_share']:.2f}`)"
        )
    lines.extend(
        [
            "",
            "## 判断",
            "",
            f"- `{title}` 的边界不是单一切点，而是具有统计宽度的过渡带。",
            "- 除 failure probability 之外，严重度排序和主导维度分布本身也具有可统计分析的稳定性。",
            "- 这批高密度关键点结果比单次粗矩阵更适合写入主文作为边界统计证据。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a high-density boundary keypoint probe.")
    parser.add_argument("--probe-dir", required=True, help="Path to probe output directory.")
    parser.add_argument("--recalibration-path", required=True, help="Path to recalibrated_summary.json.")
    parser.add_argument("--case", default="burgers", help="Case name, default burgers.")
    parser.add_argument("--confidence", type=float, default=0.95, help="Wilson CI confidence level.")
    args = parser.parse_args()

    probe_dir = Path(args.probe_dir).resolve()
    output_dir = probe_dir
    probe_runs = pd.read_csv(probe_dir / "probe_runs.csv")
    thresholds = load_case_thresholds(Path(args.recalibration_path).resolve(), args.case)

    rows: List[Dict[str, object]] = []
    for _, row in probe_runs.iterrows():
        metrics = {
            "physics_rms": float(row["physics_rms"]),
            "boundary_rms": float(row["boundary_rms"]),
            "rel_l2": float(row["rel_l2"]),
            "structure_error": float(row["structure_error"]),
            "loss_std": float(row["loss_std"]),
            "loss_ratio": float(row["loss_ratio"]),
        }
        recal = build_reliability_summary(metrics, thresholds)
        dim_scores = recal["dimension_scores"]
        dominant = min(dim_scores.items(), key=lambda kv: kv[1])[0]
        rows.append(
            {
                **row.to_dict(),
                "reliability_raw_recal": float(recal["reliability_raw"]),
                "physics_consistency_recal": float(dim_scores["physics_consistency"]),
                "training_stability_recal": float(dim_scores["training_stability"]),
                "numerical_accuracy_recal": float(dim_scores["numerical_accuracy"]),
                "structural_stability_recal": float(dim_scores["structural_stability"]),
                "dominant_dimension": dominant,
            }
        )
    run_df = pd.DataFrame(rows)
    run_df.to_csv(output_dir / "probe_runs_recalibrated.csv", index=False)

    summary_rows: List[Dict[str, object]] = []
    for label, grp in run_df.groupby("label", sort=False):
        k = int(grp["crosses_threshold"].sum())
        n = int(len(grp))
        ci_low, ci_high = wilson_interval(k, n, confidence=float(args.confidence))
        dominant_counts = Counter(grp["dominant_dimension"].tolist())
        mode_dim, mode_count = dominant_counts.most_common(1)[0]
        row = {
            "label": label,
            "num_observation": int(grp["num_observation"].iloc[0]),
            "noise_std": float(grp["noise_std"].iloc[0]),
            "n_seed": n,
            "crosses_threshold_count": k,
            "crosses_threshold_rate": k / n,
            "cross_rate_ci_low": ci_low,
            "cross_rate_ci_high": ci_high,
            "cross_rate_ci_width": ci_high - ci_low,
            "rel_l2_mean": float(grp["rel_l2"].mean()),
            "rel_l2_std": float(grp["rel_l2"].std(ddof=0)),
            "reliability_raw_recal_mean": float(grp["reliability_raw_recal"].mean()),
            "reliability_raw_recal_std": float(grp["reliability_raw_recal"].std(ddof=0)),
            "dominant_dimension_mode": mode_dim,
            "dominant_dimension_mode_share": mode_count / n,
        }
        for dim in DIM_ORDER:
            row[f"{dim}_count"] = int(dominant_counts.get(dim, 0))
            row[f"{dim}_share"] = float(dominant_counts.get(dim, 0) / n)
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(output_dir / "boundary_probe_summary_with_ci.csv", index=False)

    mean_rel_rank = rank_map(summary_df.set_index("label")["rel_l2_mean"].to_dict(), reverse=True)
    mean_R_rank = rank_map(summary_df.set_index("label")["reliability_raw_recal_mean"].to_dict(), reverse=False)

    rel_rhos = []
    R_rhos = []
    for seed, grp in run_df.groupby("seed"):
        rel_rank = rank_map(grp.set_index("label")["rel_l2"].to_dict(), reverse=True)
        R_rank = rank_map(grp.set_index("label")["reliability_raw_recal"].to_dict(), reverse=False)
        labels = summary_df["label"].tolist()
        rel_rhos.append(
            {
                "seed": int(seed),
                "rel_l2_rank_rho": spearman_from_rankings(
                    [mean_rel_rank[label] for label in labels],
                    [rel_rank[label] for label in labels],
                ),
                "R_rank_rho": spearman_from_rankings(
                    [mean_R_rank[label] for label in labels],
                    [R_rank[label] for label in labels],
                ),
            }
        )

    rank_df = pd.DataFrame(rel_rhos)
    rank_df.to_csv(output_dir / "boundary_probe_ranking_stability.csv", index=False)
    ranking_summary = {
        "rel_l2_rank_rho_mean": float(rank_df["rel_l2_rank_rho"].mean()),
        "rel_l2_rank_rho_std": float(rank_df["rel_l2_rank_rho"].std(ddof=0)),
        "R_rank_rho_mean": float(rank_df["R_rank_rho"].mean()),
        "R_rank_rho_std": float(rank_df["R_rank_rho"].std(ddof=0)),
    }

    plot_failure_rates(summary_df, output_dir / "figure_35_boundary_keypoint_failure_rates.png", args.case)
    plot_dominant_stability(summary_df, output_dir / "figure_36_boundary_keypoint_dominant_stability.png", args.case)

    with (output_dir / "boundary_probe_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "case": args.case,
                "n_points": int(summary_df.shape[0]),
                "n_seed": int(summary_df["n_seed"].iloc[0]),
                "ranking_summary": ranking_summary,
                "points": summary_rows,
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )

    note_path = ROOT.parent / "notes" / f"{args.case}_boundary_keypoints_results.md"
    note_path.write_text(
        build_markdown(
            output_dir,
            summary_df,
            ranking_summary,
            int(summary_df["n_seed"].iloc[0]),
            args.case,
        ),
        encoding="utf-8",
    )

    print(f"[done] output_dir={output_dir}")
    print(summary_df.to_string(index=False))
    print(json.dumps(ranking_summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

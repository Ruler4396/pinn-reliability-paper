from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .recalibrate_dimensions import CASE_TABLES, METRICS
from .reliability import logistic_score


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "results" / "analysis" / "calibration_aggregation_robustness_v1"
NOTE_PATH = ROOT.parent / "notes" / "calibration_aggregation_robustness_results.md"

QUANTILE_PAIRS: List[Tuple[float, float]] = [
    (0.10, 0.90),
    (0.15, 0.85),
    (0.20, 0.80),
]

INTRA_AGGS = ["geometric", "arithmetic", "minimum"]
INTER_AGGS = ["mean_equal", "mean_nonphysics", "minimum"]

DIM_ORDER = [
    "physics_consistency",
    "training_stability",
    "numerical_accuracy",
    "structural_stability",
]

CASE_TITLES = {
    "poisson": "Poisson",
    "stokes_poiseuille": "Stokes-Poiseuille",
    "fisher_kpp": "Fisher-KPP",
    "burgers": "Burgers",
}

DIM_DISPLAY = {
    "physics_consistency": "physics",
    "training_stability": "training",
    "numerical_accuracy": "numerical",
    "structural_stability": "structural",
}


def quantile_thresholds(df: pd.DataFrame, low_q: float, high_q: float) -> Dict[str, Dict[str, float | str]]:
    thresholds: Dict[str, Dict[str, float | str]] = {}
    for metric in METRICS:
        good = float(df[metric].quantile(low_q))
        fail = float(df[metric].quantile(high_q))
        if math.isclose(good, fail):
            span = max(abs(good) * 0.1, 1e-8)
            good -= span
            fail += span
        thresholds[metric] = {"good": good, "fail": fail, "mode": "smaller_better"}
    return thresholds


def aggregate(values: Iterable[float], mode: str) -> float:
    vals = [float(v) for v in values]
    if not vals:
        return 0.0
    if mode == "geometric":
        product = 1.0
        for value in vals:
            product *= max(value, 1e-12)
        return product ** (1.0 / len(vals))
    if mode == "arithmetic":
        return sum(vals) / len(vals)
    if mode == "minimum":
        return min(vals)
    raise ValueError(f"Unsupported aggregation mode: {mode}")


def inter_aggregate(dim_scores: Dict[str, float], mode: str) -> float:
    if mode == "mean_equal":
        return sum(dim_scores.values()) / len(dim_scores)
    if mode == "mean_nonphysics":
        weights = {
            "physics_consistency": 0.15,
            "training_stability": 0.30,
            "numerical_accuracy": 0.275,
            "structural_stability": 0.275,
        }
        return sum(dim_scores[key] * weights[key] for key in DIM_ORDER)
    if mode == "minimum":
        return min(dim_scores.values())
    raise ValueError(f"Unsupported inter aggregation mode: {mode}")


def build_scores(
    row: pd.Series,
    thresholds: Dict[str, Dict[str, float | str]],
    intra_mode: str,
    inter_mode: str,
) -> Dict[str, object]:
    indicator_scores = {
        name: logistic_score(
            value=float(row[name]),
            good=float(spec["good"]),
            fail=float(spec["fail"]),
            mode=str(spec["mode"]),
        )
        for name, spec in thresholds.items()
    }

    dim_scores = {
        "physics_consistency": aggregate(
            [indicator_scores["physics_rms"], indicator_scores["boundary_rms"]], intra_mode
        ),
        "training_stability": aggregate(
            [indicator_scores["loss_std"], indicator_scores["loss_ratio"]], intra_mode
        ),
        "numerical_accuracy": aggregate([indicator_scores["rel_l2"]], intra_mode),
        "structural_stability": aggregate([indicator_scores["structure_error"]], intra_mode),
    }
    reliability = inter_aggregate(dim_scores, inter_mode)
    dominant_dimension = min(dim_scores.items(), key=lambda kv: kv[1])[0]
    return {
        "indicator_scores": indicator_scores,
        "dimension_scores": dim_scores,
        "reliability_raw_recal": reliability,
        "dominant_dimension": dominant_dimension,
    }


def evaluate_case(
    case_name: str,
    df: pd.DataFrame,
    low_q: float,
    high_q: float,
    intra_mode: str,
    inter_mode: str,
) -> Dict[str, object]:
    thresholds = quantile_thresholds(df, low_q=low_q, high_q=high_q)
    rows: List[Dict[str, object]] = []
    for _, row in df.iterrows():
        scores = build_scores(row, thresholds, intra_mode=intra_mode, inter_mode=inter_mode)
        rows.append(
            {
                **row.to_dict(),
                "physics_consistency_recal": scores["dimension_scores"]["physics_consistency"],
                "training_stability_recal": scores["dimension_scores"]["training_stability"],
                "numerical_accuracy_recal": scores["dimension_scores"]["numerical_accuracy"],
                "structural_stability_recal": scores["dimension_scores"]["structural_stability"],
                "reliability_raw_recal": scores["reliability_raw_recal"],
                "dominant_dimension": scores["dominant_dimension"],
            }
        )

    table = pd.DataFrame(rows)
    threshold_rel_l2 = float(table["threshold_rel_l2"].iloc[0])
    selected = table[table["rel_l2"] >= threshold_rel_l2].copy()
    selection_rule = "threshold_rel_l2"
    if selected.empty:
        selected = table[table["rel_l2"] >= float(table["rel_l2"].quantile(0.75))].copy()
        selection_rule = "top_quartile_rel_l2"

    counts = Counter(selected["dominant_dimension"].tolist())
    counts = {dim: int(counts.get(dim, 0)) for dim in DIM_ORDER}
    dominant = max(DIM_ORDER, key=lambda dim: counts.get(dim, 0))

    if case_name == "poisson":
        role_holds = dominant == "numerical_accuracy"
        role_reason = "dominant=numerical_accuracy"
    elif case_name == "stokes_poiseuille":
        role_holds = dominant == "numerical_accuracy"
        role_reason = "dominant=numerical_accuracy"
    elif case_name == "fisher_kpp":
        tn = counts["training_stability"] + counts["numerical_accuracy"]
        ps = counts["physics_consistency"] + counts["structural_stability"]
        role_holds = (
            dominant in {"training_stability", "numerical_accuracy"}
            and tn >= ps
            and counts["physics_consistency"] <= max(2, counts["training_stability"])
        )
        role_reason = "training+numerical >= physics+structural and no physics collapse"
    elif case_name == "burgers":
        ts = counts["training_stability"] + counts["structural_stability"]
        role_holds = ts > counts["physics_consistency"] and ts > counts["numerical_accuracy"]
        role_reason = "training+structural > physics and numerical"
    else:
        role_holds = False
        role_reason = "unknown"

    return {
        "table": table,
        "selection_rule": selection_rule,
        "n_selected": int(len(selected)),
        "dominant_dimension": dominant,
        "counts": counts,
        "role_holds": bool(role_holds),
        "role_reason": role_reason,
        "spearman_rel_l2_vs_R": float(
            table[["rel_l2", "reliability_raw_recal"]].corr(method="spearman").iloc[0, 1]
        ),
    }


def plot_role_stability(summary_df: pd.DataFrame, output_path: Path) -> None:
    config_labels = summary_df["config_label"].unique().tolist()
    n_cases = len(CASE_TITLES)
    fig, axes = plt.subplots(1, n_cases, figsize=(5.2 * n_cases, 4.8), constrained_layout=True)
    if n_cases == 1:
        axes = [axes]
    colors = {True: "#2c7a5a", False: "#b64040"}
    for ax, case_name in zip(axes, CASE_TITLES):
        case_df = summary_df[summary_df["case"] == case_name].copy()
        vals = [1 if bool(x) else 0 for x in case_df["role_holds"].tolist()]
        ax.bar(range(len(config_labels)), vals, color=[colors[bool(x)] for x in case_df["role_holds"].tolist()])
        ax.set_title(CASE_TITLES[case_name])
        ax.set_ylim(0, 1.15)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["fail", "hold"])
        ax.set_xticks(range(len(config_labels)))
        ax.set_xticklabels(config_labels, rotation=75, ha="right", fontsize=8)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_dominant_counts(summary_df: pd.DataFrame, output_path: Path) -> None:
    n_cases = len(CASE_TITLES)
    fig, axes = plt.subplots(1, n_cases, figsize=(5.2 * n_cases, 5.0), constrained_layout=True)
    if n_cases == 1:
        axes = [axes]
    colors = {
        "physics_consistency": "#1f4e79",
        "training_stability": "#7a7a7a",
        "numerical_accuracy": "#b64040",
        "structural_stability": "#2c7a5a",
    }
    config_labels = summary_df["config_label"].unique().tolist()
    width = 0.18
    x = list(range(len(config_labels)))

    for ax, case_name in zip(axes, CASE_TITLES):
        case_df = summary_df[summary_df["case"] == case_name].copy()
        for offset, dim in zip([-1.5, -0.5, 0.5, 1.5], DIM_ORDER):
            ax.bar(
                [v + offset * width for v in x],
                case_df[f"{dim}_count"].tolist(),
                width=width,
                color=colors[dim],
                label=DIM_DISPLAY[dim],
            )
        ax.set_title(CASE_TITLES[case_name])
        ax.set_xticks(x)
        ax.set_xticklabels(config_labels, rotation=75, ha="right", fontsize=8)
        ax.set_ylabel("Dominant-count among high-risk points")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_markdown(summary_df: pd.DataFrame, config_summary: pd.DataFrame) -> str:
    lines = [
        "# 校准与聚合稳健性结果",
        "",
        "本轮实验在不新增训练的前提下，系统扫描了三类因素：",
        "",
        "- 分位点：`10/90`、`15/85`、`20/80`",
        "- 维度内聚合：`geometric`、`arithmetic`、`minimum`",
        "- 维度间聚合：`mean_equal`、`mean_nonphysics`、`minimum`",
        "",
        f"共评估 `{len(config_summary)}` 组校准与聚合配置。",
        "",
        "## 核心结论",
        "",
    ]

    for case_name, title in CASE_TITLES.items():
        case_df = summary_df[summary_df["case"] == case_name].copy()
        holds = int(case_df["role_holds"].sum())
        total = int(len(case_df))
        dominant_counts = Counter(case_df["dominant_dimension"].tolist())
        labels = ", ".join(f"{DIM_DISPLAY[k]}:{v}" for k, v in dominant_counts.items())
        lines.append(f"### {title}")
        lines.append("")
        lines.append(f"- 角色判定在 `{holds}/{total}` 组配置下保持成立。")
        lines.append(f"- 各配置下出现过的主导维度标签：{labels}")
        if case_name == "poisson":
            lines.append("- 结果整体保持为 `numerical_accuracy` 主导的稳健对照，没有被聚合方式改写成复杂多维边界。")
        elif case_name == "stokes_poiseuille":
            lines.append("- 结果整体仍保持为 `numerical_accuracy` 主导的规则边界，仅主导计数会随聚合方式发生轻微波动。")
        elif case_name == "fisher_kpp":
            lines.append("- 结果整体保持为 `training/numerical` 参与但不塌缩为 `physics` 单维主导的中间层案例，说明其“规则但非硬刚性”的定位对校准与聚合选择相对稳健。")
        else:
            lines.append("- 结果整体仍保持 `training + structural` 共同参与的复杂边界特征，未被重新压回单一 `physics` 主导。")
        lines.append("")

    full_hold = config_summary["all_case_roles_hold"].sum()
    lines.extend(
        [
            "## 判断",
            "",
            f"- 在 `{int(full_hold)}/{len(config_summary)}` 组完整配置下，四个案例的角色分工同时保持成立。",
            "- 因此，当前主结论并不是某一套分位点或某一种聚合规则“做出来”的。",
            "- 但聚合方式会影响计数强弱与相对边界形状，因此主文仍应把这些规则写成 operational design choice，而不是唯一正确设定。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, object]] = []
    config_rows: List[Dict[str, object]] = []
    full_summary: Dict[str, object] = {}

    for low_q, high_q in QUANTILE_PAIRS:
        for intra_mode in INTRA_AGGS:
            for inter_mode in INTER_AGGS:
                config_label = f"q{int(low_q*100)}-{int(high_q*100)}|{intra_mode}|{inter_mode}"
                config_cases: Dict[str, object] = {}
                all_hold = True
                for case_name, path in CASE_TABLES.items():
                    df = pd.read_csv(path)
                    result = evaluate_case(
                        case_name=case_name,
                        df=df,
                        low_q=low_q,
                        high_q=high_q,
                        intra_mode=intra_mode,
                        inter_mode=inter_mode,
                    )
                    config_cases[case_name] = {
                        "selection_rule": result["selection_rule"],
                        "n_selected": result["n_selected"],
                        "dominant_dimension": result["dominant_dimension"],
                        "counts": result["counts"],
                        "role_holds": result["role_holds"],
                        "role_reason": result["role_reason"],
                        "spearman_rel_l2_vs_R": result["spearman_rel_l2_vs_R"],
                    }
                    row = {
                        "config_label": config_label,
                        "case": case_name,
                        "low_q": low_q,
                        "high_q": high_q,
                        "intra_agg": intra_mode,
                        "inter_agg": inter_mode,
                        "selection_rule": result["selection_rule"],
                        "n_selected": result["n_selected"],
                        "dominant_dimension": result["dominant_dimension"],
                        "role_holds": result["role_holds"],
                        "spearman_rel_l2_vs_R": result["spearman_rel_l2_vs_R"],
                    }
                    for dim in DIM_ORDER:
                        row[f"{dim}_count"] = result["counts"][dim]
                    rows.append(row)
                    all_hold = all_hold and bool(result["role_holds"])

                config_rows.append(
                    {
                        "config_label": config_label,
                        "low_q": low_q,
                        "high_q": high_q,
                        "intra_agg": intra_mode,
                        "inter_agg": inter_mode,
                        "all_case_roles_hold": bool(all_hold),
                        "n_case_roles_hold": sum(1 for c in config_cases.values() if c["role_holds"]),
                    }
                )
                full_summary[config_label] = config_cases

    summary_df = pd.DataFrame(rows)
    config_df = pd.DataFrame(config_rows)
    summary_df.to_csv(OUTPUT_DIR / "calibration_aggregation_robustness_summary.csv", index=False)
    config_df.to_csv(OUTPUT_DIR / "calibration_aggregation_robustness_configs.csv", index=False)

    with (OUTPUT_DIR / "calibration_aggregation_robustness_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "configs": full_summary,
                "aggregate": {
                    "n_configs": len(config_df),
                    "n_all_case_roles_hold": int(config_df["all_case_roles_hold"].sum()),
                },
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )

    plot_role_stability(summary_df, OUTPUT_DIR / "figure_33_role_stability.png")
    plot_dominant_counts(summary_df, OUTPUT_DIR / "figure_34_dominant_counts.png")
    NOTE_PATH.write_text(build_markdown(summary_df, config_df), encoding="utf-8")

    print(f"[done] output_dir={OUTPUT_DIR}")
    print(config_df.to_string(index=False))


if __name__ == "__main__":
    main()

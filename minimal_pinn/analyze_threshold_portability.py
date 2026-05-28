from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "results" / "variant_robustness" / "variant_robustness_v2"
OUTPUT_DIR = ROOT / "results" / "analysis" / "threshold_portability_v1"

CASE_ORDER = ["poisson", "stokes_poiseuille", "fisher_kpp", "burgers"]
CASE_TITLES = {
    "poisson": "Poisson",
    "stokes_poiseuille": "Stokes-Poiseuille",
    "fisher_kpp": "Fisher-KPP",
    "burgers": "Burgers",
}
VARIANT_ORDER = ["baseline", "capacity_v1", "weight_balanced_v2"]
R_RELIABLE_CUTOFF = 0.9
R_UNRELIABLE_CUTOFF = 0.7
SEVERITY_MAP = {
    ("poisson", "safe_obs256_noise000"): 0,
    ("poisson", "degraded_obs8_noise020"): 1,
    ("stokes_poiseuille", "safe_obs64_noise000"): 0,
    ("stokes_poiseuille", "critical_obs8_noise0125"): 1,
    ("stokes_poiseuille", "failure_obs8_noise0175"): 2,
    ("fisher_kpp", "safe_obs64_noise000"): 0,
    ("fisher_kpp", "edge_obs16_noise005"): 1,
    ("fisher_kpp", "transition_obs128_noise020"): 2,
    ("fisher_kpp", "failure_obs16_noise030"): 3,
    ("burgers", "safe_obs64_noise005"): 0,
    ("burgers", "transition_obs48_noise010"): 1,
    ("burgers", "seed_sensitive_obs32_noise010"): 2,
    ("burgers", "failure_obs32_noise0175"): 3,
}


def r_regime(value: float) -> str:
    if value >= R_RELIABLE_CUTOFF:
        return "reliable"
    if value >= R_UNRELIABLE_CUTOFF:
        return "critical"
    return "unreliable"


def majority_label(series: pd.Series) -> str:
    counts = series.value_counts()
    return str(counts.index[0])


def load_runs() -> pd.DataFrame:
    return pd.read_csv(INPUT_DIR / "point_runs.csv")


def build_threshold_reference(runs: pd.DataFrame) -> pd.DataFrame:
    case_thresholds = runs.groupby("case")["threshold_rel_l2"].first().rename("absolute_threshold_rel_l2")
    safe_mask = runs["label"].str.startswith("safe_")

    baseline_safe = (
        runs[safe_mask & (runs["variant"] == "baseline")]
        .groupby("case")["rel_l2"]
        .mean()
        .rename("baseline_safe_rel_l2_mean")
    )
    out = pd.concat([case_thresholds, baseline_safe], axis=1).reset_index()
    out["relative_factor_vs_safe"] = out["absolute_threshold_rel_l2"] / out["baseline_safe_rel_l2_mean"]

    variant_safe = (
        runs[safe_mask]
        .groupby(["case", "variant"])["rel_l2"]
        .mean()
        .rename("variant_safe_rel_l2_mean")
        .reset_index()
    )
    out = variant_safe.merge(out, on="case", how="left")
    out["variant_relative_threshold_rel_l2"] = out["relative_factor_vs_safe"] * out["variant_safe_rel_l2_mean"]
    return out.sort_values(["case", "variant"])


def attach_rule_columns(runs: pd.DataFrame, threshold_ref: pd.DataFrame) -> pd.DataFrame:
    out = runs.merge(
        threshold_ref[["case", "variant", "variant_relative_threshold_rel_l2"]],
        on=["case", "variant"],
        how="left",
    )
    out["cross_abs_threshold"] = out["rel_l2"] >= out["threshold_rel_l2"]
    out["cross_relative_threshold"] = out["rel_l2"] >= out["variant_relative_threshold_rel_l2"]
    out["r_regime"] = out["reliability_raw_recal"].map(r_regime)
    out["r_unreliable"] = out["reliability_raw_recal"] < R_UNRELIABLE_CUTOFF
    return out


def aggregate_point_rules(runs: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        runs.groupby(["case", "label", "variant"])
        .agg(
            n_seed=("seed", "count"),
            rel_l2_mean=("rel_l2", "mean"),
            rel_l2_std=("rel_l2", "std"),
            r_mean=("reliability_raw_recal", "mean"),
            r_std=("reliability_raw_recal", "std"),
            abs_cross_rate=("cross_abs_threshold", "mean"),
            relative_cross_rate=("cross_relative_threshold", "mean"),
            r_unreliable_rate=("r_unreliable", "mean"),
            abs_majority=("cross_abs_threshold", lambda s: "cross" if float(s.mean()) >= 0.5 else "safe"),
            relative_majority=("cross_relative_threshold", lambda s: "cross" if float(s.mean()) >= 0.5 else "safe"),
            r_majority=("r_regime", majority_label),
            variant_relative_threshold_rel_l2=("variant_relative_threshold_rel_l2", "first"),
            absolute_threshold_rel_l2=("threshold_rel_l2", "first"),
        )
        .reset_index()
    )
    return grouped


def build_disagreement_summary(point_summary: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for (case, label), group in point_summary.groupby(["case", "label"]):
        rows.append(
            {
                "case": case,
                "label": label,
                "abs_cross_span": float(group["abs_cross_rate"].max() - group["abs_cross_rate"].min()),
                "relative_cross_span": float(group["relative_cross_rate"].max() - group["relative_cross_rate"].min()),
                "r_unreliable_span": float(group["r_unreliable_rate"].max() - group["r_unreliable_rate"].min()),
                "r_mean_span": float(group["r_mean"].max() - group["r_mean"].min()),
                "abs_majority_unique_count": int(group["abs_majority"].nunique()),
                "relative_majority_unique_count": int(group["relative_majority"].nunique()),
                "r_majority_unique_count": int(group["r_majority"].nunique()),
            }
        )
    return pd.DataFrame(rows).sort_values(["case", "label"])


def build_case_rule_summary(disagreement: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for case, group in disagreement.groupby("case"):
        rows.append(
            {
                "case": case,
                "mean_abs_cross_span": float(group["abs_cross_span"].mean()),
                "mean_relative_cross_span": float(group["relative_cross_span"].mean()),
                "mean_r_unreliable_span": float(group["r_unreliable_span"].mean()),
                "mean_r_mean_span": float(group["r_mean_span"].mean()),
                "abs_majority_disagreement_fraction": float((group["abs_majority_unique_count"] > 1).mean()),
                "relative_majority_disagreement_fraction": float((group["relative_majority_unique_count"] > 1).mean()),
                "r_majority_disagreement_fraction": float((group["r_majority_unique_count"] > 1).mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("case")


def spearman_rank(x: pd.Series, y: pd.Series) -> float:
    return float(x.corr(y, method="spearman"))


def build_severity_ordering_summary(point_summary: pd.DataFrame) -> pd.DataFrame:
    df = point_summary.copy()
    df["severity_rank"] = [SEVERITY_MAP[(case, label)] for case, label in zip(df["case"], df["label"])]
    rows: List[Dict[str, object]] = []
    for (case, variant), group in df.groupby(["case", "variant"]):
        rows.append(
            {
                "case": case,
                "variant": variant,
                "rho_severity_vs_rel_l2": spearman_rank(group["severity_rank"], group["rel_l2_mean"]),
                "rho_severity_vs_neg_r": spearman_rank(group["severity_rank"], -group["r_mean"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["case", "variant"])


def plot_rule_spans(case_rule_summary: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 4.6), constrained_layout=True)
    x = range(len(case_rule_summary))
    width = 0.22
    ax.bar(
        [i - width for i in x],
        case_rule_summary["mean_abs_cross_span"],
        width=width,
        label="Fixed rel_l2 threshold",
        color="#b64040",
    )
    ax.bar(
        x,
        case_rule_summary["mean_relative_cross_span"],
        width=width,
        label="Variant-relative rel_l2 threshold",
        color="#1f4e79",
    )
    ax.bar(
        [i + width for i in x],
        case_rule_summary["mean_r_unreliable_span"],
        width=width,
        label="R < 0.7 regime rate",
        color="#2c7a5a",
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels([CASE_TITLES[c] for c in case_rule_summary["case"]])
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("Mean cross-variant disagreement span")
    ax.set_title("Cross-variant threshold disagreement by rule")
    ax.legend(frameon=False, fontsize=9)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_severity_ordering(ordering: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2), constrained_layout=True, sharey=True)
    for ax, case in zip(axes, CASE_ORDER):
        case_df = ordering[ordering["case"] == case].set_index("variant").reindex(VARIANT_ORDER).reset_index()
        x = range(len(case_df))
        width = 0.32
        ax.bar(
            [i - width / 2 for i in x],
            case_df["rho_severity_vs_rel_l2"],
            width=width,
            label="rel_l2",
            color="#b64040",
        )
        ax.bar(
            [i + width / 2 for i in x],
            case_df["rho_severity_vs_neg_r"],
            width=width,
            label="-R",
            color="#1f4e79",
        )
        ax.set_xticks(list(x))
        ax.set_xticklabels(case_df["variant"], rotation=20, ha="right")
        ax.set_title(CASE_TITLES[case])
        ax.set_ylim(0.0, 1.05)
        ax.set_ylabel("Spearman rho vs severity rank")
    axes[0].legend(frameon=False, fontsize=9, loc="lower right")
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_summary_json(
    threshold_ref: pd.DataFrame,
    case_rule_summary: pd.DataFrame,
    ordering_summary: pd.DataFrame,
    disagreement: pd.DataFrame,
) -> Dict[str, object]:
    out: Dict[str, object] = {
        "r_cutoffs": {
            "reliable": R_RELIABLE_CUTOFF,
            "unreliable": R_UNRELIABLE_CUTOFF,
        },
        "cases": {},
    }
    for case in CASE_ORDER:
        case_thresholds = threshold_ref[threshold_ref["case"] == case]
        case_rules = case_rule_summary[case_rule_summary["case"] == case].iloc[0].to_dict()
        case_ordering = (
            ordering_summary[ordering_summary["case"] == case]
            .set_index("variant")[["rho_severity_vs_rel_l2", "rho_severity_vs_neg_r"]]
            .to_dict(orient="index")
        )
        case_disagreement = disagreement[disagreement["case"] == case]
        out["cases"][case] = {
            "threshold_reference": case_thresholds.to_dict(orient="records"),
            "rule_portability": case_rules,
            "severity_ordering": case_ordering,
            "worst_abs_span_label": case_disagreement.sort_values("abs_cross_span", ascending=False).iloc[0][
                ["label", "abs_cross_span"]
            ].to_dict(),
            "worst_relative_span_label": case_disagreement.sort_values("relative_cross_span", ascending=False).iloc[0][
                ["label", "relative_cross_span"]
            ].to_dict(),
            "worst_r_span_label": case_disagreement.sort_values("r_unreliable_span", ascending=False).iloc[0][
                ["label", "r_unreliable_span"]
            ].to_dict(),
        }
    return out


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    runs = load_runs()
    threshold_ref = build_threshold_reference(runs)
    enriched_runs = attach_rule_columns(runs, threshold_ref)
    point_summary = aggregate_point_rules(enriched_runs)
    disagreement = build_disagreement_summary(point_summary)
    case_rule_summary = build_case_rule_summary(disagreement)
    ordering_summary = build_severity_ordering_summary(point_summary)
    summary = build_summary_json(threshold_ref, case_rule_summary, ordering_summary, disagreement)

    threshold_ref.to_csv(OUTPUT_DIR / "threshold_reference.csv", index=False)
    point_summary.to_csv(OUTPUT_DIR / "point_portability_summary.csv", index=False)
    disagreement.to_csv(OUTPUT_DIR / "label_disagreement_summary.csv", index=False)
    case_rule_summary.to_csv(OUTPUT_DIR / "case_rule_portability_summary.csv", index=False)
    ordering_summary.to_csv(OUTPUT_DIR / "severity_ordering_summary.csv", index=False)

    plot_rule_spans(case_rule_summary, OUTPUT_DIR / "figure_23_rule_portability_spans.png")
    plot_severity_ordering(ordering_summary, OUTPUT_DIR / "figure_24_severity_ordering.png")

    with (OUTPUT_DIR / "threshold_portability_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(f"[done] output_dir={OUTPUT_DIR}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

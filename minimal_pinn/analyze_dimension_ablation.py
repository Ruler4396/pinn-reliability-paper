from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "results" / "analysis" / "recalibrated_dimensions_v1"
OUTPUT_DIR = ROOT / "results" / "analysis" / "dimension_ablation_v1"
NOTE_PATH = ROOT.parent / "notes" / "dimension_ablation_results.md"

CASE_TABLES = {
    "poisson": INPUT_DIR / "poisson_recalibrated_table.csv",
    "burgers": INPUT_DIR / "burgers_recalibrated_table.csv",
    "stokes_poiseuille": INPUT_DIR / "stokes_poiseuille_recalibrated_table.csv",
    "fisher_kpp": INPUT_DIR / "fisher_kpp_recalibrated_table.csv",
}

CASE_TITLES = {
    "poisson": "Poisson",
    "burgers": "Burgers",
    "stokes_poiseuille": "Stokes-Poiseuille",
    "fisher_kpp": "Fisher-KPP",
}

SCORE_COLS = {
    "full_R": "reliability_raw_recal",
    "rel_l2_only": "numerical_accuracy_recal",
    "physics_only": "physics_consistency_recal",
}

DIM_COLS = [
    "physics_consistency_recal",
    "training_stability_recal",
    "numerical_accuracy_recal",
    "structural_stability_recal",
]


def add_ablation_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["R_minus_phy"] = (
        out["training_stability_recal"] + out["numerical_accuracy_recal"] + out["structural_stability_recal"]
    ) / 3.0
    out["R_minus_train"] = (
        out["physics_consistency_recal"] + out["numerical_accuracy_recal"] + out["structural_stability_recal"]
    ) / 3.0
    out["R_minus_num"] = (
        out["physics_consistency_recal"] + out["training_stability_recal"] + out["structural_stability_recal"]
    ) / 3.0
    out["R_minus_str"] = (
        out["physics_consistency_recal"] + out["training_stability_recal"] + out["numerical_accuracy_recal"]
    ) / 3.0
    return out


def worst_set(df: pd.DataFrame, score_col: str, k: int) -> set[str]:
    ranked = df.sort_values(score_col, ascending=True).head(k)
    return set(ranked["run_name"].tolist())


def jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def unique_mean(df: pd.DataFrame, run_names: set[str], metric_col: str) -> float | None:
    if not run_names:
        return None
    return float(df[df["run_name"].isin(run_names)][metric_col].mean())


def analyze_case(case_name: str, df: pd.DataFrame) -> Dict[str, object]:
    df = add_ablation_scores(df)
    k = max(1, math.ceil(len(df) * 0.2))

    full_set = worst_set(df, "reliability_raw_recal", k)
    rel2_set = worst_set(df, "numerical_accuracy_recal", k)
    physics_set = worst_set(df, "physics_consistency_recal", k)

    full_only_vs_rel2 = full_set - rel2_set
    rel2_only_vs_full = rel2_set - full_set

    summary = {
        "n_points": int(len(df)),
        "top_k": int(k),
        "single_indicator_overlap": {
            "full_vs_rel_l2_only_jaccard": jaccard(full_set, rel2_set),
            "full_vs_physics_only_jaccard": jaccard(full_set, physics_set),
        },
        "ablation_overlap": {
            "R_minus_phy": jaccard(full_set, worst_set(df, "R_minus_phy", k)),
            "R_minus_train": jaccard(full_set, worst_set(df, "R_minus_train", k)),
            "R_minus_num": jaccard(full_set, worst_set(df, "R_minus_num", k)),
            "R_minus_str": jaccard(full_set, worst_set(df, "R_minus_str", k)),
        },
        "full_only_vs_rel_l2_only_means": {
            "n_points": len(full_only_vs_rel2),
            "rel_l2": unique_mean(df, full_only_vs_rel2, "rel_l2"),
            "physics_consistency_recal": unique_mean(df, full_only_vs_rel2, "physics_consistency_recal"),
            "training_stability_recal": unique_mean(df, full_only_vs_rel2, "training_stability_recal"),
            "structural_stability_recal": unique_mean(df, full_only_vs_rel2, "structural_stability_recal"),
        },
        "rel_l2_only_vs_full_means": {
            "n_points": len(rel2_only_vs_full),
            "rel_l2": unique_mean(df, rel2_only_vs_full, "rel_l2"),
            "physics_consistency_recal": unique_mean(df, rel2_only_vs_full, "physics_consistency_recal"),
            "training_stability_recal": unique_mean(df, rel2_only_vs_full, "training_stability_recal"),
            "structural_stability_recal": unique_mean(df, rel2_only_vs_full, "structural_stability_recal"),
        },
    }
    return summary


def build_summary_tables(case_summaries: Dict[str, Dict[str, object]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    overlap_rows: List[Dict[str, object]] = []
    ablation_rows: List[Dict[str, object]] = []
    for case_name, summary in case_summaries.items():
        overlap_rows.append(
            {
                "case": case_name,
                "full_vs_rel_l2_only_jaccard": summary["single_indicator_overlap"]["full_vs_rel_l2_only_jaccard"],
                "full_vs_physics_only_jaccard": summary["single_indicator_overlap"]["full_vs_physics_only_jaccard"],
            }
        )
        for key, value in summary["ablation_overlap"].items():
            ablation_rows.append({"case": case_name, "ablation": key, "jaccard_vs_full": value})
    return pd.DataFrame(overlap_rows), pd.DataFrame(ablation_rows)


def plot_results(overlap_df: pd.DataFrame, ablation_df: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.2), constrained_layout=True)

    x = range(len(overlap_df))
    width = 0.28
    axes[0].bar(
        [i - width / 2 for i in x],
        overlap_df["full_vs_rel_l2_only_jaccard"],
        width=width,
        color="#b64040",
        label="full vs rel_l2-only",
    )
    axes[0].bar(
        [i + width / 2 for i in x],
        overlap_df["full_vs_physics_only_jaccard"],
        width=width,
        color="#1f4e79",
        label="full vs physics-only",
    )
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels([CASE_TITLES[c] for c in overlap_df["case"]])
    axes[0].set_ylim(0.0, 1.0)
    axes[0].set_ylabel("Jaccard overlap")
    axes[0].set_title("Single-indicator overlap with full R")
    axes[0].legend(frameon=False)

    order = ["R_minus_phy", "R_minus_train", "R_minus_num", "R_minus_str"]
    colors = {
        "R_minus_phy": "#1f4e79",
        "R_minus_train": "#7a7a7a",
        "R_minus_num": "#b64040",
        "R_minus_str": "#2c7a5a",
    }
    case_positions = {case: i for i, case in enumerate(overlap_df["case"])}
    for idx, ablation in enumerate(order):
        subset = ablation_df[ablation_df["ablation"] == ablation]
        axes[1].bar(
            [case_positions[c] + (idx - 1.5) * 0.18 for c in subset["case"]],
            subset["jaccard_vs_full"],
            width=0.18,
            color=colors[ablation],
            label=ablation.replace("R_minus_", "-"),
        )
    axes[1].set_xticks(list(case_positions.values()))
    axes[1].set_xticklabels([CASE_TITLES[c] for c in overlap_df["case"]])
    axes[1].set_ylim(0.0, 1.0)
    axes[1].set_ylabel("Jaccard overlap")
    axes[1].set_title("Ablation overlap with full R")
    axes[1].legend(frameon=False, ncol=2)

    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_note(case_summaries: Dict[str, Dict[str, object]]) -> None:
    b = case_summaries["burgers"]
    s = case_summaries["stokes_poiseuille"]
    p = case_summaries["poisson"]
    f = case_summaries.get("fisher_kpp", {})
    lines = [
        "# Single-Indicator Comparison and Dimension Ablation Results",
        "",
        "## Key Findings",
        "",
        f"- Poisson: full R vs rel_l2-only Jaccard = {p['single_indicator_overlap']['full_vs_rel_l2_only_jaccard']:.3f}. No practical failure boundary; conclusions should not be overinterpreted.",
        f"- Stokes-Poiseuille: full R vs rel_l2-only Jaccard = {s['single_indicator_overlap']['full_vs_rel_l2_only_jaccard']:.3f}. Error-dominated but full R captures some additional low-stability cases.",
        f"- Burgers: full R vs rel_l2-only Jaccard = {b['single_indicator_overlap']['full_vs_rel_l2_only_jaccard']:.3f}. Full R identifies risk cases that single-error ranking misses.",
    ]
    if f:
        lines.append(f"- `Fisher-KPP` 中，full R 与 `rel_l2-only` 的重合度为 `{f['single_indicator_overlap']['full_vs_rel_l2_only_jaccard']:.3f}`。该案例处于 Stokes 与 Burgers 之间，full R 提供了一定补充信息但增幅有限。")

    lines.extend([
        "",
        "## Burgers Key Findings",
        "",
        f"- Points uniquely flagged by full R (not rel_l2-only): {b['full_only_vs_rel_l2_only_means']['n_points']}, mean training_stability_recal = {b['full_only_vs_rel_l2_only_means']['training_stability_recal']:.3f}, mean structural_stability_recal = {b['full_only_vs_rel_l2_only_means']['structural_stability_recal']:.3f}.",
        f"- Points uniquely flagged by rel_l2-only: mean training_stability_recal = {b['rel_l2_only_vs_full_means']['training_stability_recal']:.3f}, mean structural_stability_recal = {b['rel_l2_only_vs_full_means']['structural_stability_recal']:.3f}.",
        "- Full R prioritizes cases with worse training stability and structural stability, not just repeating error ranking.",
        "",
        "## Stokes Comments",
        "",
        f"- Full R unique points: training_stability_recal = {s['full_only_vs_rel_l2_only_means']['training_stability_recal']:.3f}, structural_stability_recal = {s['full_only_vs_rel_l2_only_means']['structural_stability_recal']:.3f}.",
        f"- rel_l2-only unique points: training_stability_recal = {s['rel_l2_only_vs_full_means']['training_stability_recal']:.3f}, structural_stability_recal = {s['rel_l2_only_vs_full_means']['structural_stability_recal']:.3f}.",
        "- Full R also favors worse stability/structural cases in Stokes, but the effect is weaker than in Burgers.",
    ])

    if f:
        lines.extend([
            "",
            "## Fisher-KPP Intermediate Performance",
            "",
            f"- Fisher-KPP: full R vs rel_l2-only Jaccard = {f['single_indicator_overlap']['full_vs_rel_l2_only_jaccard']:.3f}. Sits between Stokes and Burgers as intermediate.",
            f"- Fisher-KPP full-only rel_l2 mean = {f['full_only_vs_rel_l2_only_means']['rel_l2']:,.4f}" if f['full_only_vs_rel_l2_only_means']['rel_l2'] is not None else "- Fisher-KPP full-only: no unique points found",
            f"- Fisher-KPP rel_l2-only training_stability mean = {f['rel_l2_only_vs_full_means']['training_stability_recal']:.3f}" if f['rel_l2_only_vs_full_means']['training_stability_recal'] is not None else "",
            "- Full R vs rel_l2-only gap is intermediate between Stokes and Burgers, consistent with intermediate boundary semantics.",
        ])

    ablation_f_ranges = []
    if f:
        ablation_min = min(f['ablation_overlap'].values())
        ablation_max = max(f['ablation_overlap'].values())
        ablation_f_ranges.append(f"- Fisher-KPP: ablation overlap range [{ablation_min:.3f}, {ablation_max:.3f}]")
    lines.extend([
        "",
        "## Dimension Ablation",
        "",
        f"- Burgers: ablation overlap range [{min(b['ablation_overlap'].values()):.3f}, {max(b['ablation_overlap'].values()):.3f}], no single dimension dominates the worst-case set.",
        f"- Stokes-Poiseuille: removing physics or numerical shows lowest overlap, consistent with regular error/physics-governed boundary.",
    ] + ablation_f_ranges + [
        "- Conclusion: full R supplements single-error metrics most in Burgers, moderately in Fisher-KPP/Stokes, and minimally in Poisson.",
        "",
    ])
    NOTE_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    case_summaries: Dict[str, Dict[str, object]] = {}
    for case_name, path in CASE_TABLES.items():
        df = pd.read_csv(path)
        case_summaries[case_name] = analyze_case(case_name, df)

    overlap_df, ablation_df = build_summary_tables(case_summaries)
    overlap_df.to_csv(OUTPUT_DIR / "single_indicator_overlap.csv", index=False)
    ablation_df.to_csv(OUTPUT_DIR / "dimension_ablation_overlap.csv", index=False)

    with (OUTPUT_DIR / "dimension_ablation_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(case_summaries, fh, ensure_ascii=False, indent=2)

    plot_results(overlap_df, ablation_df, OUTPUT_DIR / "figure_13_dimension_ablation.png")
    write_note(case_summaries)

    print(f"[done] output_dir={OUTPUT_DIR}")
    print(overlap_df.to_string(index=False))
    print(ablation_df.to_string(index=False))


if __name__ == "__main__":
    main()

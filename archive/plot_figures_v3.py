"""
Regenerate paper figures with proper layout: max 2 subplots per figure,
Chinese labels (宋体), readable sizes.
"""
from __future__ import annotations

import json, shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd

# Force Chinese font
plt.rcParams['font.sans-serif'] = ['SimSun', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

PROJECT = Path(__file__).resolve().parent
R_DIR = PROJECT / "results"
FIG_DIR = R_DIR / "paper_figures" / "v3"
FIG_DIR.mkdir(parents=True, exist_ok=True)

CASE_NAMES = {
    "poisson": "泊松方程",
    "burgers": "Burgers 方程", 
    "stokes_poiseuille": "Stokes-Poiseuille 流",
    "fisher_kpp": "Fisher-KPP 方程",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def pivot_df(df, val_col):
    return df.pivot(index="noise_std", columns="num_observation", values=val_col).sort_index().sort_index(axis=1)


# ═══════════════ FIG 1: rel_l2 phase maps (2 panels per figure) ═══════════════

def gen_phase_maps_rel_l2():
    cases = ["poisson", "burgers", "stokes_poiseuille", "fisher_kpp"]
    paths = {
        "poisson,burgers,stokes_poiseuille": R_DIR / "matrices" / "coarse_v1" / "matrix_summary.csv",
        "fisher_kpp": R_DIR / "matrices" / "coarse_fisher_kpp_v1" / "matrix_summary.csv",
    }
    dfs = {}
    for key, p in paths.items():
        if not p.exists():
            continue
        df = pd.read_csv(p)
        for case in key.split(","):
            if case in cases:
                dfs[case] = df[df["case"] == case]

    tables = {c: pivot_df(d, "rel_l2") for c, d in dfs.items() if c in dfs}
    if not tables:
        return

    vmin = min(t.values.min() for t in tables.values())
    vmax = max(t.values.max() for t in tables.values())

    # Split into 2x2 = 4 individual figures, each 2 panels
    pairs = [("poisson", "stokes_poiseuille"), ("burgers", "fisher_kpp")]
    for pi, (c1, c2) in enumerate(pairs):
        if c1 not in tables or c2 not in tables:
            continue
        
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), constrained_layout=True)
        for ax, c in zip(axes, [c1, c2]):
            t = tables[c]
            im = ax.imshow(t.values, origin="lower", aspect="auto", cmap="viridis", vmin=vmin, vmax=vmax)
            ax.set_title(CASE_NAMES[c], fontsize=12)
            ax.set_xlabel("观测点数", fontsize=10); ax.set_ylabel("噪声标准差", fontsize=10)
            ax.set_xticks(range(len(t.columns)))
            ax.set_xticklabels([str(int(x)) for x in t.columns], rotation=45, ha="right", fontsize=9)
            ax.set_yticks(range(len(t.index)))
            ax.set_yticklabels([f"{x:.3f}" for x in t.index], fontsize=9)
        
        fig.colorbar(im, ax=list(axes), shrink=0.85, label="相对 $L_2$ 误差")
        label = "ab" if pi == 0 else "cd"
        out = FIG_DIR / f"fig01_rel_l2_{label}.png"
        fig.savefig(out, dpi=220, bbox_inches="tight")
        plt.close(fig)
        print(f"  Fig 1-{label}: {out}")


# ═══════════════ FIG 2: R phase maps ═══════════════

def gen_phase_maps_R():
    cases = ["poisson", "burgers", "stokes_poiseuille", "fisher_kpp"]
    table_dir = R_DIR / "analysis" / "recalibrated_dimensions_v1"
    tables = {}
    for c in cases:
        p = table_dir / f"{c}_recalibrated_table.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p)
        tables[c] = pivot_df(df, "reliability_raw_recal")

    if not tables:
        return

    pairs = [("poisson", "stokes_poiseuille"), ("burgers", "fisher_kpp")]
    for pi, (c1, c2) in enumerate(pairs):
        if c1 not in tables or c2 not in tables:
            continue
        
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), constrained_layout=True)
        for ax, c in zip(axes, [c1, c2]):
            t = tables[c]
            im = ax.imshow(t.values, origin="lower", aspect="auto", cmap="RdYlGn", vmin=0, vmax=1)
            ax.set_title(CASE_NAMES[c], fontsize=12)
            ax.set_xlabel("观测点数", fontsize=10); ax.set_ylabel("噪声标准差", fontsize=10)
            ax.set_xticks(range(len(t.columns)))
            ax.set_xticklabels([str(int(x)) for x in t.columns], rotation=45, ha="right", fontsize=9)
            ax.set_yticks(range(len(t.index)))
            ax.set_yticklabels([f"{x:.3f}" for x in t.index], fontsize=9)
        
        fig.colorbar(im, ax=list(axes), shrink=0.85, label="重标定综合分 $R$")
        label = "ab" if pi == 0 else "cd"
        out = FIG_DIR / f"fig02_R_{label}.png"
        fig.savefig(out, dpi=220, bbox_inches="tight")
        plt.close(fig)
        print(f"  Fig 2-{label}: {out}")


# ═══════════════ FIG 3: Boundary comparison (3 systems, 3 individual figures) ═══════════════

def gen_boundary_comparison():
    src_paths = [
        (R_DIR / "probability_matrices" / "stokes_probability_boundary_v1" / "multiseed_summary.csv", "Stokes-Poiseuille 流", "#2c7a5a"),
        (R_DIR / "probability_matrices" / "fisher_kpp_probability_boundary_v1" / "multiseed_summary.csv", "Fisher-KPP 方程", "#b64040"),
        (R_DIR / "probability_matrices" / "burgers_probability_boundary_v2_5seed" / "multiseed_summary.csv", "Burgers 方程", "#1f4e79"),
    ]

    for si, (p, name, color) in enumerate(src_paths):
        if not p.exists():
            continue
        df = pd.read_csv(p)
        cr_col = "crosses_threshold_rate"
        if cr_col not in df.columns:
            continue

        obs_levels = sorted(df["num_observation"].unique(), reverse=True)
        noise_levels = sorted(df["noise_std"].unique())
        
        data = np.zeros((len(obs_levels), len(noise_levels)))
        for _, row in df.iterrows():
            i = obs_levels.index(row["num_observation"])
            j = noise_levels.index(row["noise_std"])
            data[i, j] = row[cr_col]

        fig, ax = plt.subplots(figsize=(6.5, 4.5), constrained_layout=True)
        im = ax.imshow(data, aspect="auto", cmap="RdBu_r", vmin=0, vmax=1)
        ax.set_title(name, fontsize=13, fontweight="bold")
        ax.set_xlabel("噪声标准差", fontsize=11); ax.set_ylabel("观测点数", fontsize=11)
        ax.set_xticks(range(len(noise_levels)))
        ax.set_xticklabels([f"{n:.3f}" for n in noise_levels], fontsize=9)
        ax.set_yticks(range(len(obs_levels)))
        ax.set_yticklabels([str(int(o)) for o in obs_levels], fontsize=10)
        
        for i in range(len(obs_levels)):
            for j in range(len(noise_levels)):
                val = data[i, j]
                text_color = "white" if val > 0.5 else "black"
                ax.text(j, i, f"{val:.0%}", ha="center", va="center", color=text_color, fontsize=8)
        
        fig.colorbar(im, ax=ax, shrink=0.85, label="越界率")
        
        labels = "abc"
        out = FIG_DIR / f"fig03_boundary_{labels[si]}.png"
        fig.savefig(out, dpi=220, bbox_inches="tight")
        plt.close(fig)
        print(f"  Fig 3-{labels[si]}: {out}")


# ═══════════════ FIG 4: Ablation (3 cases, 3 individual bar charts) ═══════════════

def gen_ablation():
    summary_path = R_DIR / "analysis" / "dimension_ablation_v2" / "ablation_summary.json"
    if not summary_path.exists():
        return
    
    data = load_json(summary_path)
    cases = ["burgers", "fisher_kpp", "stokes_poiseuille"]
    score_labels = [
        ("R_full", "完整四维", "#333333"),
        ("R_minus_physics", "去除物理约束", "#1f4e79"),
        ("R_minus_training", "去除训练稳定性", "#7a7a7a"),
        ("R_minus_numerical", "去除数值精度", "#b64040"),
        ("R_minus_structural", "去除结构保真度", "#2c7a5a"),
        ("rel_l2", "仅相对误差", "#b64040"),
        ("training_stability", "仅训练稳定性", "#7a7a7a"),
        ("physics_consistency", "仅物理约束", "#1f4e79"),
        ("numerical_accuracy", "仅数值精度", "#b64040"),
        ("structural_stability", "仅结构保真度", "#2c7a5a"),
    ]

    for si, case in enumerate(cases):
        if case not in data:
            continue
        rhos = data[case].get("ranking_consistency", {})
        labels, values, colors = [], [], []
        for key, ch_label, color in score_labels:
            if key in rhos:
                labels.append(ch_label)
                values.append(rhos[key].get("mean_rho", 0))
                colors.append(color)

        if not values:
            continue
        
        fig, ax = plt.subplots(figsize=(8, 3.5), constrained_layout=True)
        bars = ax.barh(range(len(labels)), values, color=colors)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlim(0, 1.05)
        ax.set_xlabel("平均 Spearman 相关系数（跨种子）", fontsize=11)
        ax.set_title(f"{CASE_NAMES.get(case, case)}：跨种子排序一致性", fontsize=12)
        
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2, 
                   f"{val:.3f}", va="center", fontsize=8)
        
        labels2 = "abc"
        out = FIG_DIR / f"fig04_ablation_{labels2[si]}.png"
        fig.savefig(out, dpi=220, bbox_inches="tight")
        plt.close(fig)
        print(f"  Fig 4-{labels2[si]}: {out}")


def main():
    print("Generating split figures...")
    gen_phase_maps_rel_l2()
    gen_phase_maps_R()
    gen_boundary_comparison()
    gen_ablation()
    print(f"\nAll figures in: {FIG_DIR}")
    # List outputs
    for f in sorted(FIG_DIR.glob("*.png")):
        print(f"  {f.name}")


if __name__ == "__main__":
    main()

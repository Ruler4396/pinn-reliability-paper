"""
v5: Fix text readability, split multi-panel figures, standardize names.
"""
from pathlib import Path
import json, csv, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimSun', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

PROJECT = Path(__file__).resolve().parent.parent
R_DIR = PROJECT / "minimal_pinn" / "results"
FIG_DIR = R_DIR / "paper_figures" / "v5"
FIG_DIR.mkdir(parents=True, exist_ok=True)

CASE_NAMES = {
    "poisson": "Poisson方程", "burgers": "Burgers方程",
    "stokes_poiseuille": "斯托克斯-泊肃叶流", "fisher_kpp": "Fisher-KPP方程",
}

def pivot_df(df, vcol):
    return df.pivot(index="noise_std", columns="num_observation", values=vcol).sort_index().sort_index(axis=1)

def text_color_for_value(val, vmin, vmax):
    """Return text color based on background brightness."""
    norm = (val - vmin) / (vmax - vmin + 1e-10)
    # viridis: dark (0) -> bright (1)
    # Use dark text for bright cells (norm > 0.6), white for dark cells
    return "black" if norm > 0.55 else "white"

# ═══ FIG 5-1: Individual case rel_l2 phase maps ═══
def gen_fig5_1():
    coarse = R_DIR / "matrices" / "coarse_v1" / "matrix_summary.csv"
    fkpp = R_DIR / "matrices" / "coarse_fisher_kpp_v1" / "matrix_summary.csv"
    dfs = {}
    for p, cases in [(coarse, ["poisson","burgers","stokes_poiseuille"]), (fkpp, ["fisher_kpp"])]:
        if not p.exists(): continue
        df = pd.read_csv(p)
        for c in cases: dfs[c] = df[df["case"]==c]
    
    vmin = min(pivot_df(d,"rel_l2").values.min() for d in dfs.values())
    vmax = max(pivot_df(d,"rel_l2").values.max() for d in dfs.values())
    
    labels = {"poisson":"a","stokes_poiseuille":"b","fisher_kpp":"c","burgers":"d"}
    for c in ["poisson","stokes_poiseuille","fisher_kpp","burgers"]:
        if c not in dfs: continue
        t = pivot_df(dfs[c], "rel_l2")
        fig, ax = plt.subplots(figsize=(5.5,4.2), constrained_layout=True)
        im = ax.imshow(t.values, origin="lower", aspect="auto", cmap="viridis", vmin=vmin, vmax=vmax)
        ax.set_title(CASE_NAMES[c], fontsize=13)
        ax.set_xlabel("观测点数", fontsize=11); ax.set_ylabel("噪声标准差", fontsize=11)
        ax.set_xticks(range(len(t.columns)))
        ax.set_xticklabels([str(int(x)) for x in t.columns], fontsize=9)
        ax.set_yticks(range(len(t.index)))
        ax.set_yticklabels([f"{x:.3f}" for x in t.index], fontsize=9)
        # FIX: Use adaptive text color
        for i in range(len(t.index)):
            for j in range(len(t.columns)):
                tc = text_color_for_value(t.values[i,j], vmin, vmax)
                ax.text(j, i, f"{t.values[i,j]:.3f}", ha="center", va="center", color=tc, fontsize=6)
        fig.colorbar(im, ax=ax, shrink=0.85, label="相对 L2 误差")
        fp = FIG_DIR / f"fig5-1{labels[c]}.png"
        fig.savefig(fp, dpi=220, bbox_inches="tight"); plt.close(fig)
        print(f"  Fig 5-1{labels[c]}: {fp}")

# ═══ FIG 5-2: Individual case R phase maps ═══
def gen_fig5_2():
    td = R_DIR / "analysis" / "recalibrated_dimensions_v1"
    labels = {"poisson":"a","stokes_poiseuille":"b","fisher_kpp":"c","burgers":"d"}
    for c in ["poisson","stokes_poiseuille","fisher_kpp","burgers"]:
        p = td / f"{c}_recalibrated_table.csv"
        if not p.exists(): continue
        df = pd.read_csv(p)
        t = pivot_df(df, "reliability_raw_recal")
        fig, ax = plt.subplots(figsize=(5.5,4.2), constrained_layout=True)
        im = ax.imshow(t.values, origin="lower", aspect="auto", cmap="RdYlGn", vmin=0, vmax=1)
        ax.set_title(CASE_NAMES[c], fontsize=13)
        ax.set_xlabel("观测点数", fontsize=11); ax.set_ylabel("噪声标准差", fontsize=11)
        ax.set_xticks(range(len(t.columns)))
        ax.set_xticklabels([str(int(x)) for x in t.columns], fontsize=9)
        ax.set_yticks(range(len(t.index)))
        ax.set_yticklabels([f"{x:.3f}" for x in t.index], fontsize=9)
        for i in range(len(t.index)):
            for j in range(len(t.columns)):
                ax.text(j, i, f"{t.values[i,j]:.2f}", ha="center", va="center", color="black", fontsize=6)
        fig.colorbar(im, ax=ax, shrink=0.85, label="综合分 R")
        fp = FIG_DIR / f"fig5-2{labels[c]}.png"
        fig.savefig(fp, dpi=220, bbox_inches="tight"); plt.close(fig)
        print(f"  Fig 5-2{labels[c]}: {fp}")

# ═══ FIG 5-3: Probability boundary heatmaps ═══
def gen_fig5_3():
    srcs = [
        (R_DIR/"probability_matrices"/"stokes_probability_boundary_v1"/"multiseed_summary.csv","斯托克斯-泊肃叶流","a"),
        (R_DIR/"probability_matrices"/"fisher_kpp_probability_boundary_v1"/"multiseed_summary.csv","Fisher-KPP方程","b"),
        (R_DIR/"probability_matrices"/"burgers_probability_boundary_v2_5seed"/"multiseed_summary.csv","Burgers方程","c"),
    ]
    for p, name, lb in srcs:
        if not p.exists(): continue
        df = pd.read_csv(p)
        obs_lv = sorted(df["num_observation"].unique(), reverse=True)
        noise_lv = sorted(df["noise_std"].unique())
        data = np.zeros((len(obs_lv), len(noise_lv)))
        for _, row in df.iterrows():
            data[obs_lv.index(row["num_observation"]), noise_lv.index(row["noise_std"])] = row["crosses_threshold_rate"]
        fig, ax = plt.subplots(figsize=(5.8,4.0), constrained_layout=True)
        im = ax.imshow(data, aspect="auto", cmap="RdBu_r", vmin=0, vmax=1)
        ax.set_title(name, fontsize=13)
        ax.set_xlabel("噪声标准差", fontsize=11); ax.set_ylabel("观测点数", fontsize=11)
        ax.set_xticks(range(len(noise_lv)))
        ax.set_xticklabels([f"{n:.3f}" for n in noise_lv], fontsize=9)
        ax.set_yticks(range(len(obs_lv)))
        ax.set_yticklabels([str(int(o)) for o in obs_lv], fontsize=10)
        for i in range(len(obs_lv)):
            for j in range(len(noise_lv)):
                ax.text(j, i, f"{data[i,j]:.0%}", ha="center", va="center", color="white" if data[i,j]>0.5 else "black", fontsize=8)
        fig.colorbar(im, ax=ax, shrink=0.85, label="越界率")
        fp = FIG_DIR / f"fig5-3{lb}.png"
        fig.savefig(fp, dpi=220, bbox_inches="tight"); plt.close(fig)
        print(f"  Fig 5-3{lb}: {fp}")

# ═══ FIG 5-4: Wilson CI plots - SPLIT into 2 separate figures ═══
def gen_fig5_4():
    probes = {}
    for case_prefix, globs in [
        ("burgers", ["burgers_boundary_keypoints_v3_10seed","burgers_boundary_keypoints_v4_extra_seed51_70","burgers_boundary_keypoints_v5_transition_seed71_80"]),
        ("fisher_kpp", ["fisher_kpp_boundary_keypoints_v1_10seed","fisher_kpp_boundary_keypoints_v2_extra_seed51_70","fisher_kpp_boundary_keypoints_v3_transition_seed71_80"]),
    ]:
        rows = []
        for g in globs:
            cp = R_DIR / "probes" / g / "probe_runs.csv"
            if not cp.exists(): continue
            for r in csv.DictReader(open(cp)):
                rows.append(r)
        if rows:
            probes[case_prefix] = pd.DataFrame(rows)
            for c in ["rel_l2","num_observation","noise_std","seed","crosses_threshold"]:
                if c in probes[case_prefix].columns:
                    probes[case_prefix][c] = pd.to_numeric(probes[case_prefix][c], errors="coerce")
    
    # SPLIT: Generate 2 separate figures
    for case, name, lb in [("burgers","Burgers方程","a"),("fisher_kpp","Fisher-KPP方程","b")]:
        if case not in probes: continue
        df = probes[case]
        labels = sorted(df["label"].unique())
        rates, lows, highs = [], [], []
        for lb_item in labels:
            sub = df[df["label"]==lb_item]
            n = len(sub)
            k = int(sub["crosses_threshold"].sum())
            p = k/n if n>0 else 0
            z = 1.96
            denom = 1 + z**2/n
            center = (p + z**2/(2*n)) / denom
            margin = z * np.sqrt((p*(1-p)/n + z**2/(4*n**2))) / denom
            rates.append(center); lows.append(max(0,center-margin)); highs.append(min(1,center+margin))
        
        fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
        x = range(len(labels))
        for i, (lo, hi, r) in enumerate(zip(lows, highs, rates)):
            ax.errorbar(i, r, yerr=[[r-lo],[hi-r]], fmt="o", color="#1f4e79", capsize=4, markersize=6)
        ax.set_title(f"{name}：边界关键点越界率（威尔逊95%置信区间）", fontsize=11)
        ax.set_xticks(x); ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        ax.set_ylabel("越界率", fontsize=11); ax.set_ylim(-0.05, 1.1)
        ax.axhline(0.2, color="green", linestyle="--", alpha=0.4); ax.axhline(0.8, color="red", linestyle="--", alpha=0.4)
        fp = FIG_DIR / f"fig5-4{lb}.png"
        fig.savefig(fp, dpi=220, bbox_inches="tight"); plt.close(fig)
        print(f"  Fig 5-4{lb}: {fp}")

# ═══ FIG 6-1: Ablation - SPLIT into 3 separate figures ═══
def gen_fig6_1():
    sp = R_DIR / "analysis" / "dimension_ablation_v2" / "ablation_summary.json"
    if not sp.exists(): return
    data = json.loads(sp.read_text(encoding="utf-8"))
    
    cases = [("burgers","Burgers方程","a"), ("fisher_kpp","Fisher-KPP方程","b"), ("stokes_poiseuille","斯托克斯-泊肃叶流","c")]
    keys_show = [
        ("R_full","完整四维","#333333"),
        ("rel_l2","仅相对误差","#b64040"),
        ("R_minus_training","去除训练稳定性","#7a7a7a"),
    ]
    
    # SPLIT: Generate 3 separate figures
    for ck, cn, lb in cases:
        rhos = data.get(ck,{}).get("ranking_consistency",{})
        labels, vals, cols = [], [], []
        for sk, sl, sc in keys_show:
            if sk in rhos and rhos[sk].get("mean_rho") is not None:
                labels.append(sl); vals.append(rhos[sk]["mean_rho"]); cols.append(sc)
        
        fig, ax = plt.subplots(figsize=(5, 3.5), constrained_layout=True)
        bars = ax.bar(range(len(labels)), vals, color=cols, width=0.5)
        ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylim(0, 1.05); ax.set_title(cn, fontsize=12)
        ax.set_ylabel("平均斯皮尔曼相关系数", fontsize=11)
        for b, v in zip(bars, vals): ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.02, f"{v:.3f}", ha="center", fontsize=9)
        fp = FIG_DIR / f"fig6-1{lb}.png"
        fig.savefig(fp, dpi=220, bbox_inches="tight"); plt.close(fig)
        print(f"  Fig 6-1{lb}: {fp}")

# ═══ FIG 7-1: Calibration sensitivity - SPLIT into 4 separate figures ═══
def gen_fig7_1():
    sp = R_DIR / "analysis" / "calibration_sensitivity_v1" / "calibration_sensitivity_summary.csv"
    if not sp.exists(): return
    df = pd.read_csv(sp)
    dims = ["physics_consistency_count","training_stability_count","numerical_accuracy_count","structural_stability_count"]
    dim_labels = ["物理约束","训练稳定性","数值精度","结构保真度"]
    colors = ["#1f4e79","#7a7a7a","#b64040","#2c7a5a"]
    cases = df["case"].unique()
    
    # SPLIT: Generate separate figure per case
    for cn in cases:
        cd = df[df["case"]==cn]
        qlabels = cd["quantiles"].tolist()
        x = range(len(qlabels))
        width = 0.18
        
        fig, ax = plt.subplots(figsize=(6, 3.5), constrained_layout=True)
        for off, (d, dl, cl) in zip([-1.5,-0.5,0.5,1.5], zip(dims, dim_labels, colors)):
            ax.bar([xi+off*width for xi in x], cd[d].tolist(), width=width, color=cl, label=dl)
        ax.set_title(CASE_NAMES.get(cn,cn), fontsize=11)
        ax.set_xticks(list(x)); ax.set_xticklabels(qlabels, fontsize=8)
        ax.set_ylabel("主导失效计数", fontsize=10)
        ax.legend(fontsize=8)
        lb = {"poisson":"a","stokes_poiseuille":"b","fisher_kpp":"c","burgers":"d"}.get(cn, cn[:2])
        fp = FIG_DIR / f"fig7-1{lb}.png"
        fig.savefig(fp, dpi=220, bbox_inches="tight"); plt.close(fig)
        print(f"  Fig 7-1{lb}: {fp}")

# ═══ FIG 7-2: Anti-circularity ═══
def gen_fig7_2():
    sp = R_DIR / "analysis" / "anti_circularity_v1" / "anti_circularity_summary.json"
    if not sp.exists(): return
    data = json.loads(sp.read_text(encoding="utf-8"))
    cr = data.get("case_results",{})
    if not cr: return
    fig, ax = plt.subplots(figsize=(6,3.5))
    names = list(cr.keys())
    rates = [cr[n]["agreement_rate"]*100 for n in names]
    ax.bar(names, rates, color=["#1f4e79","#b64040","#2c7a5a"][:len(names)], width=0.4)
    ax.axhline(25, color="gray", linestyle="--", label="随机基线（四分类）")
    for b, r in zip(ax.patches, rates): ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.5, f"{r:.0f}%", ha="center")
    ax.set_ylabel("分半校验一致率 (%)", fontsize=11)
    ax.set_title("反循环校验：留出评估中主导维度的一致率", fontsize=12)
    ax.legend(); ax.set_ylim(0,105)
    fp = FIG_DIR / "fig7-2.png"
    fig.savefig(fp, dpi=220, bbox_inches="tight"); plt.close(fig)
    print(f"  Fig 7-2: {fp}")

# ═══ FIG 7-3: Baseline failure rate vs threshold ═══
def gen_fig7_3():
    blp = R_DIR / "baseline_multiseed_v1" / "summary.json"
    baseline_mean = 0.017792
    if blp.exists():
        bl = json.loads(blp.read_text(encoding="utf-8"))
        for r in bl.get("summary_rows",[]):
            if r["case"]=="burgers": baseline_mean = r["rel_l2_mean"]; break
    rows = []
    for g in ["burgers_boundary_keypoints_v3_10seed","burgers_boundary_keypoints_v4_extra_seed51_70","burgers_boundary_keypoints_v5_transition_seed71_80"]:
        cp = R_DIR / "probes" / g / "probe_runs.csv"
        if not cp.exists(): continue
        for r in csv.DictReader(open(cp)):
            if float(r.get("num_observation",0))==128 and float(r.get("noise_std",0))==0.0:
                rows.append(float(r["rel_l2"]))
    if not rows: return
    mults = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
    rates = [sum(1 for v in rows if v>=baseline_mean*m)/len(rows) for m in mults]
    fig, ax = plt.subplots(figsize=(6,3.5))
    colors = ["#2c7a5a" if r<0.2 else "#b64040" for r in rates]
    ax.bar([str(m) for m in mults], [r*100 for r in rates], width=0.5, color=colors)
    ax.set_xlabel("阈值倍数（×基线均值）", fontsize=11)
    ax.set_ylabel("最安全点越界率 (%)", fontsize=11)
    ax.set_title(f"Burgers方程：最安全点越界率随阈值变化（{len(rows)}个种子）", fontsize=12)
    for b, r in zip(ax.patches, rates): ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.3, f"{r:.0%}", ha="center", fontsize=9)
    ax.axhline(20, color="gray", linestyle="--"); ax.set_ylim(0,105)
    fp = FIG_DIR / "fig7-3.png"
    fig.savefig(fp, dpi=220, bbox_inches="tight"); plt.close(fig)
    print(f"  Fig 7-3: {fp}")

def main():
    print("v5: Regenerating figures with fixes...")
    gen_fig5_1()
    gen_fig5_2()
    gen_fig5_3()
    gen_fig5_4()
    gen_fig6_1()
    gen_fig7_1()
    gen_fig7_2()
    gen_fig7_3()
    print(f"\nAll figures in: {FIG_DIR}")
    for f in sorted(FIG_DIR.glob("*.png")): print(f"  {f.name}")

if __name__ == "__main__":
    main()

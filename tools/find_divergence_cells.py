"""Find divergence cells for A2 morphology plots."""
import csv, json
from collections import defaultdict
from pathlib import Path

RESULTS = Path("minimal_pinn/results")
PROB = RESULTS / "probability_matrices"

for case, mname in [
    ("burgers", "burgers_probability_boundary_v2_5seed"),
    ("fisher_kpp", "fisher_kpp_probability_boundary_v1"),
    ("stokes_poiseuille", "stokes_probability_boundary_v1"),
]:
    path = PROB / mname / "multiseed_runs.csv"
    rows = list(csv.DictReader(open(path)))
    
    cells = defaultdict(lambda: {"r_vals": [], "l2_vals": [], "runs": []})
    for r in rows:
        obs = int(float(r["num_observation"]))
        noise = int(float(r["noise_std"]) * 1000)
        key = f"obs{obs}_n{noise:03d}"
        cells[key]["r_vals"].append(float(r["reliability_raw_recal"]))
        cells[key]["l2_vals"].append(float(r["rel_l2"]))
        cells[key]["runs"].append(r["run_name"])
    
    r_means = {k: sum(v["r_vals"]) / len(v["r_vals"]) for k, v in cells.items()}
    l2_means = {k: sum(v["l2_vals"]) / len(v["l2_vals"]) for k, v in cells.items()}
    
    # R: higher = better. Sort ascending for worst first
    # rel_l2: lower = better. Sort descending for worst first
    r_rank = sorted(r_means, key=lambda k: r_means[k])
    l2_rank = sorted(l2_means, key=lambda k: -l2_means[k])
    
    n = len(r_rank)
    k = max(1, n // 3)
    
    r_worst = set(r_rank[:k])
    l2_worst = set(l2_rank[:k])
    
    r_only = r_worst - l2_worst
    l2_only = l2_worst - r_worst
    shared = r_worst & l2_worst
    
    print(f"\n{case} ({n} cells, k={k}):")
    print(f"  Shared: {sorted(shared)}")
    print(f"  R-only worst: {sorted(r_only)[:3]}")
    print(f"  L2-only worst: {sorted(l2_only)[:3]}")
    
    if r_only:
        cell = sorted(r_only)[0]
        median_run = cells[cell]["runs"][len(cells[cell]["runs"]) // 2]
        print(f"  Sample R-only: {cell} R={r_means[cell]:.3f} l2={l2_means[cell]:.4f} run={median_run}")
    if l2_only:
        cell = sorted(l2_only)[0]
        median_run = cells[cell]["runs"][len(cells[cell]["runs"]) // 2]
        print(f"  Sample L2-only: {cell} R={r_means[cell]:.3f} l2={l2_means[cell]:.4f} run={median_run}")

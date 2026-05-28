"""Quick summary generator for Fisher-KPP probability boundary matrix."""
import json, statistics
from pathlib import Path
from itertools import groupby

runs_dir = Path("minimal_pinn/results/probability_matrices/fisher_kpp_probability_boundary_v1/runs")
rows = []
for run_dir in sorted(runs_dir.iterdir()):
    if not run_dir.is_dir():
        continue
    metrics_path = run_dir / "metrics.json"
    config_path = run_dir / "config.json"
    if not metrics_path.exists() or not config_path.exists():
        continue
    with open(metrics_path) as f:
        metrics = json.load(f)
    with open(config_path) as f:
        config = json.load(f)
    s = metrics["scalar_metrics"]
    row = {
        "run_name": run_dir.name,
        "num_observation": config["data"]["num_observation"],
        "noise_std": config["data"]["noise_std"],
        "seed": config["seed"],
        "rel_l2": s["rel_l2"],
    }
    rows.append(row)

key = lambda r: (r["num_observation"], r["noise_std"])
summary = []
for (obs, noise), group in groupby(sorted(rows, key=key), key=key):
    g = list(group)
    rels = [r["rel_l2"] for r in g]
    thr = 0.018860769923776388
    srow = {
        "num_observation": obs,
        "noise_std": noise,
        "n_seed": len(g),
        "rel_l2_mean": statistics.mean(rels),
        "rel_l2_std": statistics.pstdev(rels),
        "crosses_threshold_count": sum(1 for v in rels if v >= thr),
        "crosses_threshold_rate": sum(1 for v in rels if v >= thr) / len(g),
    }
    summary.append(srow)

summary.sort(key=lambda r: (r["num_observation"], r["noise_std"]))

print(f"{'obs':>4s} {'noise':>6s} {'n':>3s} {'rel_l2_mean':>10s} {'rel_l2_std':>10s} {'cross':>5s} {'cross_rate':>10s}")
print("-" * 55)
for s in summary:
    print(f"{s['num_observation']:>4d} {s['noise_std']:>6.3f} {s['n_seed']:>3d} "
          f"{s['rel_l2_mean']:>10.4f} {s['rel_l2_std']:>10.4f} "
          f"{s['crosses_threshold_count']:>5d} {s['crosses_threshold_rate']:>9.2%}")

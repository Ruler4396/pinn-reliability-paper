# Convergence verification: 500 vs 1500 epoch comparison
# Tests whether Poisson's lack of degradation is due to insufficient training

# Burgers: clean baseline, 3 seeds × 1500 epochs
# Allen-Cahn: clean baseline, 3 seeds × 1500 epochs
# Poisson: clean baseline, 3 seeds × 1500 epochs
# Plus degraded points to compare degradation patterns

import json
import csv
import subprocess
import sys
from pathlib import Path

CASES = ["poisson", "burgers", "allen_cahn"]
EPOCHS = 1500
SEEDS = [41, 42, 43]

# Baseline: clean, high obs
BASELINE_POINTS = [
    {"num_observation": 128, "noise_std": 0.0},
]

# Degraded points to compare patterns
DEGRADED_POINTS = {
    "poisson": [
        {"num_observation": 16, "noise_std": 0.20},
    ],
    "burgers": [
        {"num_observation": 32, "noise_std": 0.10},
    ],
    "allen_cahn": [
        {"num_observation": 16, "noise_std": 0.15},
    ],
}


def run_one(case_name, num_obs, noise_std, seed, epochs, output_dir):
    """Run a single experiment."""
    config = {
        "case": {"name": case_name},
        "seed": seed,
        "run_name": output_dir.name,
        "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
        "training": {
            "epochs": epochs,
            "lr": 0.001,
            "print_every": 100,
            "weights": {"data": 10.0, "physics": 1.0, "boundary": 10.0},
        },
        "data": {
            "num_observation": num_obs,
            "num_collocation": 2048,
            "num_boundary": 256,
            "num_eval": 51,
            "noise_std": noise_std,
        },
        "reliability": {
            "thresholds": {
                "physics_rms": {"good": 1e-3, "fail": 1e-1, "mode": "smaller_better"},
                "boundary_rms": {"good": 1e-3, "fail": 1e-1, "mode": "smaller_better"},
                "rel_l2": {"good": 1e-2, "fail": 2e-1, "mode": "smaller_better"},
                "structure_error": {"good": 1e-2, "fail": 2e-1, "mode": "smaller_better"},
                "loss_std": {"good": 1e-4, "fail": 1e-2, "mode": "smaller_better"},
                "loss_ratio": {"good": 0.1, "fail": 0.9, "mode": "smaller_better"},
            }
        },
    }
    config_path = output_dir / "config.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2))

    cmd = [sys.executable, "-m", "minimal_pinn.run_experiment",
           "--config", str(config_path),
           "--output-dir", str(output_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"  FAILED: {result.stderr[:200]}")
        return None

    metrics_path = output_dir / "metrics.json"
    if metrics_path.exists():
        return json.loads(metrics_path.read_text())
    return None


def main():
    base_dir = Path("minimal_pinn/results/convergence_v1500")
    base_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for case_name in CASES:
        # Baseline runs
        for pt in BASELINE_POINTS:
            for seed in SEEDS:
                tag = f"{case_name}_e{EPOCHS}_obs{pt['num_observation']}_noise000_seed{seed}"
                out = base_dir / tag
                print(f"[run] {tag}")
                m = run_one(case_name, pt["num_observation"], pt["noise_std"],
                            seed, EPOCHS, out)
                if m:
                    rows.append({
                        "case": case_name, "point": "baseline",
                        "num_observation": pt["num_observation"],
                        "noise_std": pt["noise_std"], "seed": seed,
                        "epochs": EPOCHS,
                        "rel_l2": m["scalar_metrics"]["rel_l2"],
                    })

        # Degraded runs
        for pt in DEGRADED_POINTS.get(case_name, []):
            for seed in SEEDS:
                noise_pct = int(round(pt["noise_std"] * 1000))
                tag = f"{case_name}_e{EPOCHS}_obs{pt['num_observation']}_noise{noise_pct:03d}_seed{seed}"
                out = base_dir / tag
                print(f"[run] {tag}")
                m = run_one(case_name, pt["num_observation"], pt["noise_std"],
                            seed, EPOCHS, out)
                if m:
                    rows.append({
                        "case": case_name, "point": "degraded",
                        "num_observation": pt["num_observation"],
                        "noise_std": pt["noise_std"], "seed": seed,
                        "epochs": EPOCHS,
                        "rel_l2": m["scalar_metrics"]["rel_l2"],
                    })

    # Save summary
    csv_path = base_dir / "convergence_summary.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    json_path = base_dir / "convergence_summary.json"
    json_path.write_text(json.dumps(rows, indent=2))

    print("\n=== CONVERGENCE SUMMARY ===")
    for case_name in CASES:
        case_rows = [r for r in rows if r["case"] == case_name]
        print(f"\n{case_name}:")
        for r in case_rows:
            print(f"  {r['point']:10s} obs={r['num_observation']:3d} noise={r['noise_std']:.3f} "
                  f"seed={r['seed']} rel_l2={r['rel_l2']:.6f}")


if __name__ == "__main__":
    main()

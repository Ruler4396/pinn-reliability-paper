"""
Generate probe_runs.csv and probe_summary.csv for all PDE cases
from individual run directories.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
PROBES_DIR = RESULTS_DIR / "probes"

ALL_CASES = [
    "poisson", "stokes_poiseuille", "allen_cahn", "fisher_kpp", "burgers",
    "heat_equation", "kdv_soliton", "nls_soliton", "wave_equation", "kdv_double_soliton"
]

# Map case names to probe directory names
PROBE_DIR_MAP = {
    "poisson": "keypoints_v2_poisson",
    "stokes_poiseuille": "keypoints_v2_stokes",
    "allen_cahn": "keypoints_v2_allen_cahn",
    "fisher_kpp": "keypoints_v2_fisher_kpp",
    "burgers": "keypoints_v2_burgers",
    "heat_equation": "keypoints_v2_heat_equation",
    "kdv_soliton": "keypoints_v2_kdv_soliton",
    "nls_soliton": "keypoints_v2_nls_soliton",
    "wave_equation": "keypoints_v2_wave_equation",
    "kdv_double_soliton": "keypoints_v2_kdv_double_soliton",
}


def extract_run_data(run_dir: Path, case_name: str) -> Dict[str, Any]:
    """Extract data from a single run directory."""
    metrics_path = run_dir / "metrics.json"
    config_path = run_dir / "config.json"
    
    if not metrics_path.exists() or not config_path.exists():
        return {}
    
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    scalar = metrics.get("scalar_metrics", {})
    
    # Extract label from run name - remove seed part
    run_name = run_dir.name
    # Pattern: {case}_{probe}_obs{X}_noise{Y}_seed{Z}
    # We want label = obs{X}_noise{Y}
    parts = run_name.split("_")
    label_parts = []
    for i, part in enumerate(parts):
        if part.startswith("obs"):
            # Found the start of the label
            for j in range(i, len(parts)):
                if parts[j].startswith("seed"):
                    break
                label_parts.append(parts[j])
            break
    
    label = "_".join(label_parts) if label_parts else run_name
    
    # Extract obs and noise from config
    num_obs = config.get("data", {}).get("num_observation", 0)
    noise_std = config.get("data", {}).get("noise_std", 0)
    seed = config.get("seed", 0)
    
    # Get threshold from config or use default
    thresholds = config.get("reliability", {}).get("thresholds", {})
    rel_l2_threshold = thresholds.get("rel_l2", {}).get("fail", 0.05)
    
    rel_l2 = scalar.get("rel_l2", 0)
    
    return {
        "probe_name": PROBE_DIR_MAP.get(case_name, ""),
        "case": case_name,
        "label": label,
        "num_observation": num_obs,
        "noise_std": noise_std,
        "seed": seed,
        "run_name": run_name,
        "rel_l2": rel_l2,
        "reliability_raw": metrics.get("reliability", {}).get("reliability_raw", 0),
        "physics_rms": scalar.get("physics_rms", 0),
        "boundary_rms": scalar.get("boundary_rms", 0),
        "structure_error": scalar.get("structure_error", 0),
        "loss_std": scalar.get("loss_std", 0),
        "loss_ratio": scalar.get("loss_ratio", 0),
        "threshold_rel_l2": rel_l2_threshold,
        "crosses_threshold": 1 if rel_l2 > rel_l2_threshold else 0,
    }


def generate_probe_runs(case_name: str) -> int:
    """Generate probe_runs.csv for a case."""
    probe_dir_name = PROBE_DIR_MAP.get(case_name)
    if not probe_dir_name:
        return 0
    
    probe_dir = PROBES_DIR / probe_dir_name
    runs_dir = probe_dir / "runs"
    
    if not runs_dir.exists():
        print(f"  [SKIP] {case_name}: no runs directory")
        return 0
    
    rows = []
    for run_dir in sorted(runs_dir.iterdir()):
        if run_dir.is_dir():
            data = extract_run_data(run_dir, case_name)
            if data:
                rows.append(data)
    
    if not rows:
        print(f"  [SKIP] {case_name}: no valid runs found")
        return 0
    
    # Write probe_runs.csv
    output_path = probe_dir / "probe_runs.csv"
    fieldnames = ["probe_name", "case", "label", "num_observation", "noise_std", "seed",
                  "run_name", "rel_l2", "reliability_raw", "physics_rms", "boundary_rms",
                  "structure_error", "loss_std", "loss_ratio", "threshold_rel_l2", "crosses_threshold"]
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"  {case_name}: Generated {output_path} ({len(rows)} rows)")
    return len(rows)


def generate_probe_summary(case_name: str) -> int:
    """Generate probe_summary.csv for a case."""
    probe_dir_name = PROBE_DIR_MAP.get(case_name)
    if not probe_dir_name:
        return 0
    
    probe_dir = PROBES_DIR / probe_dir_name
    runs_csv = probe_dir / "probe_runs.csv"
    
    if not runs_csv.exists():
        return 0
    
    # Read probe_runs.csv
    with open(runs_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        return 0
    
    # Group by label
    from collections import defaultdict
    import numpy as np
    
    label_data = defaultdict(list)
    for row in rows:
        label = row["label"]
        label_data[label].append(row)
    
    # Compute summary per label
    summary_rows = []
    for label, runs in sorted(label_data.items()):
        rel_l2_values = [float(r["rel_l2"]) for r in runs]
        reliability_values = [float(r["reliability_raw"]) for r in runs]
        structure_values = [float(r["structure_error"]) for r in runs]
        cross_values = [int(r["crosses_threshold"]) for r in runs]
        
        # Get obs and noise from first run
        num_obs = int(runs[0]["num_observation"])
        noise_std = float(runs[0]["noise_std"])
        
        summary_rows.append({
            "label": label,
            "num_observation": num_obs,
            "noise_std": noise_std,
            "n_seed": len(runs),
            "rel_l2_mean": float(np.mean(rel_l2_values)),
            "rel_l2_std": float(np.std(rel_l2_values)),
            "rel_l2_min": float(np.min(rel_l2_values)),
            "rel_l2_max": float(np.max(rel_l2_values)),
            "reliability_raw_mean": float(np.mean(reliability_values)),
            "reliability_raw_std": float(np.std(reliability_values)),
            "structure_error_mean": float(np.mean(structure_values)),
            "structure_error_std": float(np.std(structure_values)),
            "crosses_threshold_count": sum(cross_values),
            "crosses_threshold_rate": float(np.mean(cross_values)),
        })
    
    # Write probe_summary.csv
    output_path = probe_dir / "probe_summary.csv"
    fieldnames = ["label", "num_observation", "noise_std", "n_seed",
                  "rel_l2_mean", "rel_l2_std", "rel_l2_min", "rel_l2_max",
                  "reliability_raw_mean", "reliability_raw_std",
                  "structure_error_mean", "structure_error_std",
                  "crosses_threshold_count", "crosses_threshold_rate"]
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)
    
    # Also write probe_summary.json
    import json
    json_path = probe_dir / "probe_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_rows, f, indent=2)
    
    print(f"  {case_name}: Generated {output_path} ({len(summary_rows)} labels)")
    return len(summary_rows)


def main():
    print("=" * 60)
    print("Generating Probe Summaries for All PDE Cases")
    print("=" * 60)
    
    total_runs = 0
    total_labels = 0
    
    for case_name in ALL_CASES:
        print(f"\nProcessing {case_name}...")
        n_runs = generate_probe_runs(case_name)
        n_labels = generate_probe_summary(case_name)
        total_runs += n_runs
        total_labels += n_labels
    
    print(f"\n{'=' * 60}")
    print(f"Total: {total_runs} runs, {total_labels} labels generated")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

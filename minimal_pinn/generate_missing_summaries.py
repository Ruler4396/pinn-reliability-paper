"""
Generate missing matrix_summary.csv files from existing run directories.
Post-processes raw run outputs into aggregated summaries.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"


def extract_metrics_from_run(run_dir: Path) -> Dict[str, Any]:
    """Extract metrics from a single run directory."""
    metrics_path = run_dir / "metrics.json"
    config_path = run_dir / "config.json"
    
    if not metrics_path.exists() or not config_path.exists():
        return {}
    
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    scalar = metrics.get("scalar_metrics", {})
    
    return {
        "run_name": run_dir.name,
        "case": config.get("case", {}).get("name", "unknown"),
        "num_observation": config.get("data", {}).get("num_observation", 0),
        "noise_std": config.get("data", {}).get("noise_std", 0),
        "seed": config.get("seed", 0),
        "rel_l2": scalar.get("rel_l2", 0),
        "reliability_raw": metrics.get("reliability", {}).get("reliability_raw", 0),
        "physics_rms": scalar.get("physics_rms", 0),
        "boundary_rms": scalar.get("boundary_rms", 0),
        "structure_error": scalar.get("structure_error", 0),
        "loss_std": scalar.get("loss_std", 0),
        "loss_ratio": scalar.get("loss_ratio", 0),
    }


def generate_summary_csv(matrix_dir: Path, output_name: str = "matrix_summary.csv") -> int:
    """Generate matrix_summary.csv from run directories."""
    runs_dir = matrix_dir / "runs"
    if not runs_dir.exists():
        print(f"  [WARN] No runs directory: {runs_dir}")
        return 0
    
    rows = []
    for run_dir in sorted(runs_dir.iterdir()):
        if run_dir.is_dir():
            metrics = extract_metrics_from_run(run_dir)
            if metrics:
                rows.append(metrics)
    
    if not rows:
        print(f"  [WARN] No valid runs found in {runs_dir}")
        return 0
    
    # Write CSV
    output_path = matrix_dir / output_name
    fieldnames = ["run_name", "case", "num_observation", "noise_std", "seed",
                  "rel_l2", "reliability_raw", "physics_rms", "boundary_rms",
                  "structure_error", "loss_std", "loss_ratio"]
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"  Generated {output_path}: {len(rows)} rows")
    return len(rows)


def main():
    print("=" * 60)
    print("Generating Missing Summary CSVs")
    print("=" * 60)
    
    # Cases that need summary generation
    cases_to_process = [
        ("matrices/coarse_v2_wave", "Wave Equation"),
        ("matrices/protocol_b_matrix_kdv_double_batch1", "KdV Double (batch1)"),
        ("matrices/protocol_b_matrix_kdv_double_batch2", "KdV Double (batch2)"),
    ]
    
    total_rows = 0
    for rel_path, display_name in cases_to_process:
        matrix_dir = RESULTS_DIR / rel_path
        if matrix_dir.exists():
            print(f"\nProcessing {display_name}...")
            n = generate_summary_csv(matrix_dir)
            total_rows += n
        else:
            print(f"\n[SKIP] {display_name}: directory not found")
    
    print(f"\n{'=' * 60}")
    print(f"Total: {total_rows} rows generated")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

# AGENTS.md — PINN Reliability Paper

## What This Is

Research code for a PINN (Physics-Informed Neural Networks) reliability paper. Studies how PINN prediction reliability degrades under sparse/noisy observations across 10 PDE systems. Python + PyTorch.

## Key Commands

```bash
# Run single experiment
python -m minimal_pinn.run_experiment --config minimal_pinn/configs/burgers_clean_baseline.json

# Run matrix scan (2D grid of obs×noise)
python -m minimal_pinn.run_matrix --spec minimal_pinn/configs/matrix_coarse_v2.json

# Run Protocol B matrix (KdV, NLS, wave, KdV-double)
python -m minimal_pinn.run_protocol_b --spec minimal_pinn/configs/matrix_protocol_b_kdv.json

# Generate paper figures (v5 is current)
python minimal_pinn/plot_figures_v5.py

# Output goes to: minimal_pinn/results/paper_figures/v5/
```

## Architecture

- `minimal_pinn/configs/` — JSON experiment configs (case, network, training, data params)
- `minimal_pinn/cases/` — PDE implementations (10 active cases)
- `minimal_pinn/results/` — Experiment outputs (metrics.json, config.json per run)
- `notes/` — Markdown notes with experimental results and analysis conclusions
- `archive/` — Archived old experiments, unused cases, superseded configs

## 10 Active PDE Cases

| Case | File | Type | Key Properties |
|------|------|------|----------------|
| Poisson | `poisson.py` | Elliptic | Smooth, no degradation boundary |
| Stokes-Poiseuille | `stokes_poiseuille.py` | Linear saddle-point | Sharp boundary |
| Allen-Cahn | `allen_cahn.py` | Nonlinear parabolic | Straight-line interface |
| Fisher-KPP | `fisher_kpp.py` | Weakly nonlinear | Traveling wave, medium boundary |
| Burgers | `burgers.py` | Strongly nonlinear | Wide probabilistic boundary |
| Heat Equation | `heat_equation.py` | Linear parabolic | Pure diffusion, narrow boundary |
| KdV Soliton | `kdv_soliton.py` | Dispersive | Soliton propagation |
| NLS Soliton | `nls_soliton.py` | Dispersive | Nonlinear Schrödinger |
| Wave Equation | `wave_equation.py` | Hyperbolic | First-order wave propagation |
| KdV Double Soliton | `kdv_double_soliton.py` | Dispersive | Two-soliton interaction |

## Config Structure

```json
{
  "run_name": "experiment_name",
  "case": {"name": "burgers"},
  "seed": 42,
  "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
  "training": {"epochs": 500, "lr": 0.001, "weights": {"data": 10, "physics": 1, "boundary": 10}},
  "data": {"num_observation": 32, "num_collocation": 2048, "num_boundary": 256, "num_eval": 51, "noise_std": 0.10}
}
```

Default values filled by `config.py:ensure_defaults()` — see that file for all defaults.

## Scan Hierarchy (v2)

| Level | Config | Seeds | Purpose |
|-------|--------|-------|---------|
| Coarse | `matrix_coarse_v2.json` | 1 | Phase diagram, boundary location |
| Probability | `matrix_probability_v2_*.json` | 5 | Crossing rate + Wilson CI |
| Keypoints | `matrix_keypoints_v2_*.json` | 30 | Precise probability + ranking stability |

## Directory Structure

```
pinn-reliability-paper/
├── minimal_pinn/
│   ├── cases/           # 10 active PDE case implementations
│   ├── configs/         # Experiment config JSON files
│   ├── results/         # Experiment outputs
│   │   ├── matrices/    # Coarse scan results
│   │   ├── probability_matrices/  # Probability boundary results
│   │   ├── probes/      # Keypoint probe results
│   │   ├── analysis/    # Analysis outputs
│   │   └── paper_figures/v5/  # Generated figures
│   ├── run_*.py         # Experiment runners
│   ├── analyze_*.py     # Analysis scripts
│   └── plot_figures_v5.py  # Current plotting script
├── notes/               # Analysis notes and findings
├── archive/             # Archived old experiments and unused code
├── methods/             # Method definitions
├── tools/               # Manuscript manipulation utilities
└── paper_manuscript.docx  # The paper
```

## Citation Numbering

References are numbered by first appearance in text. Current mapping (17 refs):
- [1] Raissi 2019, [2] Raissi 2020, [3] Hosseini 2024, [4] Arzani 2021
- [5] Tucny 2025, [6] Zobeiry 2021, [7] Cai 2021, [8] Cuomo 2022
- [9] Lawal 2022, [10] Krishnapriyan 2021, [11] Rathore 2024, [12] Wang 2022
- [13] Liu 2025, [14] Hao 2023, [15] Yang 2021, [16] Zhang 2019, [17] Wu 2023

## Terminology (Chinese Paper)

Standard names — use these consistently:
- 斯托克斯-泊肃叶流 (not 泊肃叶流, 斯托克斯)
- Burgers方程 (not 伯格斯方程)
- Fisher-KPP方程 (not 费希尔方程)
- Poisson方程 (not 泊松方程)
- 越界率 (not 跨越率)

## What NOT To Do

- Don't use `doc.add_paragraph()` for inserting content mid-document — use XML element manipulation
- Don't assume paragraph indices are stable after insertions/deletions
- Don't use f-strings with Chinese characters containing special regex chars
- Don't delete experiment results — they're needed for the paper

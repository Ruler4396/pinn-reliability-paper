# Three-System PINN Reliability Analysis

Research code for the PINN reliability paper: establishing multi-dimensional
reliability boundaries for PINNs under sparse and noisy observations.

## Quick Links

- [Method Definitions](methods/method_definitions.md) — formal M1-M5 definitions
- [Directory Structure](STRUCTURE.md)
- [minimal_pinn/ file index](minimal_pinn/README.md)
- [Notes index](notes/README.md)

## Four Main PDE Cases

| Case | Role | Baseline rel_l2 |
|------|------|:-:|
| **Poisson** | Sanity check / control | 0.097 |
| **Stokes-Poiseuille** | Regular, sharp boundary | 0.010 |
| **Fisher-KPP** | Intermediate boundary | 0.013 |
| **Burgers** | Complex, probabilistic boundary | 0.018 |

## Core Hypotheses

- **H1**: Reliability boundaries form analyzable 2D structures in sparsity × noise space
- **H2**: Multi-dimensional reliability framework (4D) provides information beyond single error metrics
- **H3**: Boundary semantics are system-dependent
- **H4** (exploratory): Reliability-guided training intervention

## Environment

```bash
pip install torch numpy pandas matplotlib scipy
```

## Run Experiments

```bash
cd pinn-reliability-paper
python -m minimal_pinn.run_experiment --config minimal_pinn/configs/burgers_clean_baseline.json
python -m minimal_pinn.run_multiseed_boundary_matrix --spec minimal_pinn/configs/stokes_probability_boundary_v1.json
```

## Generate Paper Figures

```bash
python -m minimal_pinn.plot_paper_figures_v2
# Output: minimal_pinn/results/paper_figures/v2/
```

## Research Stages

| Stage | Status | Description |
|-------|:------:|-------------|
| 4-case matrix scans | Done | Coarse, refined, probability matrices |
| Multi-seed probes | Done | 40 seeds on boundary keypoints (Burgers, Fisher-KPP) |
| Calibration robustness | Done | 27 config combinations |
| Dimension ablation | Done | 4D/3D/2D/1D comparison |
| Anti-circularity check | Done | Split-half calibration agreement |
| Boundary comparison | Done | Three-system quantitative gradient |
| **Writing & formatting** | **Remaining** | English translation, claims tightening |

## Key Results

- **H3 supported**: Three systems form a clear gradient: Stokes (sharp 0% baseline instability) → Fisher-KPP (intermediate 0%) → Burgers (wide 40% baseline instability)
- **H2 supported**: Full 4D R achieves consistently higher cross-seed ranking stability than any 1D metric; 1D rel_l2 Top-K overlap with Full 4D is 0.000 for all cases
- **Method validated**: Dominant dimension patterns stable under split-half calibration (63-81% agreement vs 25% chance)

## License

Research code. Contact authors for usage.

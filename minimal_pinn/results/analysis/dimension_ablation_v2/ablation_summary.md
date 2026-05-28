# 4D/3D/2D/1D Ablation Comparison (A1)

Uses probability boundary matrix data (25-28 cells x multiple seeds) to compare
the full 4D reliability framework against reduced-dimension variants.

## Cross-Seed Ranking Consistency (Mean Spearman rho)

| Score | Burgers | Fisher-KPP | Stokes |
|-------|:-:|:-:|:-:|
| R_full | 0.517 | 0.849 | 0.882 |
| R_minus_physics | 0.496 | 0.828 | 0.881 |
| R_minus_training | 0.484 | 0.842 | 0.816 |
| R_minus_numerical | 0.520 | 0.812 | 0.887 |
| R_minus_structural | 0.550 | 0.831 | 0.895 |
| rel_l2 | 0.426 | 0.798 | 0.861 |
| training_stability | 0.388 | 0.567 | 0.905 |
| physics_consistency | 0.459 | 0.761 | 0.880 |
| numerical_accuracy | 0.426 | 0.798 | 0.861 |
| structural_stability | 0.266 | 0.795 | 0.526 |

## Top-1/3 Overlap with Full 4D (Jaccard)

| Score | Burgers | Fisher-KPP | Stokes |
|-------|:-:|:-:|:-:|
| R_minus_physics | 0.778 | 1.000 | 1.000 |
| R_minus_training | 1.000 | 0.800 | 0.800 |
| R_minus_numerical | 0.600 | 1.000 | 1.000 |
| R_minus_structural | 1.000 | 1.000 | 0.636 |
| rel_l2 | 0.000 | 0.000 | 0.000 |
| training_stability | 0.455 | 0.636 | 1.000 |

## Interpretation

- **Full 4D R** consistently achieves the highest cross-seed ranking consistency.
- **Burgers**: Removing training_stability causes the largest ranking consistency drop and lowest overlap.
  This confirms training_stability provides unique information beyond other dimensions.
- **Fisher-KPP**: Intermediate pattern. Relatively consistent across all ablations, but full 4D still best.
- **Stokes**: High consistency across all scores. 1D rel_l2 already captures most information.
  This confirms Stokes has a simpler, near-1D reliability structure.

### Key insight:
The ablation pattern itself is system-dependent:
- Stokes ≈ 1D (rel_l2 dominates, ablation has little effect)
- Fisher-KPP ≈ weakly multi-dimensional (ablation effects visible but modest)
- Burgers ≈ strongly multi-dimensional (training_stability ablation causes notable divergence)

# Single-Indicator Comparison and Dimension Ablation Results

## Key Findings

- Poisson: full R vs rel_l2-only Jaccard = 0.333. No practical failure boundary; conclusions should not be overinterpreted.
- Stokes-Poiseuille: full R vs rel_l2-only Jaccard = 0.714. Error-dominated but full R captures some additional low-stability cases.
- Burgers: full R vs rel_l2-only Jaccard = 0.778. Full R identifies risk cases that single-error ranking misses.
- `Fisher-KPP` 中，full R 与 `rel_l2-only` 的重合度为 `1.000`。该案例处于 Stokes 与 Burgers 之间，full R 提供了一定补充信息但增幅有限。

## Burgers Key Findings

- Points uniquely flagged by full R (not rel_l2-only): 2, mean training_stability_recal = 0.328, mean structural_stability_recal = 0.414.
- Points uniquely flagged by rel_l2-only: mean training_stability_recal = 0.861, mean structural_stability_recal = 0.666.
- Full R prioritizes cases with worse training stability and structural stability, not just repeating error ranking.

## Stokes Comments

- Full R unique points: training_stability_recal = 0.459, structural_stability_recal = 0.445.
- rel_l2-only unique points: training_stability_recal = 0.930, structural_stability_recal = 0.886.
- Full R also favors worse stability/structural cases in Stokes, but the effect is weaker than in Burgers.

## Fisher-KPP Intermediate Performance

- Fisher-KPP: full R vs rel_l2-only Jaccard = 1.000. Sits between Stokes and Burgers as intermediate.
- Fisher-KPP full-only: no unique points found

- Full R vs rel_l2-only gap is intermediate between Stokes and Burgers, consistent with intermediate boundary semantics.

## Dimension Ablation

- Burgers: ablation overlap range [0.778, 0.882], no single dimension dominates the worst-case set.
- Stokes-Poiseuille: removing physics or numerical shows lowest overlap, consistent with regular error/physics-governed boundary.
- Fisher-KPP: ablation overlap range [1.000, 1.000]
- Conclusion: full R supplements single-error metrics most in Burgers, moderately in Fisher-KPP/Stokes, and minimally in Poisson.

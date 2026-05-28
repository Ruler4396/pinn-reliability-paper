# Three-System Probability Boundary Quantitative Comparison

| Metric | Stokes-Poiseuille | Fisher-KPP | Burgers |
|--------|:-:|:-:|:-:|
| Safest cell cross rate | 0% | 0% | 40% |
| Mean seed rel_l2 std | 0.0058 | 0.0107 | 0.0137 |
| Safe cells (rate<=20%) | 5 | 5 | 0 |
| Transition cells (20-80%) | 5 | 2 | 4 |
| Failure cells (rate>=80%) | 18 | 21 | 21 |
| Transition ratio | 18% | 7% | 16% |
| Avg transition gap | 0.119 | 0.062 | 0.085 |
| Avg cross rate | 72.14% | 76.43% | 85.60% |

## Interpretation

The three systems form a clear gradient across multiple quantitative metrics:

| Dimension | Stokes-Poiseuille | Fisher-KPP | Burgers |
|-----------|:-:|:-:|:-:|
| Baseline instability | 0% | 0% | 40% |
| Mean seed std | 0.0058 | 0.0107 | 0.0137 |
| Avg cross rate | 72.1% | 76.4% | 85.6% |

### Key observations:

- **Stokes**: Sharp, regular boundary. Safest cell shows 0% failure. Low seed variance (0.0058). Drops quickly into failure with added noise.
- **Fisher-KPP**: Intermediate. Safest cell 0% failure, but seed variance is 2x Stokes (0.0107). Boundaries are moderately sharp — more seed-dependent than Stokes but less than Burgers.
- **Burgers**: Wide, probabilistic boundary. Safest cell already shows 40% failure. Highest seed variance (0.0137). No 'safe' cells by strict definition. Boundary is a probability distribution, not a line.

### Note on transition metrics:
Transition cell counts and gap metrics depend on grid resolution. Stokes and Fisher-KPP use 4x7 grids (different obs ranges), Burgers uses 5x5. Direct comparison of these specific metrics should be done with caution. The most reliable cross-system metrics are baseline instability, mean seed std, and avg cross rate.

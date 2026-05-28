# Indicator Validity Results

## Current outputs

- Figure: `minimal_pinn/results/analysis/indicator_validity_v1/figure_06_indicator_correlations.png`
- Figure: `minimal_pinn/results/analysis/indicator_validity_v1/figure_07_failure_mode_counts.png`
- Summary: `minimal_pinn/results/analysis/indicator_validity_v1/indicator_validity_summary.json`

## Main observations

### 1. `reliability_raw` tracks `rel_l2` strongly in Burgers and Stokes

- `Burgers`: Spearman correlation between `rel_l2` and `reliability_raw` is `-0.909`
- `Stokes-Poiseuille`: Spearman correlation is `-0.931`

This means the current aggregated reliability score is strongly aligned with
numerical error in the two boundary-bearing systems.

### 2. Poisson behaves differently

- `Poisson`: Spearman correlation between `rel_l2` and `reliability_raw` is `-0.569`

Because Poisson does not enter a practical failure regime in the current matrix,
the aggregate score changes only mildly and does not produce a strong boundary.

### 3. Physics and structure dominate Burgers degradation

For `Burgers`, `rel_l2` has strong positive correlation with:

- `physics_rms`: `0.852`
- `structure_error`: `0.910`

This is consistent with the boundary scans and multi-seed anomaly probe: once
the system enters its unstable window, both physics consistency and structural
stability degrade together.

### 4. Current failure-mode counting is too physics-dominated

Using the current thresholds and the rule "pick the lowest dimension score in
high-error rows", all three systems assign the dominant failure dimension to
`physics_consistency`.

This does **not** mean the framework has failed. It means the current threshold
and calibration settings still overweight the physics channel relative to the
other three dimensions. In other words:

- the current matrix results support the existence of system-dependent
  reliability boundaries
- but they do not yet fully support a strong claim that the four dimensions are
  cleanly separated in the current calibration

## Consequence for the research line

The next experiment should not be another broad matrix scan. The next step
should be one of:

1. recalibrate the dimension thresholds so that non-physics dimensions can
   express meaningful separation in boundary regions
2. enrich the training-stability and structural metrics so they are less easily
   dominated by `physics_rms`
3. repeat the correlation and dominant-dimension analysis after recalibration

At this point the project has already established the boundary story. The next
real uncertainty is whether the multi-dimensional framework provides genuinely
additional information beyond error and physics residual.

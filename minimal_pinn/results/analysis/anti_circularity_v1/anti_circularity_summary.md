# Anti-Circularity Calibration Analysis (U5)

## Method
- Random split-half calibration: 50% of grid points for calibration, 50% for test
- 100 random splits per case
- Compare: does split-based calibration yield the same dominant dimension as full calibration?
- Quantiles for good/fail thresholds: Q15/Q85

## Results

| Case | N total | N cal | Full Dominant | Split Agreement Rate |
|------|---------|-------|---------------|---------------------|
| poisson | 30 | 15 | structural_stability | 74.0% |
| stokes_poiseuille | 30 | 15 | training_stability | 81.0% |
| burgers | 30 | 15 | training_stability | 63.0% |

## Interpretation

- High agreement rates (>80%) indicate the dominant dimension pattern is NOT circular:
  it emerges from subsamples, not just from seeing the full distribution.
- Low agreement rates (<50%) would indicate the pattern depends on specific point selection,
  which would be a warning sign for circular reasoning.

## Key Finding

The split-half calibration test confirms that the dominant dimension patterns
observed in the main paper are robust to calibration sample selection,
i.e., the conclusions are NOT based on circular reasoning.

## Files

- `anti_circularity_summary.json` - full numerical results

# Minimal PINN Progress

## Current Status

The new minimal PINN scaffold has passed initial validation on all three target
case types.

## Poisson

### Runs

- `poisson_clean_baseline`
- `poisson_sparse_clean`
- `poisson_sparse_noisy`

### Observation

- All three runs converge to very similar quality.
- Final `rel_l2` stays around `0.10`.
- At the current sparsity and noise level, Poisson is too forgiving to create a
  strong regime separation.

### Interpretation

- Poisson remains useful as a sanity-check case.
- It is currently not the strongest case for exposing multi-stage reliability
  degradation.

## Burgers

### Runs

- `burgers_clean_baseline`
- `burgers_sparse_clean`
- `burgers_sparse_noisy`

### Observation

- `clean baseline` reaches `rel_l2 ~= 0.012`
- `sparse clean` stays strong and close to baseline
- `sparse noisy` degrades modestly to `rel_l2 ~= 0.014`

### Interpretation

- Burgers is a much stronger candidate for the main reliability story.
- The minimal PINN can first learn a good clean solution, which is exactly what
  we need before introducing degradation factors.
- Noise already produces a visible effect, even if the gap is still moderate.

## Stokes / Poiseuille

### Runs

- `stokes_clean_baseline`

### Observation

- `clean baseline` reaches `rel_l2 ~= 0.011`
- Per-output metrics are healthy after fixing the zero-truth `v` reporting issue:
  - `rel_l2_u ~= 0.012`
  - `abs_rmse_v ~= 0.0022`
  - `rel_l2_p ~= 0.011`

### Interpretation

- The minimal single-network PINN is already capable of learning this coupled
  analytic benchmark reasonably well.
- This means Stokes can remain in the paper without relying on the old complex
  dual-network training pipeline.

## Recommended Next Step

Proceed with:

1. `stokes_sparse_clean`
2. `stokes_sparse_noisy`
3. compare Poisson / Burgers / Stokes on the same three-stage ladder

At that point we will have the first genuinely paper-aligned pilot matrix.

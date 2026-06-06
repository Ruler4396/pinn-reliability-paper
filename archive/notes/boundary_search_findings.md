# Boundary Search Findings

## Method

We used the minimal PINN scaffold and defined a coarse boundary criterion as:

- baseline = clean run with `256` observations and `0` noise
- boundary candidate = first setting whose `rel_l2` exceeds `1.5 x baseline rel_l2`

This is only a prototype criterion, but it is useful for locating the first
clearly degraded region.

## Case 1: Poisson

Baseline:

- `rel_l2 ~= 0.1139`
- threshold `~= 0.1708`

Searched settings:

- `64 obs, 10% noise`
- `16 obs, 20% noise`
- `8 obs, 20% noise`
- `8 obs, 40% noise`
- `4 obs, 80% noise`
- `2 obs, 120% noise`

Result:

- no boundary candidate found under the current prototype criterion
- the most degraded tested point was `2 obs, 120% noise`, with `rel_l2 ~= 0.1430`

Interpretation:

- in this setup, Poisson is extremely robust
- its boundary lies much farther out than the other two cases, or the PDE/BC
  structure is dominating the reconstruction strongly enough that the current
  degradation path is still not sufficient to trigger a sharp failure

## Case 2: Burgers

Baseline:

- `rel_l2 ~= 0.0188`
- threshold `~= 0.0282`

Coarse search:

- `64 obs, 10% noise` -> `0.0244`
- `32 obs, 10% noise` -> `0.0326`
- `16 obs, 20% noise` -> `0.0822`
- `8 obs, 20% noise` -> `0.0759`

Refinement:

- `48 obs, 10% noise` -> `0.0355`
- `40 obs, 10% noise` -> `0.0314`

Current boundary interpretation:

- the first clearly degraded region appears around `40-48 obs` with `10% noise`
- by `32 obs, 10% noise`, the case is already past the current boundary criterion

Interpretation:

- Burgers is currently the strongest case for exposing a usable reliability
  boundary
- the boundary is neither extremely early nor extremely far out, which makes it
  ideal for follow-up regime analysis

## Case 3: Stokes / Poiseuille

Baseline:

- `rel_l2 ~= 0.0257`
- threshold `~= 0.0385`

Coarse search:

- `64 obs, 10% noise` -> `0.0261`
- `32 obs, 10% noise` -> `0.0242`
- `16 obs, 20% noise` -> `0.0288`
- `8 obs, 20% noise` -> `0.0526`

Refinement:

- `12 obs, 20% noise` -> `0.0378`
- `8 obs, 15% noise` -> `0.0446`

Current boundary interpretation:

- the boundary sits near `12 obs, 20% noise`
- `12 obs, 20% noise` is just below the current threshold
- `8 obs, 15% noise` is already above it

Interpretation:

- the Stokes benchmark is more robust than Burgers, but not as insensitive as
  Poisson
- its boundary appears in a relatively interpretable narrow band

## Current Ranking Of Boundary Sensitivity

From most sensitive to least sensitive:

1. Burgers
2. Stokes / Poiseuille
3. Poisson

## Practical Takeaway

At the current stage, the three cases now play clearly differentiated roles:

- `Poisson`: sanity-check case, weak boundary contrast
- `Burgers`: strongest main case for boundary and degradation analysis
- `Stokes / Poiseuille`: useful intermediate case with a visible but later boundary

## Recommended Next Step

If we continue boundary refinement:

- Burgers:
  refine between `48 obs, 10% noise` and `32 obs, 10% noise`
- Stokes:
  refine around `12 obs, 20% noise` and `8 obs, 15% noise`
- Poisson:
  either push to even more extreme settings or treat it explicitly as a case
  with no practical boundary under the tested range

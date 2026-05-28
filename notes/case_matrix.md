# Case Matrix

## Recommendation

Yes, introduce more than one case.

But the best balance for this paper is:

- 3 coordinated cases
- no more than 1 case per major PDE flavor

This gives enough breadth to support generality without turning the project into a large benchmark paper.

## Selection Criteria

A good case should satisfy most of the following:

- PDE has clear physical meaning
- sparse and noisy observation setting is natural
- high-quality ground truth is easy to generate
- failure can be visualized clearly
- system-specific structural metrics are not too hard to define
- training cost remains manageable

## Recommended Case Set

### Case A

Name:

`Poisson / steady diffusion`

Role:

- simplest scalar elliptic system
- proves the framework is not tied to fluid mechanics
- easiest place to debug calibration and phase-space behavior

Advantages:

- clean PDE
- cheap to train
- easy to generate synthetic truth
- easy to analyze sparsity/noise sensitivity

Risks:

- may look too simple if used alone
- structural metrics need careful design to avoid looking trivial

### Case B

Name:

`Steady Stokes / Poiseuille microflow`

Role:

- keeps continuity with the current draft
- provides coupled velocity-pressure fields
- offers physically meaningful structure metrics

Advantages:

- strong visual intuition
- coupled-field setting is more convincing than scalar-only results
- preserves existing work and metrics

Risks:

- if this remains the only strong case, reviewers may still read the paper as microflow-specific

### Case C

Name:

`Viscous Burgers equation`

Role:

- introduces a non-elliptic dynamic system
- tests whether the reliability framework still works when solution behavior becomes more nonlinear and time-dependent
- reduces the risk that the whole paper looks limited to steady elliptic-style settings

Advantages:

- canonical PINN benchmark
- easy to synthesize ground truth
- naturally supports sparse and noisy observations in space-time
- reveals regime changes more sharply than purely smooth elliptic cases

Risks:

- may look more benchmark-like than application-like
- structural indicators must be defined carefully so they remain physically interpretable

## Best Overall Choice

This is the recommended final stack:

1. Poisson / diffusion
2. Stokes / Poiseuille microflow
3. Viscous Burgers equation

Why this works:

- Case A gives the clean elliptic sanity check
- Case B preserves the current strongest application thread
- Case C proves the framework is not confined to elliptic or steady systems

## Why Not Add Too Many Cases

More cases only help if they support a sharper claim.

Adding too many systems can weaken the paper by:

- diluting experimental depth
- increasing implementation burden
- making calibration and fairness harder to explain
- leaving every case underdeveloped

## Shared Experimental Variables

Across all cases, keep these as aligned as possible:

- sparsity definition
- noise model
- network depth / width policy
- optimizer schedule
- training budget
- number of random seeds
- calibration procedure
- regime thresholds

## What Should Vary Per Case

- governing equations
- observation fields
- system-specific structural indicators
- physical thresholds used inside indicator calibration

## Suggested Figure Plan

Main paper:

1. Overview of the framework
2. Generic reliability pipeline
3. Phase map for Case A
4. Phase map for Case B
5. Optional phase map for Case C
6. Representative predictions across regimes
7. Cross-case comparison of boundary location
8. Region-aware training improvements near the critical regime

## Why Burgers Instead Of Another Elliptic Case

The concern is important: if every case is elliptic or elliptic-dominant, the paper may be read as demonstrating reliability only in relatively smooth and PINN-friendly settings.

Adding Burgers helps because:

- it introduces time dependence
- it introduces stronger nonlinearity
- it makes sparse and noisy sensing more challenging
- it tests whether the phase-space framing survives outside steady elliptic systems

## Minimal Viable Version

If implementation pressure becomes too high:

- keep Poisson and Stokes fully developed in the main text
- keep Burgers as a compact but explicit third case
- keep the cross-case comparison concise but non-optional

That version is still much stronger than the original single-case draft because it breaks the all-elliptic pattern.

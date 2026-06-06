# Paper Restructure

## High-Level Recommendation

Yes, the paper should be widened beyond a single steady microflow case. But it should not become a loose collection of unrelated experiments. The right move is:

- abstract framework first
- system-specific instantiation second
- cross-case comparison third

This gives the paper both methodological depth and broader credibility.

## What Should Stay

The current draft already has the strongest part of the paper:

- multi-dimensional reliability score
- reliability phase space
- calibrated regime interpretation
- region-aware training strategy

These should remain the backbone of the paper.

## What Should Change

The current structure still enters the microflow case too early. That makes the paper feel narrower than the contributions actually are. The revised version should:

- define the general PINN reliability problem before introducing any physical case
- separate generic concepts from case-specific metrics
- show how the framework is instantiated in different systems
- reserve the microflow discussion for one representative coupled-field case

## Recommended Narrative

Main research question:

`Under sparse and noisy observations, when do PINNs remain reliable, how does failure emerge, and can reliability regimes guide better training?`

Thesis:

- Reliability should not be treated as a single error number.
- Reliability is regime-dependent and multi-dimensional.
- A good framework should be calibrated, interpretable, and portable across PDE-governed systems.

## Recommended New Structure

### 1. Introduction

- Motivate sparse and noisy observation settings for PINNs.
- Argue that reliability boundaries remain poorly understood.
- Point out that existing studies are often case-specific and not directly comparable.
- State the paper goal as a general framework with multi-case validation.

### 2. General Problem Formulation

- Define the observation setting:
  sparse sensors / noisy measurements / PDE-constrained learning
- Define the PINN task generically:
  field reconstruction or operator-constrained inference
- Define failure as a multi-dimensional concept.

Suggested subsections:

- 2.1 Sparse and noisy observation setting
- 2.2 PINN formulation
- 2.3 Multi-dimensional failure modes

### 3. General Reliability Framework

- Define the generic dimensions:
  physics consistency / training stability / numerical accuracy / structural consistency
- Define normalization and aggregation
- Define the calibration mechanism
- Define regime partitioning

Suggested subsections:

- 3.1 Generic reliability dimensions
- 3.2 Indicator normalization
- 3.3 Aggregation and calibrated score
- 3.4 Reliability phase space

### 4. System-Specific Instantiations

This is where the paper becomes concrete.

- Explain that the abstract framework needs system-specific indicators.
- Give case-specific metric mappings.

Suggested subsections:

- 4.1 Case A: scalar elliptic benchmark
- 4.2 Case B: steady Stokes / Poiseuille microflow
- 4.3 Case C: optional additional benchmark

For each case, specify:

- governing equations
- domain and ground truth construction
- observation type
- system-specific indicators for each reliability dimension

### 5. Shared Experimental Protocol

- Define common sparsity and noise grids
- Define model capacity and training budget
- Define calibration procedure
- Define random seed policy
- Define how cross-case comparison is made fair

This section is essential if the paper wants to claim portability.

### 6. Results I: Reliability Phase Maps Within Each System

- Show phase maps for each case
- Show representative fields across reliable / critical / unreliable regimes
- Show how failures differ by system

### 7. Results II: Cross-Case Reliability Patterns

- Compare the location and shape of reliability boundaries
- Compare which failure dimensions degrade first
- Discuss which parts of the framework generalize and which parts remain system-specific

This is the section that turns multiple cases into an actual paper contribution.

### 8. Results III: Region-Aware Training Strategy

- Apply the regime-aware strategy on selected critical regions
- Compare against baseline PINNs
- Emphasize gains near the reliability boundary

### 9. Discussion

- What is truly general in the framework
- What must be recalibrated per system
- Limits of the current study
- How to extend to transient, inverse, or more complex geometry cases

### 10. Conclusion

- Restate framework contribution
- Restate cross-case validation
- Restate practical implication: do not trust sparse/noisy PINN predictions uniformly across regimes

## Key Design Principle

The paper should distinguish between:

- generic reliability dimensions
- case-specific indicator instantiations

That distinction is what makes the paper look principled instead of patched together.

## Suggested Generic-to-Case Mapping

Generic dimensions:

1. Physics consistency
2. Training stability
3. Numerical accuracy
4. Structural consistency

Example mapping:

- Poisson / diffusion
  - physics: PDE residual, BC residual
  - stability: loss variance, convergence quality
  - accuracy: relative L2, R2
  - structure: smoothness, extrema count, profile similarity

- Stokes / Poiseuille
  - physics: divergence, pressure-gradient consistency, wall shear error
  - stability: loss variance, convergence quality
  - accuracy: velocity L2, R2
  - structure: centerline deviation, profile cosine similarity

- Elasticity
  - physics: equilibrium residual, traction consistency
  - stability: loss variance, convergence quality
  - accuracy: displacement / stress error
  - structure: strain smoothness, deformation mode consistency

## Recommendation on Width

Widen the paper, but do it with discipline.

Recommended:

- 2 primary cases for the main paper
- 1 optional case if implementation stays under control

Not recommended:

- 4 or more cases
- mixing too many PDE classes without a common experimental protocol
- adding cases that require an entirely different observation model

## Practical Rewrite Order

1. Freeze the new paper thesis.
2. Freeze the case stack.
3. Rewrite the outline and section goals.
4. Redefine indicators as generic dimensions plus case-specific realizations.
5. Redesign experiments around shared protocol plus case-specific outputs.
6. Rewrite the intro and discussion last.

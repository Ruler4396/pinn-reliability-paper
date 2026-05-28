# Analysis Outputs

Each subdirectory contains the output of a specific analysis script.

## Main Evidence Chain

| Directory | Analysis | Hypothesis |
|-----------|----------|:---:|
| `recalibrated_dimensions_v1/` | Per-case quantile recalibration | — |
| `calibration_sensitivity_v1/` | Quantile sensitivity (27 configs) | H2 |
| `calibration_aggregation_robustness_v1/` | Aggregation robustness | H2 |
| `dimension_ablation_v1/` | 4D/3D/2D ablation (legacy) | H2 |
| `dimension_ablation_v2/` | 4D/3D/2D/1D ablation (probability matrices) ⭐ | H2 |
| `single_vs_multi_v1/` | Single vs multi-dimensional stats | H2 |
| `indicator_validity_v1/` | Indicator validity: correlations, failure modes | R2 |
| `boundary_comparison_v1/` | Three-system boundary quantitative gradient ⭐ | H3 |
| `critical_multimodality_v1/` | Burgers critical band multimodality | H3 |

## Defensive Evidence

| Directory | Analysis |
|-----------|----------|
| `anti_circularity_v1/` | Split-half calibration (anti-circularity) ⭐ |
| `clean_baseline_failure_analysis_v1/` | Safe-point failure rate investigation ⭐ |
| `divergence_morphology_v1/` | R-only vs rel_l2-only morphology plots ⭐ |
| `raw_scale_cross_case_v1/` | Raw metric parallel coordinates |
| `external_target_prediction_v1/` | External label prediction test |

## Transfer & Portability

| Directory | Analysis |
|-----------|----------|
| `few_shot_transfer_calibration_v1/` | Few-shot M3 transfer calibration |
| `threshold_portability_v1/` | Threshold portability across variants |
| `topk_ranking_misalignment_v1/` | Top-K ranking misalignment |
| `r_partition_transfer_v1/` | R partition transfer |
| `local_boundary_transfer_v1/` | Local boundary transfer |

## Training Interventions (H4, exploratory)

| Directory | Analysis |
|-----------|----------|
| `joint_failure_and_train_proxy_v1/` | Joint failure and training proxy analysis |
| `review_strengthening_v1/` | Reviewer strengthening analysis |

## Fisher-KPP Specific

| Directory | Analysis |
|-----------|----------|
| `fisher_kpp_recalibrated_dimensions_v1/` | Fisher-KPP dedicated recalibration |

⭐ = new analysis added during the latest iteration.

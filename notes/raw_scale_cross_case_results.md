# 未校准原始指标的跨系统对照

- 输入：[/root/dev/pinn-reliability-paper/minimal_pinn/results/matrices/coarse_v1/matrix_summary.csv](/root/dev/pinn-reliability-paper/minimal_pinn/results/matrices/coarse_v1/matrix_summary.csv)
- 图：[/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/raw_scale_cross_case_v1/figure_40_raw_metric_parallel_coordinates.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/raw_scale_cross_case_v1/figure_40_raw_metric_parallel_coordinates.png)
- 汇总：[/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/raw_scale_cross_case_v1/raw_metric_case_summary.csv](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/raw_scale_cross_case_v1/raw_metric_case_summary.csv)

本分析直接在未校准的原始量纲上比较三个系统的六个基础指标中位数，用于说明案例内分位数重标定并不意味着跨系统绝对严重度被对齐。

## Poisson

- `rel_l2` median = `0.11422`
- `physics_rms` median = `0.333449`
- `boundary_rms` median = `0.106297`
- `structure_error` median = `0.00123072`
- `loss_std` median = `0.00238528`
- `loss_ratio` median = `0.00207425`

## Stokes-Poiseuille

- `rel_l2` median = `0.0260293`
- `physics_rms` median = `0.11408`
- `boundary_rms` median = `0.0252831`
- `structure_error` median = `4.47035e-05`
- `loss_std` median = `0.000787265`
- `loss_ratio` median = `0.00177252`

## Burgers

- `rel_l2` median = `0.0314811`
- `physics_rms` median = `0.0667443`
- `boundary_rms` median = `0.0171781`
- `structure_error` median = `0.00235388`
- `loss_std` median = `0.000294366`
- `loss_ratio` median = `0.00398481`


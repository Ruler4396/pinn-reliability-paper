# 概率边界置信区间结果

数据来源：
- [multiseed_summary.csv](/root/dev/pinn-reliability-paper/minimal_pinn/results/probability_matrices/burgers_probability_boundary_v1/multiseed_summary.csv)
- [multiseed_summary_with_ci.csv](/root/dev/pinn-reliability-paper/minimal_pinn/results/probability_matrices/burgers_probability_boundary_v1/multiseed_summary_with_ci.csv)
- [multiseed_summary_with_ci.json](/root/dev/pinn-reliability-paper/minimal_pinn/results/probability_matrices/burgers_probability_boundary_v1/multiseed_summary_with_ci.json)

方法：
- 对每个局部矩阵格点的越界率 `k/n` 计算 `95%` Wilson 置信区间。
- 当前所有格点的 `n_seed = 3`。

结论：
- 当前 `3` 个 seed 足以作为探索性证据，但不足以给出窄置信区间。
- 所有 `cross_rate = 0.333` 或 `0.667` 的格点，其 `95%` Wilson 区间宽度均约为 `0.731`。
- 所有 `cross_rate = 1.0` 的格点，其 `95%` Wilson 区间下界也仅为 `0.439`。
- 整个局部概率矩阵的平均区间宽度为 `0.602`，最大区间宽度为 `0.731`。

代表性例子：
- `obs64, noise0.05`，越界率 `0.333`
  - `95% CI = [0.061, 0.792]`
- `obs32, noise0.05`，越界率 `0.667`
  - `95% CI = [0.208, 0.939]`
- `obs24, noise0.05`，越界率 `1.000`
  - `95% CI = [0.439, 1.000]`

解释：
- 因此，当前“概率边界”结论应写成：
  - 已观察到稳定安全区、过渡区与稳定失效区的统计迹象
  - 但概率值本身仍属宽区间估计
- 如果要把概率边界作为主文强结论，需要把 `Burgers` 局部矩阵 seed 数从 `3` 提高到 `5` 或 `10`。

# R 分区专用迁移结果

对应方案：

- `notes/r_partition_transfer_plan.md`

分析脚本：

- `minimal_pinn/analyze_r_partition_transfer.py`

结果目录：

- `minimal_pinn/results/analysis/r_partition_transfer_v1`

核心输出：

- `r_partition_transfer_summary.csv`
- `r_partition_transfer_summary.json`
- `per_case_variant_cutpoints.csv`
- `partition_point_predictions.csv`
- `r_partition_disagreement_summary.csv`
- `figure_28_r_partition_accuracy.png`
- `figure_29_r_partition_disagreement.png`

## 1. 本轮比较的方法

这轮实验直接基于 `M3_order_constrained_piecewise` 的连续 `R` 输出，专门做三分类切分，不再拟合新的连续 `R`。

比较的方法：

- `P0_fixed_cutoffs`
  - 固定使用 `0.9 / 0.7`
- `P1_anchor_mean_midpoint`
  - 用锚点均值的中点定义两个切点
- `P2_anchor_median_midpoint`
  - 用锚点中位数的中点定义两个切点

## 2. 主要结果

### 2.1 Stokes-Poiseuille：分区专用迁移几乎没有额外收益

对非 baseline 变体平均：

- `P0`
  - run accuracy: `0.833`
  - macro F1: `0.821`
- `P1`
  - run accuracy: `0.833`
  - macro F1: `0.821`
- `P2`
  - run accuracy: `0.833`
  - macro F1: `0.821`

也就是说，`Stokes-Poiseuille` 上这三种分区切点几乎等价。

更细看点级预测：

- `capacity_v1` 已经全部预测正确
- `weight_balanced_v2` 中，`critical_obs8_noise0125` 仍然被预测成 `reliable`

所以这里的问题不是切点形式，而是：

- 当前 `M3` 迁移后的 `R` 本身仍把临界点推得过高

### 2.2 Burgers：P1/P2 只有轻微 run 级改进，点级语义仍未修好

对非 baseline 变体平均：

- `P0`
  - run accuracy: `0.417`
  - macro F1: `0.398`
  - 分区分歧: `0.75`
- `P1`
  - run accuracy: `0.500`
  - macro F1: `0.522`
  - 分区分歧: `0.75`
- `P2`
  - run accuracy: `0.458`
  - macro F1: `0.479`
  - 分区分歧: `0.75`

因此：

- `P1` 比固定切点略好
- `P2` 没有进一步提升
- 但三种方法在点级跨变体分歧上没有本质区别

更关键的是点级预测仍然有系统性错误：

`capacity_v1`
- `safe_obs64_noise005` 仍被分到 `critical`
- `transition_obs48_noise010` 仍被分到 `reliable`
- `seed_sensitive_obs32_noise010` 仍被分到 `reliable`

`weight_balanced_v2`
- `safe_obs64_noise005` 仍被分到 `critical`
- `transition_obs48_noise010` 仍被分到 `reliable`
- `seed_sensitive_obs32_noise010` 仍被分到 `unreliable`

这说明：

- 当前问题不是简单的“切点取错了”
- 而是 `Burgers` 上 `M3` 迁移后的连续 `R` 分布，本身就没有形成稳定的三段结构

## 3. 对当前主问题的影响

这轮结果回答得比较明确：

1. 单独给 `R` 重新找两个切点，不能从根本上解决 `Burgers` 的分区迁移问题。
2. 当前 `Burgers` 上的问题不在于固定 `0.9 / 0.7` 太僵硬，而在于：
   - 连续 `R` 的语义分布本身已经发生变形
3. 因此，`R` 分区专用迁移的“最小切点校准”路线，目前只能算有限改进，不足以闭环。

## 4. 当前最稳的判断

到现在为止：

- `M3_order_constrained_piecewise`
  - 是当前连续迁移层面最好的方案
  - 它修复了 `Burgers` 的排序问题
- `P1/P2`
  - 在 `Burgers` 上只能轻微提升 run 级分类
  - 但没有真正恢复点级三分类语义

所以当前最准确的结论是：

`复杂多维边界案例中，问题的关键不只是分区切点，而是连续可靠性表示本身的类间可分性不足。`

## 5. 下一步建议

如果继续解决当前实验中发现的问题，最值得做的是：

1. 设计“局部边界专用分类器”
   - 不再试图一次性恢复三分类
   - 先单独解决：
     - `critical vs unreliable`
     - `reliable vs non-reliable`

2. 或者直接承认：
   - `R` 在复杂案例中更适合作为排序量
   - 三段分区只能作为近似展示，而不是严格迁移目标

基于当前结果，我更倾向于第二条作为论文主文口径，第一条作为后续方法增强方向。

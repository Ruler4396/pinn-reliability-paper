# R 分区专用迁移方案

本文档提出一个新的迁移方向：

`不再把 R 当成需要连续回归的标量，而是把 reliable / critical / unreliable 三段语义作为一等目标直接迁移。`

这个方案是对当前 few-shot transfer calibration 结果的回应。现有结论已经表明：

- `M3_order_constrained_piecewise` 能在 `Burgers` 中保住排序
- 但 `R` 分区精度仍然偏弱
- 简单用 `rel_l2` 去保守裁剪 `R` 的 `M4` 没有继续改善

因此，下一步不应再把 `R` 迁移视为“把一个连续值拟合回 baseline”，而应直接做：

`语义分区迁移`

## 1. 目标

给定一个新 PINN 变体和极少数锚点，我们希望恢复的是：

1. 哪些点属于 `reliable`
2. 哪些点属于 `critical`
3. 哪些点属于 `unreliable`

而不是强行恢复一个精确的连续 `R` 数值。

## 2. 为什么要单独做分区迁移

连续 `R` 拟合在复杂案例上有两个问题：

1. `R` 的数值大小会随变体漂移
2. 即使排序恢复了，切分边界仍可能失真

在 `Burgers` 上，当前已经看到：

- 排序保持约束可以修复顺序
- 但 `R` 的类间边界仍然对不齐

所以更合理的做法是：

- 保留 `R` 的排序信息
- 单独学习或校准“从排序到分区”的映射

## 3. 方案核心

### 3.1 两层结构

将迁移拆成两层：

1. **排序层**
   - 继续使用 `M3_order_constrained_piecewise`
   - 作用：恢复可靠性顺序

2. **分区层**
   - 不再直接用固定 `0.9 / 0.7`
   - 而是用少量锚点重新定位：
     - `reliable / critical` 切点
     - `critical / unreliable` 切点

### 3.2 基本思想

对每个 `case × variant`，在 `M3` 的迁移输出上定义两个新切点：

- `tau_high`
- `tau_low`

满足：

- `R_transfer >= tau_high` -> `reliable`
- `tau_low <= R_transfer < tau_high` -> `critical`
- `R_transfer < tau_low` -> `unreliable`

其中 `tau_high` 和 `tau_low` 不再固定写死，而由少量锚点决定。

## 4. 候选方法

建议至少比较三种方法。

### P0. 固定切点基线

直接使用：

- `tau_high = 0.9`
- `tau_low = 0.7`

作用：
- 作为当前方法基线

### P1. 锚点中点切分

选取三类锚点：

- `reliable` 锚点
- `critical` 锚点
- `unreliable` 锚点

令：

- `tau_high = (R_reliable_anchor + R_critical_anchor) / 2`
- `tau_low = (R_critical_anchor + R_unreliable_anchor) / 2`

优点：
- 最简单
- 直接针对三段语义

风险：
- 对单个锚点波动较敏感

### P2. 排序约束下的分位切分

不直接用单个锚点，而用锚点邻域的统计量来定切点，例如：

- `tau_high = weighted midpoint` of reliable/critical cluster
- `tau_low = weighted midpoint` of critical/unreliable cluster

如果当前只有点级代表点，可先用：

- 锚点多 seed 均值
- 并对高方差锚点做保守修正

优点：
- 对 seed 波动更稳

### P3. 仅边界局部分类

不把任务写成“三分类”，而写成两个局部判别：

1. 是否进入 `unreliable`
2. 在非 `unreliable` 中，是否属于 `reliable`

也就是：

- 先校准 `tau_low`
- 再校准 `tau_high`

这个方法适合 `Burgers`，因为它的主要问题往往是：

- `critical` 和 `unreliable` 混淆

## 5. 锚点设计

### 5.1 Stokes-Poiseuille

可直接使用：

- `safe_obs64_noise000` -> `reliable`
- `critical_obs8_noise0125` -> `critical`
- `failure_obs8_noise0175` -> `unreliable`

### 5.2 Burgers

建议不要把 `seed_sensitive_obs32_noise010` 直接当作主锚点，因为它本身高方差。

推荐：

- `safe_obs64_noise005` -> `reliable`
- `transition_obs48_noise010` -> `critical`
- `failure_obs32_noise0175` -> `unreliable`

然后把：

- `seed_sensitive_obs32_noise010`

完全留作评估点。

## 6. 评价指标

这轮评价不再重点看连续 `R` 数值误差，而看语义恢复。

### 6.1 分类准确率

- `R_partition_accuracy`
- `macro_f1` for `reliable / critical / unreliable`

### 6.2 边界恢复

- `critical/unreliable` 边界是否比当前更准
- `reliable/critical` 边界是否保持稳定

### 6.3 与排序的一致性

分区方案不能破坏 `M3` 已经修复的排序。需要检查：

- 分区切点调整后，`severity -> -R_transfer` 的 Spearman 不下降

### 6.4 跨变体分歧

看各代表点在不同变体下的：

- `R_majority_label` 分歧是否下降

## 7. 成功判据

一个 `R` 分区专用迁移方案要进入主文，至少满足：

1. 在 `Burgers` 上，`R` 标签准确率高于当前 `M3` 的 `0.50`
2. 不低于当前 `M3` 的排序相关性
3. 不能通过把大量点都压成 `critical` 来“伪提升”

建议更具体地要求：

- `Burgers` 平均 `R` 标签准确率达到 `>= 0.625`
- `severity rho with -R` 维持在 `>= 0.60`
- `R` 跨变体分歧相比 `M3` 再下降至少 `25%`

## 8. 实现建议

新增分析脚本：

- `minimal_pinn/analyze_r_partition_transfer.py`

输入：

- `few_shot_transfer_calibration_v1/transfer_run_predictions.csv`
- 或直接复用 `variant_robustness_v1/point_runs.csv` 和 `M3` 映射

输出目录建议：

- `minimal_pinn/results/analysis/r_partition_transfer_v1`

建议输出文件：

- `r_partition_transfer_summary.csv`
- `r_partition_transfer_summary.json`
- `per_case_variant_cutpoints.csv`
- `figure_28_r_partition_accuracy.png`
- `figure_29_r_partition_disagreement.png`

对应说明文档：

- `notes/r_partition_transfer_results.md`

## 9. 推荐执行顺序

先做最小版本：

1. 基于 `M3` 输出实现 `P1` 和 `P2`
2. 先只做 `Burgers` 和 `Stokes-Poiseuille`
3. 比较：
   - 固定切点 `P0`
   - 锚点中点切分 `P1`
   - 稳健中点/分位切分 `P2`

如果 `P1/P2` 在 `Burgers` 上有改进，再考虑：

4. 做 `P3` 两阶段局部分区

## 10. 当前预期

最可能的结果是：

- `Stokes-Poiseuille` 上几乎所有分区方法都会比较稳
- `Burgers` 上只有“排序恢复 + 分区专用切点”这条路线可能继续提升

因此，这个方案的价值在于：

`把 R 从“一个不好迁移的连续数值”改造成“先排序、再分区”的两步语义系统。`

# Recalibrated Dimension Results

## 方法

本轮不改训练流程，只对现有矩阵结果做后处理重标定。

- 输入数据：
  - `Poisson`: `coarse_v1`
  - `Burgers`: `refine_burgers_v1`
  - `Stokes-Poiseuille`: `refine_stokes_v1`
- 标量指标：
  - `physics_rms`
  - `boundary_rms`
  - `rel_l2`
  - `structure_error`
  - `loss_std`
  - `loss_ratio`
- 阈值策略：
  - 对每个案例、每个标量指标，取该案例分布的 `15%` 分位作为 `good`
  - 取 `85%` 分位作为 `fail`
  - 再用现有 logistic 映射重算 indicator score 与 dimension score

这个步骤的目的不是给出最终工程阈值，而是检查当前多维框架是否能在合理的归一化区间下真正拉开四个维度。

## 输出

- Summary:
  - `minimal_pinn/results/analysis/recalibrated_dimensions_v1/recalibrated_summary.json`
- Tables:
  - `minimal_pinn/results/analysis/recalibrated_dimensions_v1/poisson_recalibrated_table.csv`
  - `minimal_pinn/results/analysis/recalibrated_dimensions_v1/burgers_recalibrated_table.csv`
  - `minimal_pinn/results/analysis/recalibrated_dimensions_v1/stokes_poiseuille_recalibrated_table.csv`
- Figures:
  - `minimal_pinn/results/analysis/recalibrated_dimensions_v1/figure_08_recalibrated_dimension_spreads.png`
  - `minimal_pinn/results/analysis/recalibrated_dimensions_v1/figure_09_recalibrated_failure_mode_counts.png`

## 结果摘要

### Poisson

- 旧结果中几乎完全由 `physics_consistency` 主导
- 重标定后，高误差区的主导维度分布变为：
  - `numerical_accuracy`: 5
  - `structural_stability`: 2
  - `training_stability`: 1
  - `physics_consistency`: 0

解释：

- `Poisson` 本来就没有实用边界，因此这类分配更多说明“轻微退化主要体现在哪些维度”，而不是说明出现了明确失效机制

### Burgers

- 这是本轮最重要的结果
- 旧结果中高误差区几乎全部被 `physics_consistency` 吃掉
- 重标定后，`59` 个越界点的主导维度分布变为：
  - `training_stability`: 23
  - `structural_stability`: 15
  - `numerical_accuracy`: 12
  - `physics_consistency`: 9

解释：

- `Burgers` 的边界区确实不是单一物理残差主导
- 训练稳定性和结构稳定性在边界带中起到实质作用
- 这与前面的多 seed 异常格点复现是相互支持的

### Stokes-Poiseuille

- 重标定后，`8` 个越界点的主导维度分布变为：
  - `numerical_accuracy`: 7
  - `physics_consistency`: 1
  - `training_stability`: 0
  - `structural_stability`: 0

解释：

- `Stokes-Poiseuille` 的边界更窄、更规整
- 在当前简化 benchmark 下，它更像一个“误差主导的规则边界”，而不是像 `Burgers` 那样呈现复杂的多维失效结构

## 结论

这轮重标定之后，可以更有把握地说：

1. 旧的默认阈值确实压扁了训练稳定性和结构稳定性
2. 在合理的案例内重标定后，`Burgers` 显示出明显的多维边界结构
3. `Stokes-Poiseuille` 仍主要表现为较规则的数值误差边界
4. 三案例在维度主导模式上存在明确差异

因此，项目现在已经可以从“边界存在”推进到“不同系统中哪些维度主导边界形成”这一层。

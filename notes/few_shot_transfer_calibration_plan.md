# 少样本迁移校准实验方案

本文档将“少样本迁移校准”具体化为可执行实验，用于解决当前最关键的方法学问题：

`固定绝对边界阈值不能跨 PINN 变体直接复用；需要一种只依赖少量校准点的迁移机制，使新变体上的可靠性语义重新对齐。`

## 1. 目标

本实验不再追求构造“完全通用、零校准”的硬阈值，而是回答更现实的问题：

1. 给定一个新 PINN 变体，是否能只用极少数参考点完成阈值迁移？
2. 迁移后，`rel_l2` 边界判定和 `R` 分区语义是否比“直接复用旧阈值”更稳定？
3. 少样本迁移后，`R` 是否能更稳地恢复案例内的严重度排序与边界带解释？

## 2. 核心思路

### 2.1 迁移对象

当前需要迁移的不是原始指标本身，而是两类“语义层”对象：

1. `rel_l2` 边界阈值
2. 综合可靠性 `R` 的分区切点

### 2.2 迁移假设

我们不假设不同变体共享同一绝对边界值；只假设：

- 在同一个 PDE 案例内，不同变体之间存在可被少量锚点校正的“单调映射”
- 这种映射足以恢复“安全 / 临界 / 失效”的相对语义

### 2.3 最小校准原则

迁移校准必须满足：

1. 不新增大规模矩阵训练
2. 只使用现有变体稳健性实验中的少量代表点
3. 校准点数量固定且很小，避免把问题变成重新拟合整张相图

## 3. 实验对象

### 3.1 案例

优先只做：

- `Stokes-Poiseuille`
- `Burgers`

`Poisson` 可作为附带对照，但不作为核心评价对象，因为其边界本就不明显。

### 3.2 变体

基于现有三种变体：

- `baseline`
- `capacity_v1`
- `weight_balanced_v2`

### 3.3 代表点

直接复用当前跨变体稳健性实验中的代表点：

`Stokes-Poiseuille`
- `safe_obs64_noise000`
- `critical_obs8_noise0125`
- `failure_obs8_noise0175`

`Burgers`
- `safe_obs64_noise005`
- `transition_obs48_noise010`
- `seed_sensitive_obs32_noise010`
- `failure_obs32_noise0175`

## 4. 校准方案

本轮至少比较三种迁移方法。

### M0. 无迁移基线

直接复用 baseline 变体上已有的：

- 绝对 `rel_l2` 阈值
- 固定 `R=0.9/0.7` 分区

作用：
- 作为当前方法的零校准基线

### M1. 双锚点线性迁移

对每个 `case × variant`，只使用两个锚点：

- 一个安全点
- 一个失效点

推荐：

`Stokes-Poiseuille`
- safe: `safe_obs64_noise000`
- fail: `failure_obs8_noise0175`

`Burgers`
- safe: `safe_obs64_noise005`
- fail: `failure_obs32_noise0175`

对 `rel_l2` 和 `R` 分别建立线性映射：

`z_target = a * z_variant + b`

其中：
- `z_variant` 为新变体上的观测值
- `z_target` 为 baseline 语义空间中的对应值

校准后：
- 用映射后的 `rel_l2` 再套 baseline 阈值
- 用映射后的 `R` 再套 baseline 分区切点

优点：
- 实现简单
- 只需两个锚点

风险：
- 只能吸收平移和缩放
- 对非线性扭曲不够强

### M2. 三锚点分段线性迁移

对每个 `case × variant`，使用三类锚点：

- safe
- critical/transition
- fail

推荐：

`Stokes-Poiseuille`
- safe: `safe_obs64_noise000`
- critical: `critical_obs8_noise0125`
- fail: `failure_obs8_noise0175`

`Burgers`
- safe: `safe_obs64_noise005`
- transition: `transition_obs48_noise010`
- fail: `failure_obs32_noise0175`

对 `rel_l2` 与 `R` 分别建立一维分段线性映射。

优点：
- 能吸收“安全段”和“失效段”不同斜率
- 对当前边界附近的校准更合理

风险：
- 需要第三个锚点
- 对锚点定义较敏感

### M3. 仅排序迁移

不做数值映射，只做变体内排序归一化。例如：

- 在该变体的少样本锚点上估计分位位置
- 把 `R` 或 `rel_l2` 映射到相对风险百分位

作用：
- 验证是否应该放弃“绝对阈值”，转向“相对风险排序”

它更像备用方案。如果 `M1/M2` 都失败，这个方向可能成为论文最终收口方式。

## 5. 数据拆分

为了避免自证循环，必须区分：

### 5.1 校准集

每个 `case × variant` 只允许使用少量锚点：

- `M1`：2 个标签点
- `M2`：3 个标签点

### 5.2 评估集

其余代表点全部作为评估集。

例如：

`Burgers`
- 若 `M2` 使用 `safe + transition + failure`
- 则 `seed_sensitive_obs32_noise010` 必须只用于评估

`Stokes-Poiseuille`
- 若 `M2` 使用三点全占满，则需在 seed 维度上评估：
  - 校准只用锚点均值
  - 评估看各 seed 的标签一致性恢复程度

## 6. 评价指标

### 6.1 阈值语义恢复

对 `rel_l2` 迁移后的判定，比较：

1. 与 baseline 语义标签的一致率
2. 各代表点在跨变体下的 majority label 分歧是否下降

建议指标：

- `label_agreement_to_baseline`
- `mean_cross_variant_disagreement_span`

### 6.2 `R` 分区语义恢复

对校准后的 `R` 分区，比较：

1. `reliable / critical / unreliable` 主类别是否更接近 baseline
2. `R` 的严重度排序相关性是否提高

建议指标：

- `R_majority_match_to_baseline`
- `Spearman(severity, -R_calibrated)`

### 6.3 边界排序保真

比较校准前后：

- safe 点是否仍最低风险
- failure 点是否仍最高风险
- critical/transition/seed-sensitive 点是否位于中间

建议指标：

- pairwise ordering accuracy

## 7. 成功判据

一个迁移方案若要进入论文主文，至少应满足：

1. 在 `Stokes-Poiseuille` 和 `Burgers` 上，跨变体 label 分歧明显下降
2. 相比 `M0`，`R` 的严重度排序相关性不下降，最好提升
3. 不能靠把所有点都压成同一类别来“伪提升”

更具体地：

- `mean_cross_variant_disagreement_span` 相比 `M0` 至少下降 `25%`
- `R_majority_match_to_baseline` 不低于 `M0`
- `Burgers` 上 `seed_sensitive` 和 `failure` 两类点不能被错误合并成同一语义层

## 8. 输出文件设计

建议新增结果目录：

- `minimal_pinn/results/analysis/few_shot_transfer_calibration_v1`

建议输出：

- `transfer_calibration_summary.csv`
- `transfer_calibration_summary.json`
- `per_case_variant_mapping.csv`
- `figure_25_transfer_label_agreement.png`
- `figure_26_transfer_disagreement_reduction.png`
- `figure_27_transfer_ordering_rho.png`

建议新增说明文档：

- `notes/few_shot_transfer_calibration_results.md`

## 9. 实现步骤

### Step 1. 整理基线语义标签

基于当前 `variant_robustness_v1/point_runs.csv`：

- 对 baseline 变体生成每个代表点的基准语义标签
- 标签可并行记录两套：
  - `rel_l2` 边界标签
  - `R` 分区标签

### Step 2. 为每个 `case × variant` 提取锚点

从现有代表点中选出 `M1` 和 `M2` 所需锚点，并计算：

- anchor mean
- anchor std

### Step 3. 拟合迁移映射

分别对 `rel_l2` 与 `R` 拟合：

- `M1`：双锚点线性映射
- `M2`：三锚点分段线性映射

### Step 4. 在评估集上打分

对非锚点评估：

- 标签一致率
- majority label 分歧
- 排序相关性

### Step 5. 与 `M0` 比较

形成三方案对照表：

- `M0` 无迁移
- `M1` 双锚点线性迁移
- `M2` 三锚点分段迁移

## 10. 预计计算成本

这组实验应当几乎不新增训练成本。

因为它只依赖：

- `variant_robustness_v1`
- 已有代表点多 seed 结果

预计耗时：

- 脚本实现：30 到 60 分钟
- 分析运行：1 到 3 分钟
- 结果整理与文档：20 到 30 分钟

## 11. 可能结果及对应处理

### 情形 A：`M1/M2` 明显优于 `M0`

含义：
- 少样本迁移校准成立
- 论文可以增加一个新的方法层贡献：
  - `few-shot transfer calibration`

### 情形 B：`M2` 有效，`M1` 无效

含义：
- 迁移需要临界锚点
- 说明边界扭曲不是简单平移/缩放，而是边界附近的局部几何变化

### 情形 C：`M1/M2` 都不明显优于 `M0`

含义：
- 绝对阈值语义确实难迁移
- 论文应进一步收口到：
  - `R` 主要用于排序与失效结构解释
  - 不再强调跨变体阈值对齐

## 12. 推荐优先执行版本

建议先做 `v1` 最小版本：

1. 只做 `Stokes-Poiseuille` 和 `Burgers`
2. 先比较 `M0`、`M1`、`M2`
3. 暂不做 `Poisson`
4. 暂不做更复杂非线性映射

如果 `v1` 有信号，再扩到：

- `Poisson` 对照
- 排序迁移 `M3`
- 新变体或新案例

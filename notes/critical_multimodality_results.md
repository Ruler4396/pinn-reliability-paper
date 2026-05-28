# Burgers 临界带多模态诊断结果

本轮分析对应：

- `minimal_pinn/analyze_critical_multimodality.py`
- `minimal_pinn/results/analysis/critical_multimodality_v1`

输入只使用现有 `M3_order_constrained_piecewise` 的 run-level 输出，不新增训练。

## 目标

验证 `Burgers` 的 `critical` 是否可以继续被当成单一连续类处理，还是应拆成不同子机制。

内部子类定义为：

- `critical_transition`
  - `transition_obs48_noise010`
- `critical_instability`
  - `seed_sensitive_obs32_noise010`

## 核心结果

### 1. 两个 critical 子类在均值上显著分离

汇总所有变体后：

- `critical_transition`
  - `transferred_R ≈ 0.845`
  - `transferred_rel_l2 ≈ 0.0305`
  - `structural_stability ≈ 0.918`
  - `training_stability ≈ 0.765`
- `critical_instability`
  - `transferred_R ≈ 0.599`
  - `transferred_rel_l2 ≈ 0.0772`
  - `structural_stability ≈ 0.746`
  - `training_stability ≈ 0.655`

这说明两者不是“同一团点的轻微波动”，而是已经在可靠性与结构特征上分开。

### 2. 单一切点不能把两者同时解释成同一类

在 pooled 数据上，对 `critical_transition` 与 `critical_instability` 做最佳单阈值划分：

- `structural_stability_recal` 的最佳准确率约 `0.889`
- `transferred_rel_l2` 约 `0.778`
- `transferred_R` 约 `0.722`
- `training_stability_recal` 仅约 `0.611`

这说明：

- 某些单特征可以分开这两个子类
- 但不存在一个简单、统一的“critical 切点”能同时恢复全部语义
- 尤其 `training_stability` 上，两类高度重叠

因此问题不在于“全局三分类切点调得还不够好”，而在于 `critical` 本身是混合类。

### 3. 两个子类与安全区/失效区的邻接关系不同

基于四维 z-score 特征空间的质心距离：

- `critical_transition`
  - pooled 下始终更接近 `reliable`
  - 各变体下也都更接近 `reliable`
- `critical_instability`
  - pooled 下整体仍略偏向 `reliable`
  - 但在 `baseline` 与 `weight_balanced_v2` 中更接近 `unreliable`
  - 仅在 `capacity_v1` 中更接近 `reliable`

这说明：

- `critical_transition` 更像安全边界附近的过渡带
- `critical_instability` 更像失效边界附近的高风险带
- 把它们压成一个统一 `critical` 类，会混淆“靠近安全边界的临界点”和“靠近失效边界的临界点”

## 结论

`Burgers` 的 `critical` 不应再被当成单一连续类处理。

更合理的内部语义是：

- `critical_transition`
- `critical_instability`

对外写论文时仍可合并显示为 `critical band`，但方法和评估内部必须承认其多模态性质。

因此后续方法结构应改为：

- `Stokes-Poiseuille`
  - 保留全局三段硬分区
- `Burgers`
  - 以 `M3` 排序为主
  - 用局部边界任务解释安全边界与失效边界
  - 不再把全局三分类准确率当成主目标

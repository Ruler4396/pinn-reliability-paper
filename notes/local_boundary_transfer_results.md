# 局部边界迁移评估结果

本轮分析对应：

- `minimal_pinn/analyze_local_boundary_transfer.py`
- `minimal_pinn/results/analysis/local_boundary_transfer_v1`

目标不是继续优化 `Burgers` 的全局三分类，而是改为评估两个局部边界任务：

- `safe_boundary`
  - `reliable` vs `non-reliable`
- `failure_boundary`
  - `unreliable` vs `non-unreliable`

同时保留 `Stokes-Poiseuille` 作为规则边界参考。

## 方法

参考方法：

- `REF_P1_global_partition`
  - 直接复用当前最好的一版全局三分类切分结果

局部边界方法：

- `L0_rel2_midpoint`
  - 用边界相邻两类的 baseline `transferred_rel_l2` 中点做阈值
- `L1_pair_prototype_2d`
  - 用边界相邻两类在 `transferred_rel_l2 + transferred_R` 上做双原型判别
- `L2_pair_prototype_3d`
  - 在 `L1` 基础上再加入 `structural_stability_recal`

对于 `Burgers`：

- `safe_boundary` 用 `safe ↔ transition` 做局部校准
- `failure_boundary` 用 `seed_sensitive ↔ failure` 做局部校准

## 核心结果

### 1. Stokes-Poiseuille 仍然符合“规则边界 + 硬分区”

在 transfer 变体平均后：

- `safe_boundary`
  - `REF_P1`、`L0`、`L1`、`L2` 都约为 `0.944` accuracy
  - disagreement 均为 `0`
- `failure_boundary`
  - `REF_P1` 与 `L1_pair_prototype_2d` 都约为 `0.889` accuracy
  - disagreement 均为 `0`

说明：

- `Stokes` 不需要改成复杂的多模态解释
- `M3 + 三段硬分区` 仍可用

### 2. Burgers 的安全边界更适合用局部边界任务表达

在 transfer 变体平均后，`safe_boundary`：

- `REF_P1_global_partition`
  - accuracy `0.583`
  - F1 `0.292`
  - disagreement `0.750`
- `L0_rel2_midpoint`
  - accuracy `0.750`
  - F1 `0.571`
  - disagreement `0.250`

这说明：

- 全局三分类在 `Burgers` 的安全边界上语义非常不稳
- 把任务改成“安全 vs 非安全”后，可解释性明显提升
- 而且这里最有效的不是更复杂的高维原型，而是简单的局部 `rel_l2` 中点阈值

### 3. Burgers 的失效边界已经基本被排序捕获，但更适合作为局部边界解释

在 transfer 变体平均后，`failure_boundary`：

- `REF_P1_global_partition`
  - accuracy `0.917`
  - F1 `0.875`
  - disagreement `0.250`
- `L1_pair_prototype_2d`
  - accuracy `0.833`
  - F1 `0.686`
  - disagreement `0.250`

这里全局分区数值上仍略优，但 `L1` 结果表明：

- 用 `seed_sensitive ↔ failure` 的局部原型对来解释失效边界是可行的
- 失效边界本身并不是当前 `Burgers` 的主要瓶颈
- 真正被全局三分类破坏的是安全边界附近的语义

## 结论

这轮结果支持以下重构：

1. `Stokes-Poiseuille`
   - 保留全局三段硬分区
   - 不需要改动主叙事
2. `Burgers`
   - 不再以全局三分类准确率作为主指标
   - 主结果改为：
     - `M3` 下的严重度排序
     - `safe_boundary` 局部边界识别
     - `failure_boundary` 局部边界识别
     - `critical` 多模态诊断

换句话说，`Burgers` 的主要问题不是“再找一个更好的全局切点”，而是：

`critical band` 本身不是单团结构，因此必须用“排序 + 局部边界”来描述，而不是用统一三分类硬压。 

# P4：区域感知训练 v2 结果

## 实验设置

- 对比工况：
  - `Burgers`: `N_obs=32`, `sigma=0.10`
  - `Stokes-Poiseuille`: `N_obs=8`, `sigma=0.125`
- 随机种子：`41, 42, 43`
- 策略：
  - `baseline`
  - `naive_region_aware_v1`
  - `dim_guided_v2`

结果目录：
- `/root/dev/pinn-reliability-paper/minimal_pinn/results/region_aware/region_aware_compare_v2`

## 策略定义

`naive_region_aware_v1` 延续第一轮思路，同时对 observation 和 collocation 做强偏置采样。

`dim_guided_v2` 只保留轻量 collocation 偏置，不再偏置 observation：
- `Burgers`：只在早期时间和中心区域增加 `30%` collocation 采样
- `Stokes-Poiseuille`：只在上下壁面窄带增加 `30%` collocation 采样

## 核心结果

### Burgers

相对 `baseline`，`dim_guided_v2` 的结果为：

- `rel_l2`: `0.0567 -> 0.0499`
- `reliability_raw_recal`: `0.5253 -> 0.6555`
- `physics_consistency`: `0.5179 -> 0.5430`
- `training_stability`: `0.3798 -> 0.7898`
- `numerical_accuracy`: `0.6086 -> 0.6764`
- `structural_stability`: `0.5948 -> 0.6126`

相比之下，`naive_region_aware_v1` 虽然把 `rel_l2` 压到 `0.0456`，但综合可靠性反而降到 `0.4822`，并明显破坏物理一致性与训练稳定性。

因此，`Burgers` 上已经出现一个可写的正结果：按主导失效维度收窄干预后，能够在保持误差下降的同时提升综合可靠性。

### Stokes-Poiseuille

相对 `baseline`，`dim_guided_v2` 的结果为：

- `rel_l2`: `0.0389 -> 0.0395`
- `reliability_raw_recal`: `0.7933 -> 0.7691`
- `physics_consistency`: `0.8581 -> 0.8876`
- `training_stability`: `0.8768 -> 0.8718`
- `numerical_accuracy`: `0.5057 -> 0.4781`
- `structural_stability`: `0.9326 -> 0.8390`

这说明 `Stokes-Poiseuille` 上的轻量壁面 collocation 偏置没有带来净收益。它提升了物理一致性，但损失了数值精度和结构稳定性，最终综合可靠性仍低于 baseline。

## 结论

`P4` 支持一个更严格、也更有价值的结论：

1. 朴素的重点区域采样不是可靠的通用增强策略。
2. 基于主导失效维度设计的干预在 `Burgers` 上可以产生正向结果。
3. 区域感知训练的有效性具有明显系统依赖性，当前不能把 `Burgers` 的结果外推到 `Stokes-Poiseuille`。

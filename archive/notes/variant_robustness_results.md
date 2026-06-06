# 跨 PINN 变体稳健性实验结果

结果目录：
- `/root/dev/pinn-reliability-paper/minimal_pinn/results/variant_robustness/variant_robustness_v1`
- `/root/dev/pinn-reliability-paper/minimal_pinn/results/variant_robustness/variant_robustness_v2`
- `/root/dev/pinn-reliability-paper/minimal_pinn/results/variant_robustness/variant_robustness_v3`

核心文件：
- `point_summary.csv`
- `strategy_summary.csv`
- `robustness_summary.json`

本轮变体：

1. `baseline`
2. `capacity_v1`：`96 x 96 x 96`
3. `weight_balanced_v2`：`data=5, physics=2, boundary=15`
4. `adaptive_rar_v1`：固定 collocation budget 下的经典 residual-adaptive resampling，具体为周期性候选点残差排序后替换 `25%` collocation 点
5. `loss_adaptive_uncertainty_v1`：可学习 `log-variance` 的 loss-adaptive weighting，属于 SA-PINNs / uncertainty weighting 风格的标准自适应权重基线

## 1. 角色分工是否稳定

### 1.1 Poisson

`Poisson` 的两个代表点在三种变体下都没有越过当前 `rel_l2` 边界阈值。

- `safe_obs256_noise000`
  - baseline: `rel_l2 = 0.1140`, `cross_rate = 0`
  - capacity_v1: `rel_l2 = 0.1076`, `cross_rate = 0`
  - weight_balanced_v2: `rel_l2 = 0.1250`, `cross_rate = 0`

- `degraded_obs8_noise020`
  - baseline: `rel_l2 = 0.1245`, `cross_rate = 0`
  - capacity_v1: `rel_l2 = 0.1189`, `cross_rate = 0`
  - weight_balanced_v2: `rel_l2 = 0.1295`, `cross_rate = 0`

结论：

`Poisson` 作为稳健对照组的角色在变体下保持稳定。

### 1.2 Stokes-Poiseuille

`Stokes-Poiseuille` 的安全点在所有变体下都保持安全。更关键的是，临界点和失效点的结果表明：

- `critical_obs8_noise0125`
  - baseline: `cross_rate = 0.667`
  - capacity_v1: `cross_rate = 0`
  - weight_balanced_v2: `cross_rate = 0`

- `failure_obs8_noise0175`
  - baseline: `cross_rate = 1.0`
  - capacity_v1: `cross_rate = 1.0`
  - weight_balanced_v2: `cross_rate = 0.333`

结论：

1. 变体会平移 `Stokes-Poiseuille` 的绝对边界位置。
2. 但其总体形态仍然是“窄而规则”的边界，而没有演化成 `Burgers` 那种宽概率边界。

### 1.3 Burgers

`Burgers` 的结果最有信息量。

- `safe_obs64_noise005`
  - baseline: `cross_rate = 0.333`
  - capacity_v1: `cross_rate = 0.667`
  - weight_balanced_v2: `cross_rate = 0.333`

- `transition_obs48_noise010`
  - baseline: `cross_rate = 0.667`
  - capacity_v1: `cross_rate = 1.0`
  - weight_balanced_v2: `cross_rate = 0`

- `seed_sensitive_obs32_noise010`
  - baseline: `cross_rate = 1.0`
  - capacity_v1: `cross_rate = 1.0`
  - weight_balanced_v2: `cross_rate = 1.0`

- `failure_obs32_noise0175`
  - baseline: `cross_rate = 1.0`
  - capacity_v1: `cross_rate = 1.0`
  - weight_balanced_v2: `cross_rate = 1.0`

结论：

1. `Burgers` 的绝对边界位置对变体更敏感。
2. 但最关键的“种子敏感点”和“失效点”没有消失。
3. 因此，`Burgers` 的困难区域并不是单个实现的偶然产物。

### 1.4 adaptive_rar_v1 的补充信息

`adaptive_rar_v1` 并没有表现为“统一更强”的 baseline，而是一个明显的 case-dependent adaptive baseline。

- `Poisson`
  - `safe_obs256_noise000` 与 `degraded_obs8_noise020` 仍然 `cross_rate = 0`
  - 但综合可靠性下降明显，主要来自训练稳定性维度被周期性重采样扰动

- `Stokes-Poiseuille`
  - `safe_obs64_noise000`: `cross_rate = 0`
  - `critical_obs8_noise0125`: `cross_rate = 0.333`
  - `failure_obs8_noise0175`: `cross_rate = 1.0`

- `Fisher-KPP`
  - `safe_obs64_noise000`: `cross_rate = 0`
  - `edge_obs16_noise005`: `cross_rate = 0.667`
  - `transition_obs128_noise020`: `cross_rate = 0.667`
  - `failure_obs16_noise030`: `cross_rate = 1.0`

- `Burgers`
  - `transition_obs48_noise010`: `cross_rate = 0.667`
  - `seed_sensitive_obs32_noise010`: `cross_rate = 1.0`
  - `failure_obs32_noise0175`: `cross_rate = 1.0`
  - `safe_obs64_noise005` 反而上升到 `cross_rate = 1.0`

这一组结果有两个含义：

1. 经典自适应采样本身也会显著移动边界位置，因此不能把当前结论写成“对任意 adaptive PINN 都完全不变”。
2. 但 `Burgers` 的宽高风险带并没有被 `RAR` 消除；相反，`RAR` 甚至会把 nominally safe 的点推向越界侧。这说明本文识别到的系统差异并不只是“最小 vanilla PINN 太弱”的单向偏差。

### 1.5 loss_adaptive_uncertainty_v1 的补充信息

这一基线比 `RAR` 更标准，也更接近 reviewer 会自然想到的“loss-adaptive PINN”。

- `Poisson`
  - `safe_obs256_noise000`: `cross_rate = 0`
  - `degraded_obs8_noise020`: `cross_rate = 0.333`
  - 说明它不是无条件增强，甚至会把原本稳健对照中的退化点推向操作性边界

- `Stokes-Poiseuille`
  - `safe_obs64_noise000`: `cross_rate = 0`
  - `critical_obs8_noise0125`: `cross_rate = 0`
  - `failure_obs8_noise0175`: `cross_rate = 0.667`
  - 相比 baseline，说明 loss-adaptive weighting 可以后移规则边界，但不能消除失效侧

- `Fisher-KPP`
  - `safe_obs64_noise000`: `cross_rate = 0`
  - `edge_obs16_noise005`: `cross_rate = 0.333`
  - `transition_obs128_noise020`: `cross_rate = 0`
  - `failure_obs16_noise030`: `cross_rate = 1.0`
  - 说明这一基线对传播型规则边界带更有效，能明显压缩过渡带

- `Burgers`
  - `safe_obs64_noise005`: `cross_rate = 0.667`
  - `transition_obs48_noise010`: `cross_rate = 1.0`
  - `seed_sensitive_obs32_noise010`: `cross_rate = 1.0`
  - `failure_obs32_noise0175`: `cross_rate = 1.0`
  - 说明 loss-adaptive weighting 并未解决 `Burgers` 的宽临界带，且在过渡点上可能更差

这一组结果说明：

1. 标准的 loss-adaptive baseline 也表现出显著系统依赖性。
2. 它更像是在 `Stokes/Fisher-KPP` 这类规则边界案例上压缩边界带，而不是对 `Burgers` 提供通用修复。
3. 因而，本文主张的系统相关边界语义并不会因为引入标准自适应权重而消失。

## 2. 变体对综合可靠性的影响

这轮结果说明，绝对 `rel_l2` 边界和综合可靠性 `R` 在跨变体时不能简单等同。

最明显的例子是：

- `Burgers failure_obs32_noise0175`
  - `weight_balanced_v2` 下 `rel_l2 = 0.0364`
  - 仍高于当前固定阈值 `0.02599`
  - 但 `R_mean = 0.8639`

这暴露出一个新问题：

`基于 baseline 的 rel_l2 边界阈值在跨变体时未必仍然保持一致语义。`

因此，本轮实验支持以下更稳的表述：

1. 案例角色分工在变体下大体稳定。
2. 但绝对边界阈值并不完全可跨变体复用。

## 3. Burgers 上训练策略的跨变体稳健性

这里比较 `baseline / naive_region_aware_v1 / dim_guided_v2`。

### 3.1 baseline 变体

- baseline: `rel_l2 = 0.0567`, `R = 0.5253`
- naive v1: `rel_l2 = 0.0456`, `R = 0.4822`
- dim-guided v2: `rel_l2 = 0.0499`, `R = 0.6555`

结论：
- `dim-guided v2` 优于 baseline 和 naive v1

### 3.2 capacity_v1 变体

- baseline: `rel_l2 = 0.0428`, `R = 0.8125`
- naive v1: `rel_l2 = 0.0454`, `R = 0.5092`
- dim-guided v2: `rel_l2 = 0.0386`, `R = 0.8563`

结论：
- `dim-guided v2` 在更强容量下仍保持最优

### 3.3 weight_balanced_v2 变体

- baseline: `rel_l2 = 0.0464`, `R = 0.7282`
- naive v1: `rel_l2 = 0.0440`, `R = 0.7872`
- dim-guided v2: `rel_l2 = 0.0328`, `R = 0.7844`

结论：
- `dim-guided v2` 在误差上最好
- 但 `R` 略低于 naive v1
- 说明它不是在所有变体下都严格最优

## 4. 当前最稳的结论

这轮变体稳健性实验支持如下表述：

1. `Poisson / Stokes-Poiseuille / Burgers` 的角色分工在少量 PINN 变体下总体稳定。
2. 变体会明显平移绝对边界位置，尤其在 `Stokes-Poiseuille` 和 `Burgers` 上。
3. `Burgers` 的关键困难区并没有因变体而消失，说明其概率边界和高风险区域并非单个实现 artifact。
4. `dim-guided v2` 在 `Burgers` 上对多个变体仍具竞争力，并在 `baseline` 和 `capacity_v1` 下保持最优；但它不是在所有变体下都严格支配其他策略。
5. 经典 `RAR` 自适应基线进一步说明：adaptive baseline 也只是在移动边界，而不是把四案例压成同一种语义。
6. 标准的 loss-adaptive weighting 对 `Stokes/Fisher-KPP` 更友好，但没有抹去 `Burgers` 的宽临界带和高风险点。

## 5. 新暴露的问题

这轮结果也暴露出两个新的严谨性问题：

1. 固定 `rel_l2` 阈值在跨变体时不一定保持一致语义。
2. 训练策略优劣在跨变体时仍可能发生局部翻转，因此不能把 `dim-guided v2` 写成“普适最优”。

因此，下一步论文写法应进一步收紧为：

- 系统角色分工具有一定稳健性
- 绝对边界位置和策略最优性仍依赖具体 PINN 配方

# U4：训练预算与 protocol 充分性控制

本轮实验用代表工况对比 `baseline_budget` 与 `stronger_budget`，目的是检验统一最小 protocol 是否人为放大了复杂系统的边界现象。

## 核心结论

- 预算增强会整体降低 `rel_l2` 并在部分点降低越界率，但不会把三类系统压成同一种边界语义。
- `Poisson` 在两种 budget 下都保持稳定；`Stokes-Poiseuille` 的规则边界位置后移，但硬点仍集中在低观测高噪声角落；`Burgers` 的高风险点排序和 seed 敏感现象没有消失。
- 因而，`H3` 中的系统依赖性不能简单归因于当前统一最小 budget 不足，但应承认 budget 会移动边界绝对位置。

### Poisson

- `stable_noisy_obs64_noise020`: rel_l2 `0.0952 ± 0.0044` -> `0.0231 ± 0.0062`, failure rate `0.00` -> `0.00`, dominant `physics_consistency` -> `physics_consistency`
- `stable_sparse_obs32_noise020`: rel_l2 `0.0948 ± 0.0039` -> `0.0243 ± 0.0073`, failure rate `0.00` -> `0.00`, dominant `physics_consistency` -> `physics_consistency`
- 点级 rel_l2 排序相关：`rho = -1.000`，baseline hardest = `stable_noisy_obs64_noise020`，stronger hardest = `stable_sparse_obs32_noise020`。

### Stokes-Poiseuille

- `near_boundary_obs12_noise020`: rel_l2 `0.0312 ± 0.0128` -> `0.0357 ± 0.0091`, failure rate `0.33` -> `0.33`, dominant `physics_consistency` -> `physics_consistency`
- `boundary_obs8_noise0125`: rel_l2 `0.0165 ± 0.0036` -> `0.0217 ± 0.0028`, failure rate `0.00` -> `0.00`, dominant `physics_consistency` -> `physics_consistency`
- `failure_obs8_noise020`: rel_l2 `0.0253 ± 0.0053` -> `0.0374 ± 0.0026`, failure rate `0.00` -> `0.33`, dominant `physics_consistency` -> `physics_consistency`
- 点级 rel_l2 排序相关：`rho = 0.500`，baseline hardest = `near_boundary_obs12_noise020`，stronger hardest = `failure_obs8_noise020`。

### Burgers

- `safe_edge_obs64_noise005`: rel_l2 `0.0223 ± 0.0042` -> `0.0134 ± 0.0038`, failure rate `0.33` -> `0.00`, dominant `physics_consistency` -> `physics_consistency`
- `transition_obs48_noise005`: rel_l2 `0.0260 ± 0.0116` -> `0.0168 ± 0.0095`, failure rate `0.67` -> `0.33`, dominant `physics_consistency` -> `physics_consistency`
- `seed_sensitive_obs32_noise010`: rel_l2 `0.0356 ± 0.0135` -> `0.0364 ± 0.0142`, failure rate `0.67` -> `0.67`, dominant `physics_consistency` -> `physics_consistency`
- `failure_obs64_noise015`: rel_l2 `0.0472 ± 0.0102` -> `0.0333 ± 0.0137`, failure rate `1.00` -> `0.33`, dominant `physics_consistency` -> `physics_consistency`
- 点级 rel_l2 排序相关：`rho = 0.800`，baseline hardest = `failure_obs64_noise015`，stronger hardest = `seed_sensitive_obs32_noise010`。

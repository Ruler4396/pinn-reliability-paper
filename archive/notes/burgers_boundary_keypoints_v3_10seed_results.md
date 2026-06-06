# Burgers 边界关键点高密度 seed 结果

数据目录：[/root/dev/pinn-reliability-paper/minimal_pinn/results/probes/burgers_boundary_keypoints_v3_10seed](/root/dev/pinn-reliability-paper/minimal_pinn/results/probes/burgers_boundary_keypoints_v3_10seed)

本轮对 `8` 个关键边界点进行了高密度复现，每个点使用 `10` 个 seeds。

## 结论

- 当前结果可以更清楚地区分稳定安全点、过渡点、seed-sensitive 点和稳定失效点。
- 按 `rel_l2` 的跨点严重度排序，逐 seed 相对总体均值排序的平均 Spearman 相关系数为 `0.740`。
- 按重标定 `R` 的跨点严重度排序，逐 seed 相对总体均值排序的平均 Spearman 相关系数为 `0.745`。

## 代表性现象

- `safe_clean_obs128_noise000`: failure rate = `0.40` (95% CI `[$0.168, 0.687$]`), `rel_l2 = 0.0278 ± 0.0101`, dominant = `training_stability` (share `0.40`)
- `safe_edge_obs64_noise005`: failure rate = `0.40` (95% CI `[$0.168, 0.687$]`), `rel_l2 = 0.0295 ± 0.0103`, dominant = `physics_consistency` (share `0.60`)
- `transition_obs48_noise005`: failure rate = `0.70` (95% CI `[$0.397, 0.892$]`), `rel_l2 = 0.0313 ± 0.0081`, dominant = `physics_consistency` (share `0.60`)
- `seed_sensitive_obs32_noise010`: failure rate = `0.90` (95% CI `[$0.596, 0.982$]`), `rel_l2 = 0.0405 ± 0.0220`, dominant = `physics_consistency` (share `0.50`)
- `transition_obs24_noise0125`: failure rate = `0.90` (95% CI `[$0.596, 0.982$]`), `rel_l2 = 0.0549 ± 0.0205`, dominant = `physics_consistency` (share `0.50`)
- `failure_obs16_noise0125`: failure rate = `1.00` (95% CI `[$0.722, 1.000$]`), `rel_l2 = 0.0557 ± 0.0180`, dominant = `physics_consistency` (share `0.70`)
- `failure_obs64_noise015`: failure rate = `1.00` (95% CI `[$0.722, 1.000$]`), `rel_l2 = 0.0442 ± 0.0076`, dominant = `physics_consistency` (share `0.50`)
- `failure_obs32_noise0175`: failure rate = `1.00` (95% CI `[$0.722, 1.000$]`), `rel_l2 = 0.0604 ± 0.0202`, dominant = `physics_consistency` (share `0.60`)

## 判断

- `Burgers` 的边界不是单一切点，而是具有统计宽度的过渡带。
- 除 failure probability 之外，严重度排序和主导维度分布本身也具有可统计分析的稳定性。
- 这批高密度关键点结果比先前的 5-seed 局部矩阵更适合写入主文作为概率边界证据。

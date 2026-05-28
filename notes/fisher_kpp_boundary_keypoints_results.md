# Fisher Kpp 边界关键点高密度 seed 结果

数据目录：[/root/dev/pinn-reliability-paper/minimal_pinn/results/probes/fisher_kpp_boundary_keypoints_v1_10seed](/root/dev/pinn-reliability-paper/minimal_pinn/results/probes/fisher_kpp_boundary_keypoints_v1_10seed)

本轮对 `8` 个关键边界点进行了高密度复现，每个点使用 `10` 个 seeds。

## 结论

- 当前结果可以更清楚地区分稳定安全点、过渡点和稳定失效点。
- 按 `rel_l2` 的跨点严重度排序，逐 seed 相对总体均值排序的平均 Spearman 相关系数为 `0.879`。
- 按重标定 `R` 的跨点严重度排序，逐 seed 相对总体均值排序的平均 Spearman 相关系数为 `0.931`。

## 代表性现象

- `safe_clean_obs64_noise000`: failure rate = `0.00` (95% CI `[$0.000, 0.278$]`), `rel_l2 = 0.0110 ± 0.0020`, dominant = `training_stability` (share `0.60`)
- `edge_obs16_noise005`: failure rate = `0.30` (95% CI `[$0.108, 0.603$]`), `rel_l2 = 0.0175 ± 0.0060`, dominant = `training_stability` (share `0.40`)
- `transition_obs128_noise020`: failure rate = `0.50` (95% CI `[$0.237, 0.763$]`), `rel_l2 = 0.0219 ± 0.0066`, dominant = `training_stability` (share `0.70`)
- `edge_obs32_noise010`: failure rate = `0.60` (95% CI `[$0.313, 0.832$]`), `rel_l2 = 0.0213 ± 0.0050`, dominant = `training_stability` (share `0.50`)
- `failure_obs32_noise020`: failure rate = `0.90` (95% CI `[$0.596, 0.982$]`), `rel_l2 = 0.0384 ± 0.0131`, dominant = `training_stability` (share `0.60`)
- `transition_obs64_noise030`: failure rate = `0.90` (95% CI `[$0.596, 0.982$]`), `rel_l2 = 0.0350 ± 0.0133`, dominant = `training_stability` (share `0.60`)
- `failure_obs128_noise030`: failure rate = `1.00` (95% CI `[$0.722, 1.000$]`), `rel_l2 = 0.0302 ± 0.0106`, dominant = `training_stability` (share `1.00`)
- `failure_obs16_noise030`: failure rate = `1.00` (95% CI `[$0.722, 1.000$]`), `rel_l2 = 0.0723 ± 0.0367`, dominant = `structural_stability` (share `0.40`)

## 判断

- `Fisher Kpp` 的边界不是单一切点，而是具有统计宽度的过渡带。
- 除 failure probability 之外，严重度排序和主导维度分布本身也具有可统计分析的稳定性。
- 这批高密度关键点结果比单次粗矩阵更适合写入主文作为边界统计证据。

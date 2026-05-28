# baseline 多 seed 结果

数据来源：
- [summary.csv](/root/dev/pinn-reliability-paper/minimal_pinn/results/baseline_multiseed_v1/summary.csv)
- [summary.json](/root/dev/pinn-reliability-paper/minimal_pinn/results/baseline_multiseed_v1/summary.json)
- [run_rows.csv](/root/dev/pinn-reliability-paper/minimal_pinn/results/baseline_multiseed_v1/run_rows.csv)

配置：
- seeds: `41, 42, 43, 44, 45`
- 案例：
  - `Poisson`
  - `Stokes-Poiseuille`
  - `Burgers`

核心结果：

## Poisson

- `rel_l2 = 0.0965 ± 0.0050`
- 范围：`[0.0887, 0.1018]`
- `reliability_raw = 0.7449 ± 0.0248`

解释：
- `Poisson` clean baseline 较稳定，但与旧正文中的单次数值 `0.1139` 存在可见偏差。
- 因此，正文不应继续使用单次 baseline 数值。

## Stokes-Poiseuille

- `rel_l2 = 0.0103 ± 0.0026`
- 范围：`[0.0072, 0.0141]`
- `reliability_raw = 0.9380 ± 0.0046`

解释：
- `Stokes-Poiseuille` clean baseline 很稳。
- 旧正文中的 `0.0267` 不再适合作为 clean baseline 主数字，应替换为多 seed 统计值。

## Burgers

- `rel_l2 = 0.0178 ± 0.0097`
- 范围：`[0.0100, 0.0346]`
- `reliability_raw = 0.9330 ± 0.0125`

解释：
- `Burgers` clean baseline 平均精度较好，但方差显著高于 `Poisson` 与 `Stokes-Poiseuille`。
- 这与其后续更宽、更随机的临界带是相容的。

总体结论：
- baseline 相关表述必须从“单次数值”改成“多 seed 均值 ± 标准差”。
- 三案例中：
  - `Poisson` 稳定且温和
  - `Stokes-Poiseuille` 最稳
  - `Burgers` 平均表现可接受，但 seed 敏感性最强

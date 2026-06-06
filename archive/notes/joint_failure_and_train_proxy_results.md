# 联合失效与训练稳定性代理分析

- 输出目录：[/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/joint_failure_and_train_proxy_v1](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/joint_failure_and_train_proxy_v1)

## 1. Burgers 越界点的联合失效

- 越界点数量：`59`
- 以固定绝对阈值统计时，双低/多低现象存在，但并不占多数。
- 更能体现复杂性的证据来自前两弱维度的接近性，而不是所有点同时跌破同一阈值。

## 2. D_train 与 failure rate 的关系

- keypoint 数量：`8`
- failure rate 与平均 `training_stability_recal` 的 Spearman 相关：`-0.741`
- failure rate 与平均 `training_stability_recal` 的 Pearson 相关：`-0.637`

这表明当前 `D_train` 与跨 seed 失败率具有明显负相关，因此可被视为 inter-run sensitivity 的一个有效代理，但二者并不等同：单次训练内部稳定性无法完全替代多 seed 概率边界分析。

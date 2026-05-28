# Helmholtz 与 advection-diffusion 首轮接入结果

## 新增目的

本轮新增两个代表系统：

- `Helmholtz`
  - 作用：补“高频/振荡型椭圆问题”
- `advection_diffusion`
  - 作用：补“显式对流-扩散竞争系统”

目标不是立刻把它们都纳入主文，而是先回答一个更基础的问题：

在当前统一最小 PINN 协议下，这两个系统的 clean baseline 能否站稳。

## 当前接入形式

- `Helmholtz`：二维单位方形上的 manufactured inhomogeneous Helmholtz，使用振荡型解析真解。
- `advection_diffusion`：二维单位方形上的 steady advection-diffusion，使用零 Dirichlet 边界和 manufactured forcing。

## 当前结果

### advection_diffusion

首轮 clean baseline 已站稳：

- 结果目录：
  - [advection_diffusion_clean_baseline](/root/dev/pinn-reliability-paper/minimal_pinn/results/advection_diffusion_clean_baseline)
- 关键结果：
  - `rel_l2 ≈ 0.0247`
  - `structure_error ≈ 1.10e-4`
  - `reliability_raw ≈ 0.7055`

这说明 `advection_diffusion` 可以直接进入后续的 `clean -> sparse clean -> sparse noisy` 三阶段实验。

### Helmholtz

当前统一 `tanh` 最小协议下，Helmholtz clean baseline 尚未站稳。

已完成的第一个 tuned baseline：

- 结果目录：
  - [helmholtz_clean_tuned_v1](/root/dev/pinn-reliability-paper/minimal_pinn/results/helmholtz_clean_tuned_v1)
- 关键结果：
  - `rel_l2 ≈ 1.0021`
  - `boundary_rms ≈ 0.5072`
  - `structure_error ≈ 0.0578`

结论：

- 当前最小 `tanh` PINN 对振荡型椭圆问题明显更脆弱；
- 这不是“略差一点”的 clean baseline，而是当前协议下尚未学到可用解；
- 因此 Helmholtz 还不能直接进入 sparse/noisy 矩阵。

## 当前判断

这轮结果说明了两件事：

1. `advection_diffusion` 是一个可直接纳入主线的新增系统。
2. `Helmholtz` 是一个有价值但更困难的 stress test，目前更像是“暴露统一协议上限”的案例，而不是已经准备好进入主文矩阵的案例。

## 下一步建议

1. 先对 `advection_diffusion` 跑 `sparse clean` 与 `sparse noisy`，确认它在观测退化下是否呈现与 `Stokes/Burgers` 不同的边界语义。
2. 对 `Helmholtz` 单独设计更合适的 clean baseline protocol，再决定是否进入主文。

# 新增案例扩展计划

当前新增两个案例，用来补当前主线中的两个空白：

- `Helmholtz`
  - 目标：补“椭圆型但高频/振荡”的空白
  - 当前角色：替代 `Poisson` 过于平滑的负结果，检验椭圆型内部是否也会出现更复杂的可靠性语义
- `advection_diffusion`
  - 目标：补“显式对流-扩散竞争”的空白
  - 当前角色：在 `Stokes` 与 `Burgers` 之间增加一个更典型的 transport-diffusion 系统

首轮实验策略：

1. 先跑 clean baseline，确认最小 PINN 是否能学到可用解。
2. 如果 clean baseline 站不住，不进入 sparse/noisy 矩阵。
3. `Helmholtz` 允许使用稍强 clean tuned baseline，以避免高频振荡问题被统一最小 budget 误判为“完全不可学”。
4. `advection_diffusion` 优先沿用统一 clean baseline。

当前方程选择：

- `Helmholtz`：二维单位方形上的 manufactured inhomogeneous Helmholtz，零 Dirichlet 边界，高频正弦真解。
- `advection_diffusion`：二维单位方形上的 steady advection-diffusion，零 Dirichlet 边界，带指数包络的 manufactured 真解。

当前结构稳定性定义：

- `Helmholtz`：中线剖面的振荡形状保持
- `advection_diffusion`：中线剖面的对流-扩散形状保持

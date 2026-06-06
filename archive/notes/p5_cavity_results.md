# P5：更实际案例探索结果

## 新增案例

本轮 `P5` 新增了一个更接近经典 CFD 使用场景的案例：

- `2D lid-driven cavity flow`
- `Re = 100`
- 案例实现：`minimal_pinn/cases/lid_driven_cavity.py`

该案例使用数值求解得到的参考速度场作为 observation/evaluation truth，并在最小 PINN 框架内预测 `(u, v, p)`，其中数据约束只作用于 `(u, v)`，物理约束通过稳态不可压 Navier-Stokes 残差给出。

## 运行结果

### 初始 clean baseline

配置：
- `configs/cavity_clean_baseline.json`
- `300` epoch

结果：
- `rel_l2 = 0.5620`
- `rel_l2_u = 0.4352`
- `rel_l2_v = 0.8331`

该结果说明新案例已经能被当前最小 PINN 学到部分结构，但 clean baseline 还明显偏弱，不适合直接进入 sparse/noisy 阶段。

### 小幅调参后的 clean baseline

配置：
- `configs/cavity_clean_tuned_v1.json`
- `600` epoch
- `data/boundary` 权重由 `10` 提高到 `20`

结果：
- `rel_l2 = 0.3731`
- `rel_l2_u = 0.2722`
- `rel_l2_v = 0.5778`
- `structure_error = 0.0354`

该结果较初始 baseline 有明显改善，但仍未达到“clean baseline 足够稳健，可以作为主文边界扫描起点”的标准。

## 当前判断

`lid-driven cavity` 作为更实际案例是合理的，但在当前最小 PINN 骨架下：

1. 案例已经成功接入，参考场生成与训练链路均打通。
2. clean baseline 能收敛，但精度仍偏弱。
3. 因此当前不宜直接把该案例纳入主文的 sparse/noisy 矩阵证据链。

更稳妥的定位是：

- 作为“更复杂 benchmark 已接入并完成首轮可行性验证”的探索结果保留；
- 在进一步改进网络表示或训练策略后，再决定是否升级为主文案例。

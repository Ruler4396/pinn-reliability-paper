# 单维 vs 多维统计检验结果

结果目录：
- `/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/single_vs_multi_v1`

核心文件：
- `single_vs_multi_summary.csv`
- `single_vs_multi_summary.json`
- `figure_20_pca_explained_variance.png`
- `figure_21_risk_separability.png`
- `figure_22_rel_l2_r2.png`

## 1. PCA：当前四维得分并没有塌成单轴

按重标定后的四个维度得分做 PCA，得到：

- `Poisson`
  - `PC1 = 0.5639`
  - `PC1 + PC2 = 0.8641`

- `Stokes-Poiseuille`
  - `PC1 = 0.6340`
  - `PC1 + PC2 = 0.8759`

- `Burgers`
  - `PC1 = 0.7138`
  - `PC1 + PC2 = 0.9544`

这说明，在当前四维得分空间中，没有任何一个案例能够被“单一主轴”完整解释。即使是最接近单轴的 `Burgers`，第一主成分也只解释约 `71%` 方差。

但这一步也没有直接证明“`Burgers` 一定最强多维”。更准确的结论是：

1. 四维得分没有塌缩成完全单轴结构。
2. PCA 本身不足以单独证明 `Burgers` 的多维性最强。

## 2. 一维 vs 四维的可分性

这里做了两种目标：

1. 目标 A：识别“高 `rel_l2` 风险点”
2. 目标 B：识别“低综合可靠性 `R` 点”

### 2.1 目标 A：高 rel_l2 风险点

结果：

- `Poisson`: `rel_l2-only = 1.0000`, `4D = 0.8920`
- `Stokes-Poiseuille`: `rel_l2-only = 0.9896`, `4D = 0.8958`
- `Burgers`: `rel_l2-only = 0.8898`, `4D = 0.7659`

这个结果不能被解释为“四维没价值”，因为目标标签本身就是由 `rel_l2` 定义的，`rel_l2-only` 天然占优。它只能说明：

`如果问题本身被定义成“识别高 rel_l2”，那么单一 rel_l2 当然是最优特征。`

### 2.2 目标 B：低综合可靠性点

结果：

- `Poisson`: `rel_l2-only = 0.7614`, `4D = 0.8920`, 增益 `+0.1307`
- `Stokes-Poiseuille`: `rel_l2-only = 0.8571`, `4D = 0.9167`, 增益 `+0.0595`
- `Burgers`: `rel_l2-only = 0.9167`, `4D = 0.9250`, 增益 `+0.0083`

这说明：

1. 当目标从“高误差”切换为“低综合可靠性”时，四维表示在三类案例上都优于单一 `rel_l2`。
2. 这证明四维框架确实包含了超出单一误差的信息。
3. 但在 `Burgers` 中，这种增益并没有大到足以单靠这一项就宣布“强多维性已被完全证明”。

## 3. 各维度是否只是 rel_l2 的映射：R^2 检验

用线性回归检验每个维度能被 `rel_l2` 单独解释到什么程度，结果如下。

### 3.1 Poisson

- `physics`: `R^2 = 0.1456`
- `training`: `R^2 = 0.0012`
- `numerical`: `R^2 = 0.9501`
- `structural`: `R^2 = 0.4266`
- `R`: `R^2 = 0.3770`

解释：

- `numerical_accuracy` 几乎就是 `rel_l2` 的映射，这是预期内的。
- `training_stability` 基本不能由 `rel_l2` 解释。
- `physics` 和 `structure` 也不是简单的单调映射。

### 3.2 Burgers

- `physics`: `R^2 = 0.8449`
- `training`: `R^2 = 0.0574`
- `numerical`: `R^2 = 0.9584`
- `structural`: `R^2 = 0.7811`
- `R`: `R^2 = 0.8774`

解释：

- `numerical_accuracy` 和 `physics_consistency` 与 `rel_l2` 高度耦合。
- 但 `training_stability` 几乎不能被 `rel_l2` 单独解释。
- 这说明 `Burgers` 中至少有一部分关键退化信息不在单一误差轴上。

### 3.3 Stokes-Poiseuille

- `physics`: `R^2 = 0.8820`
- `training`: `R^2 = 0.2585`
- `numerical`: `R^2 = 0.9656`
- `structural`: `R^2 = 0.0594`
- `R`: `R^2 = 0.7828`

解释：

- `numerical_accuracy` 与 `rel_l2` 高度耦合，符合“误差主导边界”的总体图景。
- `structural_stability` 却几乎不能由 `rel_l2` 解释。
- 因此 `Stokes-Poiseuille` 不是纯单维，只是它的主导机制仍偏误差主导。

## 4. 当前最稳的结论

这组统计检验后，最稳的结论应当调整为：

1. 现有四维框架并没有塌缩为单一 `rel_l2` 轴。
2. 至少 `training_stability` 和部分案例中的 `structural_stability` 不能被单一误差简单解释。
3. 但“强多维性”的证据并不是在所有案例上都一样强。
4. `Poisson` 更像稳健对照，`Stokes-Poiseuille` 是弱多维、误差主导，`Burgers` 中最值得强调的是训练稳定性不受单一误差充分解释。

## 5. 仍未完全解决的问题

这一步解决了“多维是否完全等于 rel_l2 映射”的一部分问题，但没有彻底解决两个核心疑问：

1. 这些现象是否能跨 PINN 变体稳定存在。
2. `Burgers` 的多维性是否在其他合理实现下仍然成立。

因此，下一步最重要的仍然是：

- 做跨 PINN 变体稳健性实验，而不是继续扩大 PDE 案例数量。

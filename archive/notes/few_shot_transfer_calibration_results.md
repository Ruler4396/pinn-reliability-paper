# 少样本迁移校准结果

本轮实验对应方案：

- `notes/few_shot_transfer_calibration_plan.md`

分析脚本：

- `minimal_pinn/analyze_few_shot_transfer_calibration.py`

结果目录：

- `minimal_pinn/results/analysis/few_shot_transfer_calibration_v1`

核心输出：

- `transfer_calibration_summary.csv`
- `transfer_calibration_summary.json`
- `transfer_disagreement_summary.csv`
- `per_case_variant_mapping.csv`
- `figure_25_transfer_label_agreement.png`
- `figure_26_transfer_disagreement_reduction.png`
- `figure_27_transfer_ordering_rho.png`

## 1. 本轮比较的方法

本轮只使用已有 `variant_robustness_v1` 结果，不新增训练。比较三种方案：

- `M0_raw`
  - 不迁移，直接复用当前原始阈值/分区语义
- `M1_two_anchor_linear`
  - 使用 2 个锚点做线性迁移
- `M2_three_anchor_piecewise`
  - 使用 3 个锚点做分段线性迁移
- `M3_order_constrained_piecewise`
  - 使用 3 个锚点，但先将锚点投影到符合严重度顺序的单调序列，再做分段迁移
- `M4_rel2_constrained_R`
  - 在 `M3` 基础上，再用已迁移的 `rel_l2` 对 `R` 做保守约束

当前只分析两个主案例：

- `Stokes-Poiseuille`
- `Burgers`

## 2. 主要结果

### 2.1 Stokes-Poiseuille：三锚点分段迁移有效，双锚点线性迁移没有额外价值

对非 baseline 变体平均后：

- `M0_raw`
  - `rel_l2` 标签准确率：`0.50`
  - `R` 标签准确率：`0.833`
- `M1_two_anchor_linear`
  - `rel_l2` 标签准确率：`0.50`
  - `R` 标签准确率：`0.50`
- `M2_three_anchor_piecewise`
  - `rel_l2` 标签准确率：`0.833`
  - `R` 标签准确率：`0.833`

同时，跨变体 `rel_l2` 主类别分歧从 `0.667` 降到 `0.333`。

这说明：

- `Stokes` 的阈值漂移可以通过少量锚点部分修正。
- 但只用“安全 + 失效”两个锚点不够，临界点本身必须进入校准。
- 这支持一个重要结论：`Stokes` 的边界扭曲更像“临界带位置偏移”，而不是简单整体缩放。

### 2.2 Burgers：普通三锚点分段迁移会破坏排序，但排序保持约束能缓解这一问题

对非 baseline 变体平均后：

- `M0_raw`
  - `rel_l2` 标签准确率：`0.75`
  - `R` 标签准确率：`0.25`
  - `severity rho` with `rel_l2`：`0.70`
  - `severity rho` with `-R`：`0.60`
- `M1_two_anchor_linear`
  - `rel_l2` 标签准确率：`0.50`
  - `R` 标签准确率：`0.25`
  - 排序表现没有改善
- `M2_three_anchor_piecewise`
  - `rel_l2` 标签准确率：`1.00`
  - `R` 标签准确率：`0.50`
  - 但 `severity rho` with `rel_l2` 降到 `0.10`
  - `severity rho` with `-R` 也下降到 `0.50`
- `M3_order_constrained_piecewise`
  - `rel_l2` 标签准确率：`0.875`
  - `R` 标签准确率：`0.50`
  - `severity rho` with `rel_l2` 回到 `0.70`
  - `severity rho` with `-R` 回到 `0.60`

同时，`Burgers` 的跨变体分歧虽然下降了：

- `rel_l2` 分歧：`0.50 -> 0.25`
- `R` 分歧：`1.00 -> 0.75`

其中：

- `M2` 的收益并不干净，因为它伴随排序信息明显退化。
- `M3` 则保留了大部分标签收益，同时避免了 `M2` 中出现的排序坍塌。

这说明：

- 在 `Burgers` 这种边界本身不规则、带有种子敏感区的案例中，锚点次序反转本身就是迁移失败的重要来源。
- 对锚点施加排序保持约束后，`M3` 能在不明显损害全局严重度排序的前提下，保留标签一致性的主要收益。
- 这说明“排序保持约束”是复杂多维边界场景下必要的迁移机制。

### 2.3 进一步用 `rel_l2` 约束 `R` 没有带来额外收益

我们又测试了 `M4_rel2_constrained_R`：

- 它在 `M3` 基础上，用已迁移的 `rel_l2` 对 `R` 做保守上界约束
- 目标是继续提升 `Burgers` 上的 `R` 标签精度

结果是：

- `Burgers`
  - `M4` 与 `M3` 基本持平
  - `R` 标签准确率仍为 `0.50`
  - 排序相关性也没有进一步提升
- `Stokes-Poiseuille`
  - `M4` 反而把平均 `R` 标签准确率从 `0.833` 降到 `0.667`
  - 虽然跨变体 `R` 主类别分歧降到了 `0.0`
  - 但这是以更保守、也更不准确的分类为代价

这说明：

- 当前 `Burgers` 上的核心问题，不是简单的“`R` 太乐观”，而是 `R` 本身在新变体里承载的语义已经发生偏移。
- 单纯用 `rel_l2` 给 `R` 加保守约束，不足以恢复它的分区语义。
- 因此，`M4` 不应作为当前首选方案。

### 2.3 当前最稳的结论不是“迁移校准已经成功”，而是“迁移需要区分系统类型”

本轮不能写成：

- “少样本迁移校准已经普遍解决跨变体阈值问题”

当前更准确的结论是：

- `Stokes-Poiseuille` 中，少样本迁移校准是有前景的，尤其三锚点分段迁移能明显改善标签一致性。
- `Burgers` 中，少样本迁移校准只能局部修复标签，但会破坏排序语义，因此当前方案还不够稳。

## 3. 对论文的影响

本轮结果把论文主张进一步收紧为：

1. 跨变体阈值对齐是可以尝试的，但必须区分是否包含排序保持约束。
2. 对于 `Burgers` 这类概率边界/多维边界案例，简单少样本映射不够；排序保持约束是必要条件。
3. 进一步用 `rel_l2` 对 `R` 做保守约束，并不能自动修复 `R` 的迁移语义。
3. 因此，本文当前最稳的写法仍然是：
   - 绝对阈值不可直接跨变体复用
   - 少样本迁移在规则边界案例中有稳定收益
   - 在复杂多维边界案例中，少样本迁移只有在加入排序保持约束后才具有可接受表现

## 4. 本轮是否解决了当前核心问题

### 已解决的部分

- 已证明“少样本迁移”不是空想，在 `Stokes-Poiseuille` 上确实能恢复更多语义一致性。
- 已证明“临界锚点”是必要的，双锚点线性方案太弱。

### 尚未解决的部分

- `Burgers` 上 `R` 标签精度仍然偏低，`M3` 和 `M4` 都只把平均 `R` 标签准确率维持在 `0.50`。
- 复杂多维边界场景下，排序保持约束虽然有效，但还不能称为最终解。

## 5. 下一步建议

如果继续沿这条线推进，最合理的不是继续加更多锚点，而是做下面两项之一：

1. 设计“排序保持约束 + R 分区专用映射”的迁移校准  
   目标：保留 `M3` 的排序优势，同时真正提升 `R` 标签精度。  
   当前 `M4` 说明，简单保守约束不是这条路的最终答案。

2. 设计“仅对边界附近做局部校准”的迁移方案  
   目标：不去拟合全局语义，只修复 safe/critical/failure 的局部边界切换。

当前结果已经足够支持一个阶段性判断：

- 少样本迁移校准在规则边界系统中具有稳定方法学潜力
- 在 `Burgers` 这类复杂多维边界上，排序保持约束是必要机制，但当前方案还不是最终答案

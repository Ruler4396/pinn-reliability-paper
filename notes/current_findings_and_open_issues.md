# 当前实验结论与待解决问题台账

本文档用于固化当前已经得到的实验结论、明确仍未解决的问题，并作为后续阶段完成后的对照检查清单。

## A. 当前已得到的核心实验结论

### A1. 三类主案例的角色已经分化

1. `Poisson` 在当前测试范围内没有出现 practical boundary。
2. `Stokes-Poiseuille` 呈现窄而规则的边界，越界区主要由数值精度主导。
3. `Burgers` 呈现宽边界、局部不规则边界以及显著的种子敏感现象，是当前最强的主结果来源。

对应依据：
- `notes/results_section_zh.md`
- `notes/probability_boundary_results.md`
- `notes/recalibrated_dimensions_results.md`

### A2. 多维可靠性框架不是在所有系统上都同样强

1. 在 `Poisson` 中，多维框架的额外收益很弱，更接近“单一误差主导的稳健对照”。
2. 在 `Stokes-Poiseuille` 中，多维框架有补充信息，但主导机制仍偏向数值误差。
3. 在 `Burgers` 中，多维框架确实补充了单一 `rel_l2` 不能显式表达的训练稳定性与结构信息。

当前最稳的表述不是“PINN 失效天然是四维的”，而是：

`失效的维度强度具有系统依赖性；简单系统中近似一维，复杂系统中更明显地表现出多维性。`

对应依据：
- `notes/dimension_ablation_results.md`
- `notes/calibration_sensitivity_results.md`

### A3. Burgers 的边界更适合解释为概率边界

局部多 seed 矩阵表明，`Burgers` 的边界不是单条确定曲线，而是由三部分组成：

1. 稳定安全区
2. 种子敏感过渡区
3. 稳定失效区

当前得到的统计证据包括：

- 越界率在临界带出现 `0.333 -> 0.667 -> 1.0` 的过渡
- 部分格点同时具有高均值和高标准差
- 重标定后的综合可靠性与越界率升高同步坍缩

对应依据：
- `notes/probability_boundary_results.md`

### A4. 区域感知训练存在系统依赖性

1. `naive region-aware v1` 不是可靠的通用策略。
   - 在 `Burgers` 上，它压低了 `rel_l2`，但损害了综合可靠性。
   - 在 `Stokes-Poiseuille` 上，也没有带来净收益。
2. `dim-guided v2` 在 `Burgers` 上给出了一个可写的正结果：
   - `rel_l2: 0.0567 -> 0.0499`
   - `R: 0.5253 -> 0.6555`
3. 同样的 `dim-guided v2` 在 `Stokes-Poiseuille` 上没有取得净收益。

当前最稳的结论是：

`可靠性相空间可以为训练干预提供设计线索，但训练增强的有效性具有明显系统依赖性。`

对应依据：
- `notes/region_aware_v2_results.md`

### A5. 新增更实际案例已经接入，但尚未通过 clean baseline 门槛

新增案例：
- `lid-driven cavity (Re=100)`

当前结果：
- 初始 clean baseline：`rel_l2 = 0.5620`
- 小幅调参后：`rel_l2 = 0.3731`

这说明：
- 新案例实现和训练链路已打通
- 但当前最小 PINN 骨架还不足以让该案例进入主文 sparse/noisy 证据链

对应依据：
- `notes/p5_cavity_results.md`

## B. 当前最关键的未解决问题

### B1. 多维失效是否只是单一潜变量的不同映射

当前风险：
- 可能真正存在的只有一个潜在“失效强度”
- `physics / training / numerical / structure` 只是这个潜变量在不同指标上的投影

当前状态：
- 已完成首轮直接统计检验，见 `notes/single_vs_multi_results.md`
- 结果表明四维得分没有塌成单轴；至少 `training_stability` 和部分案例中的 `structural_stability` 不能被 `rel_l2` 单独解释
- 但 PCA 和可分性结果并未把 `Burgers` 的“强多维性”完全钉死
- 因此该问题目前属于“部分解决，但尚未闭环”

因此，这个问题尚未被严格解决，仍需跨 PINN 变体稳健性验证。

### B2. 当前结论是否依赖于我们这套最小 PINN 的实现

当前风险：
- 边界位置、维度主导模式、region-aware 结果可能受具体网络容量、损失权重和训练策略影响
- 如果换一个 PINN 变体，当前主线可能部分改变

当前状态：
- 已完成首轮跨 PINN 变体稳健性验证，见 `notes/variant_robustness_results.md`
- 当前结果表明：
  - `Poisson / Stokes-Poiseuille / Burgers` 的角色分工总体稳定
  - `Burgers` 的关键困难区没有消失
  - `dim-guided v2` 在 `Burgers` 上对多个变体仍具竞争力
- 但同时也暴露出新的问题：
  - 绝对 `rel_l2` 边界位置会明显随变体平移
  - 固定阈值不一定可跨变体直接复用
  - 训练策略排序仍可能在局部发生翻转

因此，这个问题目前属于“主线稳健性得到初步支持，但阈值可移植性与策略普适性仍未解决”。

补充进展：
- 已完成跨变体阈值/校准可移植性分析，见 `notes/threshold_portability_results.md`
- 当前结果表明：
  - 固定绝对 `rel_l2` 阈值不能跨变体直接复用
  - 安全点归一化后的相对 `rel_l2` 阈值只能部分修正阈值漂移
  - 固定 `R=0.9/0.7` 分区更适合作为严重度排序工具，而不是通用硬阈值

因此，这个问题目前进一步收敛为：
- 哪种最小校准信息足以把阈值语义迁移到新变体
- 是否存在更稳的无量纲边界量替代固定绝对阈值

对应后续方案：
- `notes/few_shot_transfer_calibration_plan.md`

最新进展：
- 已完成首轮少样本迁移校准，见 `notes/few_shot_transfer_calibration_results.md`
- 当前结果表明：
  - `Stokes-Poiseuille` 中，三锚点分段迁移能改善标签一致性
  - `Burgers` 中，普通三锚点迁移会破坏严重度排序，但加入排序保持约束后可显著缓解这一问题
  - 进一步用 `rel_l2` 对 `R` 做保守约束没有继续提升 `Burgers` 的 `R` 分区精度

因此，这个问题目前属于：
- 在规则边界案例中已有可行方向
- 在复杂多维边界案例中已有必要机制，但 `R` 分区迁移仍未闭环

进一步进展：
- 已完成 `R` 分区专用迁移最小版本，见 `notes/r_partition_transfer_results.md`
- 当前结果表明：
  - 在 `Stokes-Poiseuille` 中，重新切分 `R` 基本没有额外收益
  - 在 `Burgers` 中，`P1/P2` 只带来轻微 run 级改进，点级三分类语义并未真正恢复

因此，这个问题进一步收敛为：
- 复杂案例中的关键不只是“切点怎么选”
- 而是连续 `R` 表示本身在新变体下的类间可分性不足

最新进展：
- 已完成 `Burgers` 的 `critical` 多模态诊断，见 `notes/critical_multimodality_results.md`
- 已完成局部边界迁移评估，见 `notes/local_boundary_transfer_results.md`
- 当前结果表明：
  - `transition` 与 `seed-sensitive` 不应再被压成单一 `critical` 类
  - `Stokes-Poiseuille` 仍可保持硬分区解释
  - `Burgers` 更适合改成“排序 + 局部边界”语义模型
  - 其中安全边界的局部评估明显优于原全局三分类，失效边界则与原排序/分区结果大体一致

因此，这个问题当前已被重新定义为：
- `Stokes-Poiseuille` 继续沿用硬分区
- `Burgers` 不再追求统一三分类迁移，而是接受 `critical band` 的多模态结构

### B3. 更实际案例仍然不足以进入主文

当前风险：
- 主文仍主要依赖理想化 benchmark
- 现实相关性仍偏弱

当前状态：
- `cavity` 已完成首轮探索
- 但 clean baseline 未达门槛

### B4. 当前论文 claim 仍需继续受控

当前不能写成：
- “PINN 失效本质上一定是四维的”
- “综合可靠性已显著优于单一指标”
- “region-aware 已形成稳定有效的通用策略”

当前最稳的写法仍然应当是：
- 多维框架用于检验失效到底近似一维还是明显多维
- 该现象具有系统依赖性
- 训练干预具有系统依赖性

## C. 后续阶段的对照检查清单

后续实验完成后，需要逐项检查以下问题是否被解决。

### C1. 单维 vs 多维问题

- [ ] `Poisson` 是否仍表现为近似一维稳健对照
- [ ] `Stokes-Poiseuille` 是否仍表现为弱多维、误差主导
- [ ] `Burgers` 是否在更直接的统计检验下仍需要两个及以上主成分/维度解释
- [ ] 结论是否可以稳定写成“多维性具有系统依赖性”

### C2. 实现依赖性问题

- [ ] 换用 2 到 3 个 PINN 变体后，三案例角色分工是否仍稳定
- [ ] `Burgers` 的概率边界是否仍存在
- [ ] `dim-guided v2` 在 `Burgers` 上的正结果是否仍保留
- [ ] 是否可以更有把握地排除“单个实现 artifact”
- [ ] 固定绝对阈值是否已经被替换为更合理的变体内或迁移后阈值方案
- [ ] `R` 的分区是否已经有更稳的跨变体校准路径
- [x] 少样本迁移是否能在 `Burgers` 中同时保持标签一致性与排序稳定性
- [ ] 排序保持约束下，`Burgers` 的 `R` 分区精度是否还能进一步提升
- [x] 仅通过重新设定 `R` 分区切点，无法从根本上解决 `Burgers` 的分区迁移问题
- [x] `Burgers` 的 `critical_transition` 与 `critical_instability` 在 `M3` 特征空间中不是单簇
- [x] `Stokes-Poiseuille` 仍可保持“排序 + 硬分区”解释
- [x] `Burgers` 的安全边界局部任务比原全局三分类更稳定、更可解释
- [ ] `Burgers` 的失效边界是否还需要进一步独立校准，还是当前局部原型已足够

### C3. 新案例问题

- [ ] `cavity` 是否达到 clean baseline 准入门槛
- [ ] 若达到门槛，是否值得进入 sparse/noisy 主文矩阵
- [ ] 若仍未达到门槛，是否应保留为探索性附录结果

### C4. 写作口径问题

- [ ] 论文主张是否已与最终证据强度匹配
- [ ] 是否仍有过强 claim 未被删掉
- [ ] 是否所有结论都能回指到明确实验结果

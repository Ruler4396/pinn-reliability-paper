# 审稿意见导向的完整升级方案

## 1. 目标

本方案不再把后续工作组织成“补几张图”，而是围绕当前最容易被 reviewer 攻击的科学问题，给出一套可执行的升级路线。目标有三条：

1. 把主实验从“结果堆砌”收束成四个假设检验。
2. 补足当前最脆弱的统计证据与方法定义。
3. 让主文结论建立在更稳的 protocol、校准与对照之上，而不是建立在单一阈值或单次运行之上。

核心原则：

- 不追求“通用阈值”叙事。
- 不把未完成的探索写成已成立的方法结论。
- 优先补强 `Burgers` 的统计证据，其次修严方法定义，再考虑扩案例。
- 主文继续保持三案例主线：`Poisson` / `Stokes-Poiseuille` / `Burgers`。

---

## 2. 当前主文要检验的四个科学假设

`H1`

PINN 的可靠性边界不是单点现象，而是在“观测稀疏度–噪声强度”二维空间中形成可分析结构。

`H2`

单一误差指标不足以完整描述 PINN 失效，多维可靠性框架能够为边界识别、种子敏感性解释、局部边界任务与训练干预提供额外信息。

`H3`

可靠性边界与失效语义具有系统依赖性。

`H4`

训练干预只有在对准主导失效维度时才更可能有效。

---

## 3. 必补实验

### U1. 校准与聚合稳健性实验

#### 目的

防守最关键的质疑：`Stokes` 与 `Burgers` 的主导维度格局，会不会只是某一套分位数与聚合规则“做出来”的。

#### 当前状态

已完成首轮分析。当前在 `27` 组“分位点 × 维度内聚合 × 维度间聚合”配置下：

- `Poisson` 在 `27/27` 组配置下保持 `numerical_accuracy` 主导；
- `Burgers` 在 `27/27` 组配置下保持 `training + structural` 主导；
- `Stokes-Poiseuille` 在 `18/27` 组配置下保持 `numerical_accuracy` 主导，失稳仅出现在“维度内取最小值”的极端保守聚合下。

这说明主结论对分位点与维度间平均方式相对稳健，真正敏感的是是否采用过度保守的维度内聚合。

#### 实验设计

在现有 coarse/refined matrix 结果基础上，不新增训练，重做以下三组敏感性分析：

1. 分位点敏感性
   - `Q0.10 / Q0.90`
   - `Q0.15 / Q0.85`
   - `Q0.20 / Q0.80`
2. 维度间聚合敏感性
   - 等权平均
   - 加权平均（例如强调 non-physics 维度）
   - 最小维度主导型聚合
3. 维度内聚合敏感性
   - 几何平均
   - 算术平均
   - 最小值聚合

#### 输出

- 主导维度分布对比表
- `Stokes` 与 `Burgers` 的边界语义是否保持
- 一张聚合敏感性图或表

#### 验收标准

- 数值可以变化，但以下主结论不能消失：
  - `Stokes` 更接近数值精度主导的规则边界
  - `Burgers` 仍呈现更强的 training/structure 参与
  - `Poisson` 仍只是稳健对照

---

### U2. Burgers 边界区高密度 seed 统计

#### 目的

把“概率边界迹象”提升为更可防守的统计证据。

#### 当前状态

已完成一轮关键点高密度 probe。当前不是对整张局部矩阵盲目扩 seed，而是对 `8` 个关键边界点做了 `10-seed` 复现，覆盖：

- 相对安全侧点
- 过渡点
- seed-sensitive 点
- 稳定失效点

当前结果显示：

- 相对安全侧点的 failure rate 约为 `0.40`，`95%` Wilson 区间约为 `[0.168, 0.687]`
- 过渡点的 failure rate 提高到 `0.70` 与 `0.90`
- 稳定失效点达到 `1.00`，对应区间下界约为 `0.722`
- 跨点严重度排序的逐 seed Spearman 相关系数均值约为：
  - `rel_l2`: `0.740`
  - `R`: `0.745`

这说明 `Burgers` 的边界更接近具有统计宽度的过渡带，而不是单一切点。

#### 实验设计

不扩大整张矩阵，只挑 `6–10` 个关键格点：

- 稳定安全点
- 过渡点
- seed-sensitive 点
- 稳定失效点

建议围绕现有局部矩阵中的关键区域：

- `obs = 64, 48, 32, 24, 16`
- `noise = 0.05, 0.10, 0.125, 0.15, 0.175`

每个格点扩展到 `10–20` 个 seeds。

#### 输出

- 失败率与 `95%` Wilson interval
- `rel_l2` 均值与标准差
- 严重度排序稳定性
- 主导维度分布稳定性

#### 验收标准

- 关键格点的区间显著收窄
- 可以更稳地区分：
  - 稳定安全区
  - 种子敏感过渡区
  - 稳定失效区
- 不仅 failure rate，可连同排序稳定性与主导维度分布一起报告

---

### U3. 干预实验加厚

#### 目的

避免 `H4` 只建立在两个点状 anecdote 上。

#### 实验设计

每个系统至少选 `2–3` 个临界工况：

- `Burgers`：选不同类型的临界点
- `Stokes-Poiseuille`：选规则边界附近不同观测/噪声组合

每个工况至少 `5` 个 seeds。

每个工况对比三类策略：

1. baseline
2. naive intervention
3. dim-guided intervention

最好再补一个：

4. non-dominant-dimension-guided intervention

#### 输出

- `rel_l2`
- 综合可靠性
- 四维分数变化
- 失败率变化

#### 验收标准

- 至少在 `Burgers` 上证明：只有对准主导失效维度时，净收益更可能出现
- 若 `Stokes` 仍无收益，也应作为系统依赖证据保留

---

### U4. 训练预算与 protocol 充分性控制

#### 目的

回应“系统依赖性是不是只是统一最小 protocol 对复杂问题不公平”的质疑。

#### 实验设计

每个 PDE 选 `2–3` 个代表工况，做小型控制：

- `500 vs 1000` epochs
- 或 `500 vs 2000` epochs
- 或 baseline budget vs stronger budget

不需要全矩阵重跑。

#### 输出

- 边界绝对位置变化
- 边界语义是否保持
- seed-sensitive 现象是否仍存在

#### 验收标准

- 可以承认边界位置会移动
- 但 `Stokes` 的规则边界、`Burgers` 的宽临界带和 seed sensitivity 不应消失

#### 当前状态

已完成一轮代表点级别控制实验，在 `Poisson`、`Stokes-Poiseuille` 与 `Burgers` 的 `9` 个代表点上，对比了 `500 epochs + 2048 collocation + 256 boundary` 与 `1000 epochs + 4096 collocation + 512 boundary` 两种 budget。当前结果表明：

- `Poisson` 的代表点在 stronger budget 下继续远离边界；
- `Stokes-Poiseuille` 的边界位置会后移，但规则边界没有消失；
- `Burgers` 的若干高风险点有改善，但 `seed_sensitive_obs32_noise010` 的 failure rate 仍保持在 `0.67`。

因此，`U4` 当前支持的最稳结论是：training budget 会移动边界绝对位置，但不会自动抹去 `Stokes` 的规则边界和 `Burgers` 的宽临界带/seed-sensitive 现象。

---

### U5. 防循环论证的校准实验

#### 目的

回应“先看完整体分布再定义标尺，再用标尺解释整体结果”的循环论证风险。

#### 实验设计

至少做一套：

1. split calibration / analysis
   - 用粗矩阵部分格点做 calibration
   - 剩余格点做 analysis

或

2. leave-region-out calibration
   - 用非边界区确定锚点
   - 在边界区检验结论

#### 输出

- 主导维度格局是否保持
- `Stokes` / `Burgers` 的语义差异是否保持

#### 验收标准

- 关键结论不依赖“先看完整张图后再定尺”

---

## 4. 逻辑与写法必须同步修严的点

### W1. 题目与结论要明确 benchmark-only 维度

当前四维框架中：

- `physics_consistency`
- `training_stability`

是可直接观测维度；

- `numerical_accuracy`
- `structural_stability`

在主实验中依赖参考解。

因此主文必须明确：

- 当前是 reliability analysis / reliability characterization framework
- 不是现实部署时可直接在线判定“是否可信”的完整工具

---

### W2. H2 不能主要用内部自指目标证明

“低综合可靠性更可分”只能作为内部一致性证据。

主文对 `H2` 的关键支撑应尽量建立在外部目标上：

- seed sensitivity
- 局部边界任务
- 干预结果
- operational boundary localization

---

### W3. H3 不能写成因果拆解

当前更稳的写法是：

- 在统一 protocol 下，边界语义呈现显著系统依赖表现

不能写成：

- 已经证明这些差异来自某个单一因果因素

---

### W4. 单误差与多维框架要明确分工

主文应持续保持这条逻辑：

- `rel_l2` 只负责 coarse localization
- 多维框架负责解释边界形成、主导维度与训练干预线索

---

### W5. `critical` 两子机制要么形式化，要么降语气

如果没有补足正式统计支撑，主文就必须写成：

`evidence suggests that the critical band is heterogeneous and likely contains at least two sub-mechanisms`

而不是直接把它写成已经完全成立的分类体系。

---

## 5. 方法定义必须补全的硬点

### M1. 归一化映射

不要在主文中保留与实现和文字描述不一致的固定公式。

当前最稳的写法：

- 锚点参数化的单调归一化映射
- 关注单调性、可校准性与稳健性
- 具体闭式参数化只在实现或附录中说明

### M2. coarse / refined matrix 区分

主文必须明确写出：

- coarse matrix 的取值
- refined matrix 的取值
- 每张图来自哪一种扫描

### M3. dominant dimension 判定规则

必须正式定义为：

- 四个重标定维度分数中的最小者

### M4. structural stability 的案例级定义

主文和补充材料都要清楚写出：

- 每个 PDE 的结构特征 `S`
- 对应距离 `d_str`
- 它为何不是简单的点值误差换皮

### M5. `M3` 迁移的最小可复现描述

至少要写清：

- 三个锚点是什么
- 排序保持约束如何施加
- 分段映射如何构造
- 为什么比 naive linear transfer 更适合

---

## 6. 主文与附录的推荐分工

### 主文必须保留

1. 明确的问题定义
2. 统一最小 protocol
3. 三个角色清晰的 PDE 案例
4. 二维 full-factorial 相空间实验
5. 多 seed 主结果
6. 单指标 vs 多维框架的核心数字
7. `Stokes` / `Burgers` 的语义差异
8. 阈值敏感性与迁移校准的核心结论
9. naive vs dim-guided intervention

### 补充材料更适合放

1. `cavity`
2. 更多网络变体
3. 更细的可视化
4. 完整热图
5. 超参数表
6. 更多迁移和局部边界诊断

---

## 7. 执行顺序

### Phase 1：不新增训练，先修严方法与写法

1. 修主文逻辑和方法定义
2. 补 `H2` 的外部任务表达
3. 明确 benchmark-only 维度
4. 完整写出 `M3`、dominant dimension、structural stability

### Phase 2：最低成本补强实验

1. `U1` 校准与聚合稳健性
2. `U5` 防循环论证校准
3. `U4` 训练预算控制

### Phase 3：最高价值统计补强

1. `U2` Burgers 高密度 seed
2. `U3` 干预实验加厚

### Phase 4：收口

1. 更新主文
2. 更新图表与附录
3. 再决定是否让 `cavity` 进入主文

---

## 8. 新增审稿导向补强项

### R1. Top-k 排序错位分析

#### 目的

直接回答“PCA 第一主成分较高时，多维框架是否仍然改变危险工况识别”。

#### 做法

- 分别按 `rel_l2` 从差到好排序
- 按重标定 `R` 从差到好排序
- 比较 `Top-10 / Top-20 / Top-30` 最差工况集合
- 指标：
  - Jaccard overlap
  - overlap count
  - `rel-only` 与 `R-only` 工况的训练稳定性/结构稳定性均值

#### 当前状态

正在执行。预期重点是：

- `Burgers` 的 Jaccard 显著低于 `Stokes-Poiseuille`
- `Burgers` 的 `R-only` 工况在 `training/structural` 上明显更差

---

### R2. 分位数重标定的公平性声明与原始尺度对照

#### 目的

防止 reviewer 认为案例内分位数校准在人为制造跨系统可比性。

#### 动作

1. 主文明确声明：
   - 重标定后的 `R` 仅用于案例内排序、主导维度识别和局部边界任务
   - 不用于跨案例绝对严重度比较
2. 附录补一张未校准原始指标的跨系统对照图
   - 展示三个系统在原始量纲上的基础指标范围差异

#### 当前状态

- 已完成未校准原始指标跨系统对照图：
  - [figure_40_raw_metric_parallel_coordinates.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/raw_scale_cross_case_v1/figure_40_raw_metric_parallel_coordinates.png)
- 已完成原始尺度汇总：
  - [raw_metric_case_summary.csv](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/raw_scale_cross_case_v1/raw_metric_case_summary.csv)
- 已在方法与结果中写明：
  - 重标定 `R` 是案例内、保序的语义归一化
  - 仅用于案例内排序、主导维度识别与局部边界任务
  - 不用于跨案例绝对严重度比较

---

### R3. 迁移结论降调到“替代组织方式”，不写成完整外推结论

#### 目的

避免从“硬分区不可迁移”直接跳到“框架可迁移”的过强推断。

#### 动作

- 主文只声称：
  - 硬分区在 `Burgers` 中不可稳定迁移
  - `M3 + 排序/局部边界` 是当前更稳的替代组织方式
- 暂不把这部分写成跨系统预测框架

---

### R4. 干预实验增加效应量/区间解释

#### 目的

避免 `H4` 只靠均值差异成立。

#### 动作

1. 在 `U3` 的多工况、多 seed 实验上：
   - 报均值差
   - 报 bootstrap `95%` CI
   - 报 effect size（至少给出标准化均值差）
2. 如果区间跨 `0`，将相关结论降级为 `tentative evidence`

#### 当前状态

- 已完成 `U3` 扩展版：`2` 个系统、`4` 个临界工况、每个工况 `5` 个 seeds，并加入 `non-dominant-guided v3` 对照。
- 已完成配对 bootstrap 与 Cohen's `d_z` 统计。
- 当前最稳结论：
  - `naive region-aware v1` 在 `Burgers/transition_obs48_noise005` 上显著恶化 `rel_l2`；
  - `dim-guided v2` 在当前加厚实验中未给出稳健正效应，且在 `Stokes-Poiseuille` 上对综合可靠性表现出显著负效应；
  - `non-dominant-guided v3` 在 `Burgers/seed_sensitive_obs32_noise010` 上对 `rel_l2` 有显著改善，但其综合可靠性区间仍跨 `0`。
- 因此，`H4` 目前应维持为探索性证据：可以确认 naive 干预不可靠，但还不能把收益唯一归因于“主导失效维度对准”本身。

---

### R5. Poisson 角色降格

#### 目的

避免 reviewer 认为 Poisson 作为主案例信息量不足。

#### 动作

- 在引言、方法和结果中统一将 `Poisson` 写成：
  - `sanity check benchmark`
  - `control group`
- 在讨论中补一句物理解释：
  - 平滑、无尖锐梯度、自伴拉普拉斯结构使其负结果不宜外推

---

## 8. 最低可投稿版标准

最低可投稿版不要求把所有增强项做满，但至少要满足：

- 三案例角色清晰
- H1–H4 全部有对应实验
- baseline 与关键数字都带多 seed 统计
- `Burgers` 概率边界不再只是单次现象
- 多维框架相对单指标有主文级硬数字
- 阈值被明确写成 operational criterion
- `Stokes` / `Burgers` 的语义差异有清晰方法与结果支撑

如果达不到这些条件，就不宜继续增加 case 或扩叙事范围。

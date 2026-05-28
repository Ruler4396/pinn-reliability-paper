# 方法定义形式化 (Method Definitions M1-M5)

本文档对论文涉及的关键方法组件给出精确的形式化定义，以满足审稿人
对"方法可复现性"和"定义完整性"的要求。

---

## M1. 归一化映射 (Logistic Score Calibration)

### 目的
将六个原始指标（physics_rms, boundary_rms, rel_l2, structure_error,
loss_std, loss_ratio）映射到 [0,1] 区间，使不同量纲的指标可聚合。

### 定义
对于指标 $x$ 及其 good/fail 锚点 $g, f$（由案例内分位数重标定确定），
归一化得分 $s \in [0,1]$ 定义为 logistic 映射：

$$
s(x; g, f) = \frac{1}{1 + \exp\big(-k \cdot (x - f)\big)}, \quad
k = \frac{\ln 19}{g - f}
$$

其中 $\ln 19$ 保证 $s(g) = 0.95$（good 锚点处得分 0.95），
$s(f) = 0.05$（fail 锚点处得分 0.05）。

### 锚点选择
- 对每个案例，从 coarse matrix 的 30 个格点中选出 $Q_{15}$（15% 分位）
  和 $Q_{85}$（85% 分位）作为 good/fail 锚点
- 选择规则：
  - Poisson: 无实用失效边界，选 top-quartile rel_l2 格点
  - Stokes / Fisher-KPP / Burgers: 选 rel_l2 超过 1.5× baseline 的格点
- 结果存在 `recalibrated_dimensions_v1/recalibrated_summary.json`

### 使用边界
- 重标定后的得分仅用于案例内排序和主导维度识别
- 不用于跨案例绝对严重度比较（原始尺度对比见附录）

---

## M2. Coarse / Refined / Probability Matrix 区分

### 定义
| 矩阵类型 | 格点密度 | 种子数 | 用途 |
|----------|---------|--------|------|
| **Coarse matrix** | 6 obs × 5 noise = 30 格点 | 1 seed | 初步相图扫描、锚点选择 |
| **Refined matrix** | 6-8 obs × 7 noise | 1 seed | 边界局部细化 |
| **Probability matrix** | 4-5 obs × 5-7 noise | 3-5 seeds | 概率边界估计、Wilson CI |

### 各案例矩阵规格
| 案例 | Coarse | Refined | Probability |
|------|:---:|:---:|:---:|
| Poisson | obs(256..8), noise(0..0.20) | — | — |
| Stokes-Poiseuille | 同上 | obs(64..6), noise(0..0.20) | obs(16..8), noise(0..0.20), 5 seeds |
| Fisher-KPP | obs(256..8), noise(0..0.30) | — | obs(32..8), noise(0..0.20), 5 seeds |
| Burgers | 同上 | obs(128..16), noise(0..0.175) | obs(64..16), noise(0.05..0.175), 5+3 seeds |

### 使用规则
- 论文中的 rel_l2 相图使用 coarse matrix
- 边界讨论使用 refined 和 probability matrix
- 图中明确标注数据来源（coarse / refined / probability）

---

## M3. 三锚点分段迁移校准 (M3 Transfer)

### 目的
将 baseline configuration 下的可靠性阈值语义迁移到变体 configuration。

### 定义
给定 baseline 配置 $C_0$ 和变体配置 $C_1$：

1. 在 $C_0$ 中选取三个代表性格点作为锚点：
   - $A_{safe}$: 安全侧代表点
   - $A_{critical}$: 临界边界点
   - $A_{failure}$: 失效侧代表点
2. 在 $C_1$ 中找到对应格点的重标定 R 值
3. 构造分段线性/保序映射 $M_3: R_{C_0} \to R_{C_1}$ 使锚点对齐
4. 对 $C_1$ 中剩余格点，使用 $M_3$ 映射得到迁移后的 R 排序

### 有序保持约束
在 Burgers 中，基础 M3 可能破坏严重度排序。加入排序保持约束：
- 约束 $C_0$ 中的排序关系在 $C_1$ 中不被反转
- 若排名反转超过阈值，标记为排序退化

### 分段映射构造
$$M_3(r) = \begin{cases}
\text{线性}[r_{safe}, r_{critical}] & r \leq r_{critical} \\
\text{线性}[r_{critical}, r_{failure}] & r > r_{critical}
\end{cases}$$

### 使用状态
- Stokes-Poiseuille: M3 有明显改善
- Fisher-KPP: M3 可改善标签一致性
- Burgers: M3+排序保持约束可恢复排序稳定性，但 R 分区迁移仍偏弱

---

## M4. 结构稳定性 (Structural Stability) 案例级定义

### 框架级抽象定义
对于每个 PDE 案例，定义一个与其物理结构相关联的"结构特征" $S$，
结构稳定性得分为预测解与真实解在结构特征上的归一化距离。

### 案例级实例化

#### Burgers (1D unsteady, manufactured solution)
- 结构特征: 速度剖面 $u(x, t)$ 的归一化形状向量
- 距离度量: 1 - |cosine_similarity(pred_profile, true_profile)|
- 计算: 对 51×51 网格上的预测值和真值向量，计算余弦误差
- 公式: `structure_error = 1 - dot(pred, truth) / (norm(pred) * norm(truth))`

#### Stokes-Poiseuille (2D steady, analytic)
- 结构特征: u 流速分量的流向剖面
- 距离度量: cosine error on u-component
- 理由: v 分量理论值为 0，p 分量线性变化，结构信息主要集中在 u 的剖面形状

#### Fisher-KPP (1D unsteady, traveling wave)
- 结构特征: 行波剖面 $c(x, t)$ 的形状
- 距离度量: cosine error on concentration field

#### Poisson (2D steady, manufactured)
- 结构特征: 全域解的归一化形状
- 距离度量: cosine error on full field
- 注意: Poisson 没有实用失效边界，此维度区分度弱

### 与非点值误差的区别
- `rel_l2` 捕获的是逐点振幅误差
- `structure_error` 捕获的是解的形状/剖面保真度
- 两者可能不一致: 振幅准确但形状扭曲 (structure_error 大, rel_l2 小)
- 也可能振幅不准但形状保真 (structure_error 小, rel_l2 大)

---

## M5. 主导维度 (Dominant Dimension) 判定规则

### 定义
对于给定工况 (obs, noise)，计算四个重标定维度得分：
- $d_{physics}$ = geometric_mean(s_physics_rms, s_boundary_rms)
- $d_{training}$ = geometric_mean(s_loss_std, s_loss_ratio)
- $d_{numerical}$ = geometric_mean(s_rel_l2)
- $d_{structural}$ = geometric_mean(s_structure_error)

**主导维度**定义为得分最低的维度：
$$\text{DominantDim} = \arg\min_{d \in \{ph,tr,nu,st\}} d$$

### 聚合规则
- **维度内聚合** (同维度多个指标): 几何平均
- **维度间聚合** (得到综合 R): 算术平均
- **稳健性验证**: 已在 27 组"分位点×维度内聚合×维度间聚合"配置下验证

### 案例级主导维度分布 (来自重标定分析)

| 案例 | physics | training | numerical | structural |
|------|:---:|:---:|:---:|:---:|
| Poisson | 0 | 1 | 5 | 2 |
| Stokes-Poiseuille | 1 | 0 | 7 | 0 |
| Fisher-KPP | 2 | 5 | 5 | 1 |
| Burgers | 9 | 23 | 10 | 17 |

### 使用规则
- 主导维度确定"哪些维度首先失效"
- 用于引导训练干预的方向选择 (exploratory)
- 边界位置由综合 R 确定，主导维度用于解释边界语义

---

## 实现文件位置

| 组件 | 文件 |
|------|------|
| Logistic score | `minimal_pinn/reliability.py::logistic_score` |
| Recalibration | `minimal_pinn/recalibrate_dimensions.py` |
| Calibration configs | `minimal_pinn/configs/` |
| Probability matrix spec | `minimal_pinn/configs/*_probability_boundary_*.json` |
| Coarse matrices | `minimal_pinn/configs/matrix_coarse_*.json` |
| Refined matrices | `minimal_pinn/configs/matrix_refine_*.json` |
| M3 transfer analysis | `minimal_pinn/analyze_few_shot_transfer_calibration.py` |
| Structure error | `minimal_pinn/cases/*.py::structure_error` |
| Dominant dimension | `minimal_pinn/reliability.py::build_reliability_summary` (argmin over dim_scores) |

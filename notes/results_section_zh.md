# 实验结果与图表终稿

## 主实验主线

当前主实验不再按“展示若干结果图”的方式组织，而是按三个主假设与一个探索性外推问题组织。当前主文证据链由 `Poisson`、`Stokes-Poiseuille`、`Fisher-KPP` 与 `Burgers` 四个案例共同构成，其中四者分别承担稳健对照、规则耦合边界、前沿传播型规则边界带与复杂宽临界带的角色。

- `H1`：PINN 的可靠性边界在“观测稀疏度–噪声强度”二维空间中形成可分析结构。
- `H2`：单一误差不足以完整描述 PINN 失效，多维可靠性框架能够为边界识别、种子敏感性解释与局部边界任务提供额外信息。
- `H3`：可靠性边界和失效语义具有系统依赖性。
- `E1`：可靠性分析得到的失效机制线索，是否能够为训练干预提供有用但当前仍属初步的设计信息。

因此，主文结果的角色分别是：

- 图 1、图 2：对应 `H1`
- 图 3、图 4、图 5：对应 `H2` 和 `H3`
- 图 6：对应探索性外推 `E1`

统计证据的组织也同步收束为“两条主证据链 + 若干 supporting evidence”。主证据链只回答两件事：

1. `Burgers` 的边界是否具有统计宽度，而不是单切点。
2. `Burgers` 的临界带是否比 `Stokes-Poiseuille` 与 `Fisher-KPP` 更具多维异质性。

其余统计结果，例如外生标签预测、Top-k 排序错位和部分配对检验，统一降级为 supporting evidence，用于补强 `R` 的合法性与语义解释，但不再与主统计证据并列。

## 统一 protocol 说明

主实验在统一最小 PINN protocol 下进行，除 PDE 本身所必需的残差和结构指标外，其余控制变量尽量不变：

- 网络：`3×64` 的 `tanh` MLP
- 优化器：`Adam`
- 初始学习率：`1e-3`
- 训练轮数：`500`
- 损失权重：`data=10, physics=1, boundary=10`
- clean baseline 采样预算：`num_observation=256`、`num_collocation=2048`、`num_boundary=256`
- 噪声注入：按观测真值标准差尺度叠加零均值高斯噪声

二维矩阵采用 full-factorial design：

- 因子 A：observation sparsity
- 因子 B：noise level
- 响应变量：`rel_l2`、四维可靠性指标、综合可靠性、失败率
- 控制变量：architecture、optimizer、training budget、sampling budget、PDE 外的统一 protocol

多 seed 不再是补充材料，而是 protocol 的一部分：

- clean baseline 用多 seed 统计；
- 疑似边界区追加多 seed；
- 主文尽量报告均值、标准差、失败率和 Wilson 区间。

需要额外说明的是，当前框架首先用于 benchmark 与 controlled setting 下的 reliability analysis，而不是现实部署时可直接在线调用的可信判别器。原因在于 `numerical_accuracy` 与 `structural_stability` 在主实验中依赖参考解，因此主文结论更准确的定位是“可靠性表征与分析框架”，而不是“在线可信判定器”。

## 主文图表编号

### 表 1. 跨 PINN 变体的代表点稳健性对照

来源：
- [point_summary.csv](/root/dev/pinn-reliability-paper/minimal_pinn/results/variant_robustness/variant_robustness_v4/point_summary.csv)

用途：
- 作为主文中 stronger-baseline 防守层的正式对照表。
- 对应正文第 10 节 `Transferability And Calibration`。

表注：
`表 1. 五种 PINN 配方在四案例代表点上的越界率对照。表中数值为对应代表点在 3 个随机种子下超过当前操作性 rel_l2 边界参考值的比例。baseline、capacity_v1、weight_balanced_v2、adaptive_rar_v1 与 loss_adaptive_uncertainty_v1 分别对应最小基线、更大容量、重平衡损失、经典残差自适应采样与标准 loss-adaptive weighting。该表用于说明不同变体会平移边界位置，但不会抹去四案例的核心语义角色。`

| Case | Representative point | baseline | capacity_v1 | weight_balanced_v2 | adaptive_rar_v1 | loss_adaptive_uncertainty_v1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Poisson | `safe_obs256_noise000` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| Poisson | `degraded_obs8_noise020` | 0.000 | 0.000 | 0.000 | 0.000 | 0.333 |
| Stokes-Poiseuille | `safe_obs64_noise000` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| Stokes-Poiseuille | `critical_obs8_noise0125` | 0.667 | 0.000 | 0.000 | 0.333 | 0.000 |
| Stokes-Poiseuille | `failure_obs8_noise0175` | 1.000 | 1.000 | 0.333 | 1.000 | 0.667 |
| Fisher-KPP | `safe_obs64_noise000` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| Fisher-KPP | `edge_obs16_noise005` | 0.667 | 0.000 | 0.333 | 0.667 | 0.333 |
| Fisher-KPP | `transition_obs128_noise020` | 0.667 | 0.667 | 0.667 | 0.667 | 0.000 |
| Fisher-KPP | `failure_obs16_noise030` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Burgers | `safe_obs64_noise005` | 0.333 | 0.667 | 0.333 | 1.000 | 0.667 |
| Burgers | `transition_obs48_noise010` | 0.667 | 1.000 | 0.000 | 0.667 | 1.000 |
| Burgers | `seed_sensitive_obs32_noise010` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Burgers | `failure_obs32_noise0175` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

### 图 1. 三案例相对误差相图

文件：
- [figure_01_rel_l2_phase_maps.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/paper_figures/v1/figure_01_rel_l2_phase_maps.png)

用途：
- 支撑四类 PDE 在相同观测退化条件下表现出不同边界形态。
- 对应正文第 6 节 `Reliability Phase Space Across PDEs`。

图注：
`图 1. Poisson、Stokes-Poiseuille 与 Burgers 的相对 L2 误差相图。Poisson 在当前扫描范围内保持稳健；Stokes-Poiseuille 仅在低观测和中高噪声角落显著退化；Burgers 则表现出更宽且更不规则的高风险区域。`

### 图 2. 三案例综合可靠性相图

文件：
- [figure_02_reliability_phase_maps.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/paper_figures/v1/figure_02_reliability_phase_maps.png)

用途：
- 展示综合可靠性与单一误差并不完全等价。
- 对应正文第 6 节整体相空间与第 7 节单指标不足的论证。

图注：
`图 2. 基于多维可靠性聚合得到的三案例综合可靠性相图。与相对 L2 误差相比，综合可靠性在边界附近保留了物理一致性、训练稳定性和结构稳定性信息，因此更适合刻画临界带。重标定后的 R 仅用于案例内语义分析；跨系统原始量纲对照见附录图 A7。`

### 图 3. 规则边界与复杂边界的语义对比

文件：
- [figure_03_regime_maps.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/paper_figures/v1/figure_03_regime_maps.png)

用途：
- 支撑 `Stokes-Poiseuille` 与 `Burgers` 在语义层上的分化。
- 对应正文第 8 节 `System-Dependent Boundary Semantics`。

图注：
`图 3. 规则边界与复杂边界的语义对比。该图基于细化矩阵与迁移实验中的经验关系绘制，用于概括 Stokes-Poiseuille 与 Burgers 的语义差异。Stokes-Poiseuille 仍可近似用三段硬分区描述；Burgers 的临界带则更适合写成排序、局部安全边界与失效侧邻接关系共同定义的多模态区间。`

### 图 4. Burgers 局部多 seed 概率边界

文件：
- [figure_14_cross_rate_heatmap.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/probability_matrices/burgers_probability_boundary_v2_5seed/figure_14_cross_rate_heatmap.png)

用途：
- 支撑 Burgers 边界是概率边界，而不是单条确定性分界线。
- 对应正文第 9 节 `Statistical Evidence Around Boundary Uncertainty`。

图注：
`图 4. Burgers 临界带附近的局部多 seed 概率边界图。颜色表示给定观测点数和噪声水平下的越界率，当前每个格点使用 5 个随机种子。随着噪声增大和观测减少，局部区域由稳定安全区逐步过渡到种子敏感区，再进入稳定失效区，说明 Burgers 的边界具有显著统计宽度。`

### 图 5. 重标定后的主导维度图

文件：
- [figure_10_burgers_recalibrated_dimension_maps.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/paper_figures/v1/figure_10_burgers_recalibrated_dimension_maps.png)
- [figure_11_stokes_recalibrated_dimension_maps.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/paper_figures/v1/figure_11_stokes_recalibrated_dimension_maps.png)

用途：
- 支撑不同 PDE 的主导失效机制不同。
- 对应正文第 7 节 `Why Single Error Is Insufficient`。

图注：
`图 5. 重标定后的主导维度图。Burgers 的边界由训练稳定性、结构稳定性与数值精度共同塑造，而 Stokes-Poiseuille 仍主要表现为数值精度主导的规则边界。这表明多维可靠性框架的价值具有明确的系统依赖性。`

### 图 6. 区域感知训练对比

文件：
- 主文建议根据 [strategy_summary.csv](/root/dev/pinn-reliability-paper/minimal_pinn/results/region_aware/region_aware_compare_v3_u3/strategy_summary.csv) 与 [effect_summary.csv](/root/dev/pinn-reliability-paper/minimal_pinn/results/region_aware/region_aware_compare_v3_u3/effect_summary.csv) 排版为条形图或点图

用途：
- 作为基于可靠性分析的探索性外推测试，而非主结果图。
- 对应正文第 11 节 `Exploratory Extension: Failure-Mechanism-Guided Intervention`。

图注：
`图 6. 扩展临界工况上的区域感知训练对比。每个系统选取两个临界工况、每个工况使用 5 个随机种子，并比较 baseline、naive region-aware v1、dim-guided v2 与 non-dominant-guided v3。结果显示，naive 干预并不可靠；Burgers 中部分策略可改善 rel_l2，但综合可靠性提升仍不稳；Stokes-Poiseuille 中 dim-guided v2 对综合可靠性表现出稳定负效应。因此，这一结果更适合支持探索性结论，而非通用训练规则。`

## 附录图表编号

### 图 A1. 代表性场可视化

文件：
- [figure_05_representative_fields.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/paper_figures/v1/figure_05_representative_fields.png)

用途：
- 补充展示可靠、临界与高风险工况下的场形态差异。

### 图 A2. Burgers 异常点多 seed 箱线图

文件：
- [figure_04_burgers_multiseed_boxplot.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/paper_figures/v1/figure_04_burgers_multiseed_boxplot.png)

用途：
- 补充说明局部异常点的种子敏感性。

### 图 A3. 校准敏感性

文件：
- [figure_12_calibration_sensitivity_counts.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/calibration_sensitivity_v1/figure_12_calibration_sensitivity_counts.png)
- [figure_33_role_stability.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/calibration_aggregation_robustness_v1/figure_33_role_stability.png)
- [figure_34_dominant_counts.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/calibration_aggregation_robustness_v1/figure_34_dominant_counts.png)

### 图 A4. 单指标对照与维度消融

文件：
- [figure_13_dimension_ablation.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/dimension_ablation_v1/figure_13_dimension_ablation.png)
- [figure_20_pca_explained_variance.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/single_vs_multi_v1/figure_20_pca_explained_variance.png)
- [figure_21_risk_separability.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/single_vs_multi_v1/figure_21_risk_separability.png)
- [figure_22_rel_l2_r2.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/single_vs_multi_v1/figure_22_rel_l2_r2.png)

### 图 A5. 阈值可移植性与少样本迁移校准

文件：
- [figure_23_rule_portability_spans.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/threshold_portability_v1/figure_23_rule_portability_spans.png)
- [figure_24_severity_ordering.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/threshold_portability_v1/figure_24_severity_ordering.png)
- [figure_25_transfer_label_agreement.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/few_shot_transfer_calibration_v1/figure_25_transfer_label_agreement.png)
- [figure_26_transfer_disagreement_reduction.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/few_shot_transfer_calibration_v1/figure_26_transfer_disagreement_reduction.png)
- [figure_27_transfer_ordering_rho.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/few_shot_transfer_calibration_v1/figure_27_transfer_ordering_rho.png)
- [figure_28_r_partition_accuracy.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/r_partition_transfer_v1/figure_28_r_partition_accuracy.png)
- [figure_29_r_partition_disagreement.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/r_partition_transfer_v1/figure_29_r_partition_disagreement.png)

### 图 A6. Burgers 临界带多模态与局部边界补充诊断

文件：
- [figure_30_burgers_critical_subtypes.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/critical_multimodality_v1/figure_30_burgers_critical_subtypes.png)
- [figure_31_local_boundary_accuracy.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/local_boundary_transfer_v1/figure_31_local_boundary_accuracy.png)
- [figure_32_local_boundary_disagreement.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/local_boundary_transfer_v1/figure_32_local_boundary_disagreement.png)

### 图 A7. 未校准原始指标的跨系统对照

文件：
- [figure_40_raw_metric_parallel_coordinates.png](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/raw_scale_cross_case_v1/figure_40_raw_metric_parallel_coordinates.png)
- [raw_metric_case_summary.csv](/root/dev/pinn-reliability-paper/minimal_pinn/results/analysis/raw_scale_cross_case_v1/raw_metric_case_summary.csv)

用途：
- 说明案例内分位数重标定不应用于跨系统绝对严重度比较。
- 用未校准原始量纲直接展示三个系统的六个基础指标尺度差异。

## 正文结果段落的图号对应

- 第 6 节 `Reliability Phase Space Across PDEs`：图 1、图 2
- 第 7 节 `Why Single Error Is Insufficient`：图 5
- 第 8 节 `System-Dependent Boundary Semantics`：图 3、附录图 A6
- 第 9 节 `Statistical Evidence Around Boundary Uncertainty`：图 4
- 第 11 节 `Failure-Mechanism-Guided Intervention`：图 6
- 代表性场和补充统计图：附录图 A1-A7

## 正文结果表达终稿

### 6.1 Reliability Phase Space Across PDEs

本文首先在观测点数与噪声水平构成的二维参数空间中，对四个 PDE 系统进行了统一扫描。粗矩阵采用观测点数 `256, 128, 64, 32, 16, 8` 与噪声水平 `0, 0.05, 0.10, 0.15, 0.20` 的全因子组合，并在 `Burgers` 与 `Stokes-Poiseuille` 的边界附近进一步进行了局部细化。如图 1 和图 2 所示，不同物理系统在相同观测退化条件下表现出显著不同的可靠性边界形态。`Poisson` 在当前扫描范围内保持高度稳定；`Stokes-Poiseuille` 仅在极低观测与中高噪声角落出现明显退化；`Fisher-KPP` 显示出具有传播前沿但总体仍较规则的噪声驱动边界带；`Burgers` 则表现出更宽、更复杂的临界带与失效区。该结果支持 `H1`：边界不是单点现象，而是二维空间中的结构化对象。

### 6.2 Poisson：稳健对照案例

在 `Poisson` 案例中，clean baseline 在 `5` 个随机种子下的 `rel_l2` 为 `0.0965 ± 0.0050`。按当前最小基线下的 `1.5x` 相对退化因子定位边界时，对应参考值约为 `0.1448`。在当前粗矩阵测试范围内，最大误差仅达到 `0.1186`；即使在更激进的扩展搜索中将观测压缩到 `2` 个点并将噪声提高到 `120%`，最差误差也仅约为 `0.1430`，仍未稳定跨过该参考值。这说明在当前最小 PINN 设置下，`Poisson` 对观测稀疏与噪声扰动高度稳健。因此，`Poisson` 更适合作为稳健对照案例，而不是主边界案例。

### 6.3 Stokes-Poiseuille：窄而规整的边界

在 `Stokes-Poiseuille` 案例中，clean baseline 在 `5` 个随机种子下的 `rel_l2` 为 `0.0103 ± 0.0026`，边界参考值约为 `0.0154`。细化结果显示，系统在大部分观测条件下保持稳定，仅在极低观测与中高噪声区域出现越界。当 `noise=0.125` 时，`obs=8` 与 `obs=6` 已经跨过参考值；当 `noise>=0.15` 时，这两个观测层级稳定处于高风险区，而 `obs=10` 与 `obs=12` 多位于临界带附近但尚未显著越界。结合图 3 和图 5，可见该系统的边界集中、狭窄且较为规则，其主导失效模式仍以数值精度为主。

### 6.4 Burgers：宽边界与局部不稳定窗口

在 `Burgers` 案例中，clean baseline 在 `5` 个随机种子下的 `rel_l2` 为 `0.0178 ± 0.0097`，对应参考值约为 `0.0267`。与 `Stokes-Poiseuille` 不同，`Burgers` 展现出更宽、更复杂的边界结构。总体上，当 `noise>=0.125` 且 `obs<=24` 时，系统大多进入高风险区；`obs=32-40` 构成主要临界带；而 `obs>=64` 在低噪声下通常保持稳定，但在 `noise=0.15` 附近已经可能发生持续退化。更重要的是，`Burgers` 的二维矩阵并不呈现简单单调退化，而是出现局部异常升高，提示其边界同时受观测退化与训练随机性影响。

### 6.5 Fisher-KPP：前沿传播型的规则边界带

`Fisher-KPP` 用于检验“具有传播前沿的反应-扩散 PDE 是否都会演化出 `Burgers` 式宽临界带”。在统一粗矩阵 protocol 下，其 clean baseline 为 `rel_l2 = 0.0126`，对应当前 `1.5x` 操作性边界参考值约为 `0.0189`。粗矩阵中的首次越界点出现在 `obs=8, noise=0.05`，`rel_l2 = 0.0221`；当噪声提高到 `0.10` 时，`obs=32/16/8` 已分别上升到 `0.0226/0.0394/0.0311`；当噪声达到 `0.20` 与 `0.30` 时，边界带进一步向更高观测侧扩张，例如 `noise=0.20` 下 `obs=128/32/16/8` 的误差约为 `0.0223/0.0462/0.0764/0.0546`，`noise=0.30` 下则约为 `0.0309/0.0714/0.1131/0.0895`。

与旧的温和 `advection-diffusion` 不同，`Fisher-KPP` 确实形成了比 `Poisson` 更清晰的边界带；但它又没有演化成 `Burgers` 式宽而异质的复杂临界区。对 `8` 个关键边界点进行 `10-seed` 复核后，可见 failure rate 呈现出较规则的梯度：从安全点 `0.00`，逐步过渡到 `0.30`、`0.50-0.60`，再进入 `0.90` 与 `1.00` 的稳定失效侧。跨点严重度排序的逐 seed Spearman 相关系数均值约为 `0.879 (rel_l2)` 与 `0.931 (R)`，说明其边界虽然具有中等统计宽度，但整体排序结构较稳。因此，`Fisher-KPP` 更适合被表述为“前沿传播型、噪声驱动、总体规则但具有中等统计宽度的边界带”。这一结果进一步加厚了 `H3`：系统依赖性不能简化为“是否含传播项”，因为即便存在显著前沿传播，边界语义也未必会演化成 `Burgers` 那样的多模态复杂临界带。

### 7. Why Single Error Is Insufficient

重标定后的结果表明，不同案例的维度主导模式出现了明确分化。结合图 5，`Burgers` 的越界区域不再被单一物理一致性主导，而是分别分布在训练稳定性、结构稳定性、数值精度与物理一致性上，其中训练稳定性与结构稳定性占据主要比例。相比之下，`Stokes-Poiseuille` 在重标定后仍主要由数值精度维度主导，仅有少量工况表现出物理一致性主导。`Poisson` 则主要表现为轻微退化在不同维度上的相对敏感性，而非明确的失效机制。`Fisher-KPP` 则处于两者之间：在当前 `13` 个越界点中，其主导维度分布为 `training/numerical/physics/structural = 5/5/2/1`，表面上看似也有多维参与；但进一步的统计结果显示，这种“多维参与”并不像 `Burgers` 那样对应真正的语义异质性，而更接近沿同一退化主轴的同步下降。

进一步的单维与多维统计检验表明，当前四维得分空间并未塌缩成单一误差轴，但不同系统的塌缩程度不同。`Poisson`、`Stokes-Poiseuille`、`Burgers` 与 `Fisher-KPP` 的第一主成分解释率分别为 `0.5639`、`0.6340`、`0.7138` 与 `0.9087`；以“低综合可靠性”作为内部一致性目标时，四维表示相对于单一 `rel_l2` 的可分性增益分别为 `+0.1307`、`+0.0595`、`+0.0083` 与 `+0.0227`；同时，`Burgers` 中 `training_stability` 对 `rel_l2` 的线性解释度仅为 `R^2 = 0.0574`，而 `Fisher-KPP` 对应值约为 `0.5002`。这说明 `Fisher-KPP` 虽然也会出现训练稳定性参与退化，但它并没有发展出 `Burgers` 式强非冗余的多维失效结构。

补充的 `Top-k` 排序错位分析显示，多维框架的价值不在于彻底改写最差工况集合，而在于改变差集工况的语义解释。在 `Top-20` 层级，`rel_l2` 与重标定 `R` 的最差工况集合 Jaccard 在 `Stokes-Poiseuille`、`Fisher-KPP` 与 `Burgers` 中分别约为 `0.667`、`0.818` 与 `0.818`。但三者的含义并不相同：对 `Burgers` 而言，被 `R` 单独识别出的工况具有明显更低的 `training_stability`（约 `0.124`）和较低的 `structural_stability`，而被 `rel_l2` 单独识别出的工况相应值约为 `0.861` 与 `0.666`；对 `Fisher-KPP` 而言，`R-only` 工况的训练稳定性虽也偏低（约 `0.885` vs `0.944`），但整体仍靠近高可靠区域，没有演化成新的独立高风险语义簇。此外，联合失效分析表明，`Burgers` 的复杂性并不主要表现为大量点同时跌破同一固定阈值；更有信息量的现象是，约 `18/59` 个越界点在前两弱维度上的分差不超过 `0.05`，说明临界带中确实存在一部分近并列退化，而不是单一瓶颈。因此，多维可靠性框架并不是简单用多个指标重复表达单一误差，而是在复杂系统中提前暴露了“误差尚可但训练/结构已恶化”的预警信号；`Fisher-KPP` 则进一步说明，多维框架也可以用于辨认“维度同时参与，但总体仍接近单轴规则退化”的中间型案例。

为了避免“用自己的分数证明自己有用”的自指风险，本文进一步补做了一个外生标签预测实验。这里不再用 `R` 或维度分数定义标签，而是直接使用多 seed 结果给出的点级外生标签：`high_failure` 定义为 `cross_rate >= 0.5`，`seed_sensitive` 定义为 `0 < cross_rate < 1`。在 `39` 个跨案例点级样本上，使用同一 LOOCV 最近质心分类器，仅改变输入表示。结果显示：在 `high_failure` 任务上，单一 `rel_l2` 的准确率仅为 `0.513`，而多维聚合后的 `R` 与完整四维状态分别达到 `0.692` 与 `0.667`，对应 balanced accuracy 从 `0.518` 提升到 `0.688` 与 `0.662`；但精确 McNemar 检验的 `p` 值仍分别为 `0.281` 与 `0.377`，说明当前证据更适合写成“中等强度的外生支持”，而不是已经统计确证。与此同时，在更细粒度的 `seed_sensitive` 任务上，`rel_l2` 的 balanced accuracy 约为 `0.786`，反而高于 `R/4D` 的 `0.641`。因此，更稳的结论是：多维框架确实有助于预测跨 seed 的高失败风险，但对“种子敏感而非必然失效”的中间态，仍需要概率边界与局部多 seed 分析来补足。

如果进一步把问题收紧为“`R` 是否只是 `rel_l2` 的重新包装”，现有结果更适合被理解为一个三层防守，而不是一个单一漂亮数字。第一层是统计非冗余性：在 `Burgers` 中，`training_stability` 对 `rel_l2` 的线性解释度仅为 `R^2=0.0574`；在 `Stokes-Poiseuille` 中，`structural_stability` 的对应值也只有 `0.0594`。第二层是差集工况语义：`Burgers` 中被 full `R` 单独识别的差集工况，其平均 `training_stability_recal` 和 `structural_stability_recal` 仅约为 `0.328` 与 `0.414`，明显低于 `rel_l2-only` 差集工况的 `0.861` 与 `0.666`。第三层是维度消融：`Burgers` 中去掉任一单维度后，与 full `R` 的 worst-set 重合度仍在 `0.778-0.882` 之间，说明其高风险语义不是由某一个维度独占决定。因而，当前更稳的表述不是“这四个维度已经被唯一证明”，而是：在当前 protocol 下，它们组成了一个足以脱离“单一误差换壳”解释的最小可工作分解。

### 8. System-Dependent Boundary Semantics

跨案例比较表明，规则边界并不只出现在 `Stokes-Poiseuille` 中，但“规则”也并不等于“完全无统计宽度”。`Fisher-KPP` 的粗矩阵与关键点 `10-seed` 结果显示，其边界总体仍保持单调、有序的前沿传播退化路径，但在高噪声边界带上保留了中等统计宽度。这说明系统依赖性的更稳解释不是简单的“有无传播项”，而是传播性、非线性和局部结构复杂度的组合差异：`Stokes-Poiseuille` 更接近窄而近确定性的规则边界，`Fisher-KPP` 更接近具有前沿传播特征、但仍可排序解释的规则边界带，而 `Burgers` 则进一步发展为宽临界带、局部不规则和语义异质并存的复杂边界。

跨变体迁移结果则进一步表明，`Stokes-Poiseuille` 与 `Burgers` 虽然都可以使用同一套连续迁移层 `M3`，但其语义层并不相同。对 `Stokes-Poiseuille` 而言，`M3` 配合三段硬分区仍然成立，说明该系统的边界近似一维且单调。对 `Burgers` 而言，全局三分类切分在跨变体时无法稳定恢复点级语义。结合图 3 与附录图 A6 可见，当前被统称为 `critical` 的区域很可能是异质的，并至少包含靠近安全边界的 `transition` 型临界点，以及更接近失效边界的 `seed-sensitive` 型不稳定点。进一步的 pooled exact permutation tests 给出了更正式的统计支持：`transferred_rel_l2` 的均值差约为 `0.0467`，`p=0.011`，`d=0.93`；`structural_stability_recal` 的均值差约为 `-0.1727`，`p=0.013`，`d=-0.83`；`transferred_R` 的差异呈边缘显著，`p=0.081`；而四维 `z` 分数空间中的质心距离 exact `p` 值约为 `0.056`。这说明当前证据已经足以拒绝“critical 是单一同质团簇”的简单写法，但仍不足以把它写成完全线性可分的两类。因此，`Burgers` 的主结果应表述为严重度排序、局部安全边界与失效侧邻接关系，而不应继续写成统一三分类恢复问题。更谨慎地说，局部安全边界任务在 transfer 变体上的平均准确率约为 `0.75`，高于全局三分类基线的 `0.583`，这更适合作为“局部语义更易迁移”的初步证据，而不是已经完成的大规模迁移验证。

`Fisher-KPP` 的迁移结果则处在 `Stokes-Poiseuille` 与 `Burgers` 之间，更接近前者。阈值可移植性分析显示，其跨变体固定阈值越界率跨度约为 `0.167`，明显低于 `Stokes-Poiseuille` 的 `0.444` 与 `Burgers` 的 `0.333`；同时 `R<0.7` 的失效侧跨度为 `0.0`，说明深失效点在变体间相对稳定。少样本迁移校准中，`Fisher-KPP` 的严重度排序在各变体上均保持 `rho = 1.0`，而 `M3/M4` 的平均评估点 `rel_l2` 标签准确率约为 `0.875`，明显高于其原始 `M0` 的 `0.75`。但它又没有像 `Stokes-Poiseuille` 那样形成更刚性的 `R` 语义，因为各方法下 `R` 标签分歧比例仍约为 `0.5`。因此，`Fisher-KPP` 更适合被视为“连续严重度和边界顺序可稳定迁移，但硬语义标签刚性低于 `Stokes`”的中间层案例。

### 9. Statistical Evidence Around Boundary Uncertainty

为将 `Burgers` 的局部异常提升为统计意义上的边界证据，本文在临界带附近构造了一个局部多 seed 概率矩阵，并将每个格点提升到 `5` 个随机种子。如图 4 所示，在 `sigma=0.05` 时，越界率已经由高观测侧的 `0.4` 逐步过渡到低观测侧的 `0.8`；在 `sigma=0.10` 时，这一过渡带进一步向高观测预算扩展；当 `sigma>=0.15` 时，局部矩阵内大部分格点已进入接近稳定失效的区域。对应的 `95%` Wilson 区间相较于 `3 seed` 情况已有所收紧，但关键过渡格点的区间仍然偏宽，例如 `0.4` 和 `0.6` 的区间分别约为 `[0.118, 0.769]` 与 `[0.231, 0.882]`，`0.8` 的区间约为 `[0.376, 0.964]`。因此，这一结果更适合作为“概率边界的统计证据”，而不是精确概率估计。

在此基础上，本文进一步对 `8` 个关键边界点进行了 `10-seed` 高密度复现，以加厚主文最核心的统计证据。结果显示，相对安全侧点的 failure rate 约为 `0.40`，对应 `95%` Wilson 区间约为 `[0.168, 0.687]`；过渡点的 failure rate 提高到 `0.70` 与 `0.90`；稳定失效点则达到 `1.00`，其区间下界约为 `0.722`。同时，跨点严重度排序的逐 seed Spearman 相关系数均值约为 `0.740 (rel_l2)` 与 `0.745 (R)`，说明边界附近不仅 failure probability 具有统计宽度，跨点严重度排序本身也具有中等偏强的稳定性。与之相对，主导维度的点级众数占比仅为 `0.4–0.7`，提示边界附近的主导机制分布本身也具有显著波动。因此，当前更稳的结论是：`Burgers` 的边界更接近具有统计宽度和机制混合性的过渡带，而不是单一切点。

### 10. Transferability And Calibration

当前结果表明，固定绝对阈值并不具有跨变体可移植性，因此 `1.5x baseline` 只应被理解为当前 protocol 下的操作性边界参考值，而不是理论边界。相对而言，更稳的可迁移对象是排序、边界形态和主导失效机制。基于这一观察，本文将连续迁移层与语义分区层解耦：连续层采用带排序保持约束的 `M3` 迁移，以尽量保住严重度结构；语义层则根据系统本身的边界几何分别处理。`Stokes-Poiseuille` 仍可采用三段硬分区，而 `Burgers` 更适合退回到排序、局部边界与临界带内部机制解释。

新增的 `Fisher-KPP` 迁移结果使这一分层口径更完整。对 `Fisher-KPP` 而言，`M3/M4` 在 transfer 变体上的平均评估点 `rel_l2` 标签准确率约为 `0.875`，严重度排序 `rho` 保持在 `1.0`，说明连续层的排序保持迁移是有效的；但其 `R` 标签准确率仍约为 `0.75`，且跨变体 `R` 标签分歧比例约为 `0.5`，说明这一案例虽然处在规则边界一侧，却仍不宜被表述成与 `Stokes-Poiseuille` 完全同质的“硬语义完全可移植”系统。换言之，`Fisher-KPP` 补上了一个重要中间层：边界次序和失效深浅可以稳定迁移，但语义标签刚性不足以支持过强的硬分区主张。

补充的校准与聚合稳健性实验进一步表明，当前主结论并不是某一组分位点或某一类维度间平均方式“做出来”的，但这并不等于四案例在任意校准下都同样稳定。具体而言，`Poisson` 与 `Burgers` 的角色在 `27/27` 组配置下保持成立，`Stokes-Poiseuille` 与 `Fisher-KPP` 则分别在 `18/27` 与 `15/27` 组配置下保持成立；四案例同时成立的配置共有 `9/27` 组，主要集中于 `Q0.15/Q0.85` 和 `Q0.20/Q0.80` 下的几何平均方案。最容易打破 `Stokes-Poiseuille` 语义的是维度内 `minimum` 聚合，而 `Fisher-KPP` 的漂移则主要集中在最激进的 `Q0.10/Q0.90` 与 `Q0.20/Q0.80 + arithmetic` 设定下。换言之，当前结论对中等强度的校准与常规聚合方式相对稳健，但对“最小值聚合”或过度拉伸尾部这类强保守规则更敏感，因此主文将当前聚合方案写成 operational design choice，而不写成唯一正确形式。需要进一步强调的是，重标定后的 `R` 只用于案例内排序、主导维度识别与局部边界任务，而不用于跨案例绝对严重度比较。附录图 A7 直接展示了核心系统在未校准原始基础指标上的绝对尺度差异，这一图用于提醒读者：主文中的重标定色彩图是案例内语义图，而不是跨系统可直接比较的热力图。

补充的 `protocol sufficiency control` 说明，统一最小 budget 确实会影响边界的绝对位置，但不会把三类系统压成同一种边界语义。在将代表点 budget 提升到 `1000 epochs + 4096 collocation + 512 boundary` 后，`Poisson` 的两个代表点都进一步远离操作性边界；`Stokes-Poiseuille` 的高风险点则表现为位置后移而不是语义消失，例如 `failure_obs8_noise020` 的平均 `rel_l2` 从 `0.0253` 升到 `0.0374`，failure rate 从 `0.00` 升到 `0.33`，说明这些点仍然位于边界带附近而非被简单“洗平”；`Burgers` 中 `transition_obs48_noise005` 与 `failure_obs64_noise015` 的平均 `rel_l2` 分别下降约 `0.0092` 与 `0.0139`，failure rate 也下降了 `0.33` 与 `0.67`，显示更强 budget 可以缓解部分关键点的失效严重度，但 `seed_sensitive_obs32_noise010` 的 failure rate 仍维持在 `0.67`。因此，当前更稳的解释是：budget 会移动边界位置，并可能降低部分关键点从“高概率失败”到“中等概率失败”的程度，但 `Stokes` 的规则边界与 `Burgers` 的宽临界带/seed sensitivity 并非统一最小 protocol 的简单产物。

除 budget control 外，当前稿件还需要一层更明确的 stronger-baseline 防守。表 1 将 `baseline / capacity_v1 / weight_balanced_v2 / adaptive_rar_v1 / loss_adaptive_uncertainty_v1` 五种配方下的代表点越界率并列起来。该表显示：`Poisson` 的安全点在五种变体下始终保持安全，但其退化点在 `loss_adaptive_uncertainty_v1` 下会升到 `cross_rate=0.333`，说明标准 loss-adaptive weighting 也并非无条件增强；`Stokes-Poiseuille` 的 `critical` 点与 `failure` 点在更强容量、重平衡损失和标准自适应权重下会后移，但失效侧并未消失；`Fisher-KPP` 的过渡点在 `loss_adaptive_uncertainty_v1` 下可被压缩到 `cross_rate=0`，而深失效点始终保持 `1.0`，说明它更接近“规则但可被标准自适应权重压缩”的边界带；`Burgers` 的 `seed_sensitive` 与深失效点在五种变体下始终保持 `cross_rate=1.0`，而 `adaptive_rar_v1` 与 `loss_adaptive_uncertainty_v1` 还会分别把 nominally safe 或 transition 点推向更高风险侧。这说明无论是经典残差自适应采样，还是更标准的 SA-PINNs/uncertainty 风格 loss-adaptive weighting，都只是在移动边界位置，而没有把 `Burgers` 的宽临界带“修平”。因此，当前更稳的防守口径不是“结论对任意 PINN 都成立”，而是：在 modest stronger baselines、一个经典 adaptive baseline 和一个标准 loss-adaptive baseline 下，边界绝对位置会移动，但四案例的核心语义角色并不只是当前最小骨架的单次 artifact。

### 11. Exploratory Extension: Failure-Mechanism-Guided Intervention

区域感知训练结果如图 6 所示。这一部分不再与 `H1-H3` 并列，而被明确视为基于可靠性分析的探索性外推测试。扩展后的 `U3` 实验在 `Burgers` 与 `Stokes-Poiseuille` 上各取两个临界工况、每个工况 `5` 个随机种子，并加入“非主导维度定向干预”对照。配对 bootstrap 结果表明，当前最稳的结论是：朴素 `region-aware v1` 并不可靠，而“对准主导失效维度”也尚未形成稳定可复现的充分条件。在 `Burgers/transition_obs48_noise005` 上，`naive region-aware v1` 的 `rel_l2` 增量为 `+0.0153`，`95%` 区间为 `[0.0008, 0.0295]`，显示其误差恶化具有统计支持；但在同一工况上，`dim-guided v2` 的 `rel_l2` 和 `reliability_raw_recal` 区间都跨 `0`。在 `Burgers/seed_sensitive_obs32_noise010` 上，`non-dominant-guided v3` 的 `rel_l2` 改变量为 `-0.0193`，区间为 `[-0.0486, -0.0027]`，而其综合可靠性提升区间仍跨 `0`。对 `Stokes-Poiseuille` 而言，`dim-guided v2` 在两个工况上都表现出显著的综合可靠性下降，而 `non-dominant-guided v3` 仅在单个工况上带来轻微的误差改善。因而，当前更稳的表述是：可靠性相空间确实能够为干预设计提供线索，但训练增强的收益具有明显的系统依赖性和工况依赖性，尚不能被简单归因于“主导失效维度对准”本身，也不应被写成本文的主结果。

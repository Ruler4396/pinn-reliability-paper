# Minimal PINN — 文件索引

## 核心库 (Core)
| 文件 | 功能 |
|------|------|
| `config.py` | 配置加载、默认值补全 |
| `network.py` | MLP 网络 (3x64 tanh) |
| `reliability.py` | 可靠性评分：logistic 映射 + 四维度聚合 |
| `trainer.py` | 训练循环：PINN 损失 + 评估 |
| `matrix_specs.py` | 矩阵实验配置构建 |
| `recalibrate_dimensions.py` | 案例内分位数重标定 |

## 案例实现 (Cases)
| 文件 | PDE |
|------|-----|
| `cases/base.py` | 基类：采样、真值、误差 |
| `cases/poisson.py` | Poisson (sin·sin forcing) |
| `cases/stokes_poiseuille.py` | Stokes-Poiseuille (analytic) |
| `cases/burgers.py` | Burgers (manufactured solution) |
| `cases/fisher_kpp.py` | Fisher-KPP (traveling wave) |
| `cases/helmholtz.py` | Helmholtz (high-frequency) |
| `cases/advection_diffusion.py` | Advection-Diffusion |
| `cases/advection_dominated_diffusion.py` | Advection-Dominated (ε=0.005) |
| `cases/variable_coefficient_diffusion.py` | Variable Coefficient Diffusion |
| `cases/lid_driven_cavity.py` | Lid-Driven Cavity (Re=100) |

## 实验运行脚本 (Runners)
| 文件 | 功能 |
|------|------|
| `run_experiment.py` | 单次实验运行 |
| `run_matrix.py` | 2D 全因子矩阵扫描 |
| `run_multiseed_baselines.py` | 多种子基线建立 |
| `run_multiseed_probe.py` | 多种子边界关键点探针 |
| `run_multiseed_boundary_matrix.py` | 多种子概率边界矩阵 |
| `run_variant_robustness.py` | 变体鲁棒性实验 |
| `run_region_aware_compare.py` | 区域感知训练对比 |
| `run_budget_control.py` | 训练预算控制 |
| `run_protocol_sweep.py` | 协议扫描 (Helmholtz) |
| `sweep_boundary.py` | 边界搜索工具 |
| `run_stokes_probability_resume.py` | Stokes 概率矩阵续传 |
| `run_fisher_probability_resume.py` | Fisher-KPP 概率矩阵续传 |

## 分析脚本 (Analysis) — 主证据链
| 文件 | 分析的假设/问题 |
|------|----------------|
| `analyze_matrix.py` | H1: 相图可视化、regime 分类 |
| `analyze_boundary.py` | H1: 单 seed 边界分析 |
| `analyze_boundary_keypoint_probe.py` | H1+H3: 多 seed 边界点探针、Wilson CI |
| `analyze_boundary_comparison.py` | H3: 三系统概率边界定量对比 ⭐ 新增 |
| `analyze_probability_boundary_ci.py` | H1+H3: 概率边界 CI |
| `analyze_dimension_ablation.py` | H2: 维度消融、单指标对照 |
| `analyze_dimension_ablation_v2.py` | H2: 4D/3D/2D/1D 消融对比 ⭐ 新增 |
| `analyze_single_vs_multi.py` | H2: 单维 vs 多维统计检验 |
| `analyze_divergence_morphology.py` | H2: R vs rel_l2 差集工况可视化 ⭐ 新增 |
| `analyze_anti_circularity.py` | U5: 反循环校准 ⭐ 新增 |
| `analyze_clean_baseline_failure.py` | E3: 干净基线失败率分析 ⭐ 新增 |

## 分析脚本 (Analysis) — 补充证据
| 文件 | 分析的假设/问题 |
|------|----------------|
| `analyze_calibration_sensitivity.py` | U1: 分位数敏感性 |
| `analyze_calibration_aggregation_robustness.py` | U1: 聚合方式稳健性 |
| `analyze_indicator_validity.py` | R2: 指标效度：相关性与失效模式 |
| `analyze_critical_multimodality.py` | H3: Burgers 临界带多模态检验 |
| `analyze_external_target_prediction.py` | R2: 外生标签预测 (H2 外部验证) |
| `analyze_few_shot_transfer_calibration.py` | 少样本迁移校准 (M3) |
| `analyze_threshold_portability.py` | 阈值可移植性 |
| `analyze_topk_ranking_misalignment.py` | R1: Top-k 排序错位 |
| `analyze_r_partition_transfer.py` | R 分区迁移 |
| `analyze_local_boundary_transfer.py` | 局部边界迁移 |
| `analyze_raw_scale_cross_case.py` | R2: 原始尺度跨系统对照 |
| `analyze_joint_failure_and_train_proxy.py` | 联合失效与训练代理 |
| `analyze_region_aware_effects.py` | H4: 区域感知干预效应量 |
| `analyze_review_strengthening.py` | 审稿强化分析 |
| `analyze_budget_control.py` | U4: 训练预算控制分析 |

## 论文图表
| 文件 | 功能 |
|------|------|
| `plot_paper_figures.py` | 旧版论文图生成 |
| `plot_paper_figures_v2.py` | 新版统一图生成 ⭐ |

## 辅助
| 文件 | 功能 |
|------|------|
| `prepare_variant_robustness_v{2,3,4}.py` | 变体实验准备 |
| `run_*_background.sh` | 后台运行脚本 (Linux) |

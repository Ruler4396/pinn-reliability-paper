# 综合退化机制分析报告

## 概述

本分析通过5个阶段验证退化原型和四因素理论。

---

## Phase 1: 原型与指标一致性检查

### 各原型统计

| 原型 | boundary_width | transition_width | seedCV | prob_band_area |
|------|---------------|------------------|--------|----------------|
| Non-Degrading | 1.33±0.00 | 0.500±0.000 | 0.0085±0.0000 | 0.500±0.000 |
| Sharp Boundary | 3.67±0.00 | 0.375±0.000 | 0.0065±0.0000 | 0.375±0.000 |
| Broad Band | 5.44±2.03 | 0.214±0.173 | 0.0456±0.0286 | 0.214±0.173 |
| Intermediate | 5.13±0.00 | 0.375±0.000 | 0.0092±0.0000 | 0.375±0.000 |

### 排序一致性 (Spearman)

| 指标 | r | p | 显著性 |
|------|---|---|--------|
| boundary_width | 1.000 | 0.000 | *** |
| transition_width | -0.949 | 0.051 | * |
| seed_cv | 0.800 | 0.200 | ns |
| irregularity | 0.400 | 0.600 | ns |
| prob_band_area | -0.949 | 0.051 | * |
| mean_entropy | -0.800 | 0.200 | ns |
| max_entropy | -0.400 | 0.600 | ns |
| entropy_area | -0.800 | 0.200 | ns |

---

## Phase 2: 概率带指标

| PDE | 原型 | prob_band_area | mean_entropy | max_entropy | entropy_area |
|-----|------|---------------|-------------|-------------|--------------|
| Poisson | Non-Degrading | 0.500 | 0.3962 | 0.6572 | 0.3962 |
| Stokes-Poiseuille | Sharp Boundary | 0.375 | 0.4428 | 0.6931 | 0.4428 |
| Allen-Cahn | Broad Band | 0.500 | 0.3163 | 0.6730 | 0.3163 |
| Fisher-KPP | Intermediate | 0.375 | 0.3414 | 0.6909 | 0.3414 |
| Burgers | Broad Band | 0.375 | 0.3969 | 0.5799 | 0.3969 |
| Heat Equation | Broad Band | 0.250 | 0.3586 | 0.6909 | 0.3586 |
| KdV Soliton | Broad Band | 0.125 | 0.2060 | 0.6730 | 0.2060 |
| NLS Soliton | Broad Band | 0.250 | 0.2091 | 0.6909 | 0.2091 |
| Wave Equation | Broad Band | 0.000 | 0.1371 | 0.5004 | 0.1371 |
| KdV Double | Broad Band | 0.000 | 0.0000 | 0.0000 | 0.0000 |

---

## Phase 3: 因素→行为相关矩阵

| 相关性 | Spearman r | 95% CI | p | 显著性 |
|--------|-----------|--------|---|--------|
| d_null <-> prob_band_area | -0.087 | [-0.815, 0.678] | 0.812 | ns |
| lambda <-> transition_sharpness | -0.279 | [-0.943, 0.520] | 0.436 | ns |
| entropy <-> mean_failure_entropy | 0.539 | [-0.200, 0.958] | 0.108 | ns |
| basin <-> prob_band_area | 0.508 | [0.119, 0.891] | 0.134 | ns |
| infoCV <-> irregularity | 0.062 | [-0.595, 0.859] | 0.866 | ns |
| d_null <-> boundary_width | 0.188 | [-0.538, 0.882] | 0.603 | ns |
| d_null <-> mean_failure_entropy | -0.273 | [-0.857, 0.459] | 0.446 | ns |
| infoCV <-> prob_band_area | -0.303 | [-0.920, 0.461] | 0.394 | ns |

---

## Phase 4: VIF和PCA

### VIF

| Factor | VIF | 状态 |
|--------|-----|------|
| d_null | 8.31 | 严重共线 |
| lambda_max | 3.27 | 中度共线 |
| hessian_entropy | 12.82 | 严重共线 |
| basin_count | 3.61 | 中度共线 |
| info_cv | 2.46 | 可接受 |

### PCA

| PC | 特征值 | 解释率 | 累积解释率 |
|----|--------|--------|-----------|
| PC1 | 2.998 | 0.540 | 0.540 |
| PC2 | 1.458 | 0.262 | 0.802 |
| PC3 | 0.723 | 0.130 | 0.932 |
| PC4 | 0.331 | 0.060 | 0.992 |
| PC5 | 0.045 | 0.008 | 1.000 |

### Loading Matrix

| Factor | PC1 | PC2 |
|--------|-----|-----|
| d_null | 0.530 | -0.027 |
| lambda_max | 0.023 | -0.795 |
| hessian_entropy | -0.583 | 0.107 |
| basin_count | -0.312 | -0.575 |
| info_cv | 0.531 | -0.159 |

---

## Phase 5: Model Comparison

| Model | R² | Adj R² | AIC | BIC | LOOCV R² |
|-------|-----|--------|-----|-----|----------|
| A (4因素) | 0.425 | -0.036 | -30.4 | -28.9 | -2.511 |
| B (3因素) | 0.411 | 0.116 | -32.2 | -30.9 | -2.361 |
| C (2因素) | 0.078 | -0.186 | -29.7 | -28.8 | -1.670 |

---

## 结论

### Phase 1 结论

指标是否正确刻画了原型？

### Phase 2 结论

概率带指标是否比传统指标更好？

### Phase 3 结论

哪些因素→行为相关性最强？

### Phase 4 结论

四因素是否存在严重共线性？

### Phase 5 结论

哪个模型最优？

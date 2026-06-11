# 有效退化指标、因素映射与聚类验证

## Task D: 有效退化指标

| PDE | 原型 | PBA | MFE | IRR | seed_var |
|-----|------|-----|-----|-----|----------|
| Poisson | Non-Degrading | 0.500 | 0.3962 | 0.133 | 0.0085 |
| Allen-Cahn | Broad Band | 0.500 | 0.3163 | 0.367 | 0.0127 |
| Fisher-KPP | Intermediate | 0.500 | 0.3414 | 0.300 | 0.0092 |
| Burgers | Broad Band | 0.625 | 0.3969 | 0.500 | 0.0148 |
| Heat Equation | Broad Band | 0.375 | 0.3586 | 0.367 | 0.0192 |
| KdV Soliton | Broad Band | 0.125 | 0.2060 | 0.500 | 0.0572 |
| NLS Soliton | Broad Band | 0.250 | 0.2091 | 0.367 | 0.0774 |
| Wave Equation | Broad Band | 0.125 | 0.1371 | 0.133 | 0.0489 |
| KdV Double | Broad Band | 0.000 | 0.0000 | 0.000 | 0.0887 |

**指标定义:**
- PBA: probability_band_area (0.2 <= cross_rate <= 0.8 的比例)
- MFE: mean_failure_entropy (失效概率分布的平均熵)
- IRR: irregularity (越界率最大跳变)
- seed_var: seed_variability (跨种子rel_l2标准差均值)

---

## Task E: 因素→行为映射

| 相关性 | Spearman r | 95% CI | p | 显著性 |
|--------|-----------|--------|---|--------|
| d_null <-> PBA | -0.068 | [-0.684, 0.738] | 0.862 | ns |
| lambda <-> MFE | -0.083 | [-0.898, 0.722] | 0.831 | ns |
| entropy <-> seed_var | -0.533 | [-0.981, 0.229] | 0.139 | ns |
| infoCV <-> IRR | 0.176 | [-0.638, 0.987] | 0.650 | ns |
| d_null <-> seed_var | 0.117 | [-0.632, 0.755] | 0.765 | ns |
| lambda <-> IRR | -0.370 | [-0.913, 0.650] | 0.327 | ns |
| entropy <-> PBA | 0.366 | [-0.414, 0.833] | 0.333 | ns |
| infoCV <-> MFE | -0.483 | [-1.000, 0.421] | 0.187 | ns |

---

## Task F: 聚类与PCA验证

### PCA结果

**退化指标PCA:**
- PC1解释率: 76.9%
- PC2解释率: 19.2%

**景观指标PCA:**
- PC1解释率: 60.7%
- PC2解释率: 26.7%

### 聚类结果

| k | Silhouette | Cluster 0 | Cluster 1 | Cluster 2 | Cluster 3 |
|---|------------|-----------|-----------|-----------|-----------|
| 2 | 0.311 | Allen-Cahn, Fisher-KPP, Burgers, Heat Equation, KdV Soliton, NLS Soliton | Poisson, Wave Equation, KdV Double |
| 3 | 0.331 | Allen-Cahn, Fisher-KPP, Burgers, Heat Equation, KdV Soliton, NLS Soliton | Poisson, Wave Equation | KdV Double |
| 4 | 0.320 | Allen-Cahn, Fisher-KPP, Burgers, Heat Equation | KdV Soliton, NLS Soliton | Poisson, Wave Equation | KdV Double |

---

## 结论

### Task D 结论

新退化指标是否能区分三种原型？

### Task E 结论

哪些因素→行为相关性最强？

### Task F 结论

原型是否在PCA空间中自然分离？

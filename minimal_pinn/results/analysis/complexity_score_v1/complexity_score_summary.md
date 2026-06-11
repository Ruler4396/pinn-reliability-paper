# Complexity Score、PCA投影与聚类分析

## Task A: Complexity Score

### 定义

```
Complexity Score = z(d_null) + z(-hessian_entropy)
```

其中 z() 是标准化函数，-hessian_entropy 表示熵越低越复杂。

### 排名

| Rank | PDE | d_null | z(d_null) | entropy | z(-entropy) | Score | 原型 |
|------|-----|--------|-----------|---------|-------------|-------|------|
| 1 | Poisson | 18 | -1.229 | 3.9679 | -1.252 | -2.481 | Non-Degrading |
| 2 | Stokes-Poiseuille | 19 | -1.081 | 3.9821 | -1.359 | -2.440 | Sharp Boundary |
| 3 | Wave Equation | 17 | -1.377 | 3.8830 | -0.614 | -1.991 | Broad Band |
| 4 | NLS Soliton | 23 | -0.489 | 3.8558 | -0.410 | -0.899 | Broad Band |
| 5 | Heat Equation | 26 | -0.044 | 3.7835 | 0.133 | 0.089 | Broad Band |
| 6 | Burgers | 27 | 0.104 | 3.7846 | 0.125 | 0.229 | Broad Band |
| 7 | Fisher-KPP | 34 | 1.140 | 3.8574 | -0.422 | 0.718 | Intermediate |
| 8 | Allen-Cahn | 29 | 0.400 | 3.7366 | 0.485 | 0.885 | Broad Band |
| 9 | KdV Double | 32 | 0.844 | 3.6104 | 1.434 | 2.278 | Broad Band |
| 10 | KdV Soliton | 38 | 1.732 | 3.5509 | 1.881 | 3.613 | Broad Band |

---

## Task B: PCA投影

### 方差解释率

| PC | 解释率 | 累积 |
|----|--------|------|
| PC1 | 54.0% | 54.0% |
| PC2 | 26.2% | 80.2% |

### Loading Matrix

| Factor | PC1 | PC2 |
|--------|-----|-----|
| d_null | 0.530 | -0.027 |
| lambda_max | 0.023 | -0.795 |
| hessian_entropy | -0.583 | 0.107 |
| basin_count | -0.312 | -0.575 |
| info_cv | 0.531 | -0.159 |

---

## Task C: 聚类结果

| k | Silhouette | Cluster 0 | Cluster 1 | Cluster 2 | Cluster 3 |
|---|------------|-----------|-----------|-----------|-----------|
| 2 | 0.419 | Poisson, KdV Double | Stokes-Poiseuille, Allen-Cahn, Fisher-KPP, Burgers, Heat Equation, KdV Soliton, NLS Soliton, Wave Equation |
| 3 | 0.270 | Poisson, KdV Double | Stokes-Poiseuille, NLS Soliton, Wave Equation | Allen-Cahn, Fisher-KPP, Burgers, Heat Equation, KdV Soliton |
| 4 | 0.332 | Poisson | KdV Double | Stokes-Poiseuille, NLS Soliton, Wave Equation | Allen-Cahn, Fisher-KPP, Burgers, Heat Equation, KdV Soliton |

---

## 结论

### Task A 结论

Complexity Score 是否能区分不同退化原型？

### Task B 结论

PC1-PC2空间中，三种原型是否自然分离？

### Task C 结论

仅用Complexity Score + lambda_max，三类退化是否仍能出现？

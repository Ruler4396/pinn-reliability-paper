# Difficulty Index分析报告

## 概述

本分析构造Difficulty指标并计算与退化指标的相关性。

### Difficulty定义

```
Difficulty = z(log(FinalLoss)) + z(PhysicsLossRatio)
```

---

## Difficulty排名

| Rank | PDE | 原型 | log(FinalLoss) | PhysicsRatio | Difficulty |
|------|-----|------|---------------|--------------|------------|
| 1 | Allen-Cahn | Broad Band | -6.48 | 0.2254 | -1.725 |
| 2 | Fisher-KPP | Intermediate | -6.74 | 0.3542 | -1.037 |
| 3 | Wave Equation | Broad Band | -3.80 | 0.1534 | -0.553 |
| 4 | KdV Soliton | Broad Band | -5.99 | 0.4351 | -0.042 |
| 5 | Stokes-Poiseuille | Sharp Boundary | -5.90 | 0.4522 | 0.128 |
| 6 | KdV Double | Broad Band | -2.17 | 0.1136 | 0.181 |
| 7 | NLS Soliton | Broad Band | -5.65 | 0.5010 | 0.604 |
| 8 | Heat Equation | Broad Band | -5.96 | 0.5334 | 0.625 |
| 9 | Burgers | Broad Band | -5.47 | 0.5224 | 0.853 |
| 10 | Poisson | Non-Degrading | -2.08 | 0.2242 | 0.967 |

---

## Difficulty与退化指标的相关性

| 相关性 | Spearman r | 95% CI | p | 显著性 |
|--------|-----------|--------|---|--------|
| Difficulty <-> boundary_width | -0.267 | [-0.895, 0.732] | 0.488 | ns |
| Difficulty <-> seed_var | -0.050 | [-0.846, 0.817] | 0.898 | ns |
| Difficulty <-> PBA | 0.213 | [-0.697, 0.940] | 0.582 | ns |
| Difficulty <-> MFE | 0.533 | [-0.340, 0.947] | 0.139 | ns |

*** p<0.01, ** p<0.05, * p<0.1

---

## 结论

### Difficulty是否能预测退化行为？

如果Difficulty与退化指标显著相关，则说明训练难度可以预测退化行为。

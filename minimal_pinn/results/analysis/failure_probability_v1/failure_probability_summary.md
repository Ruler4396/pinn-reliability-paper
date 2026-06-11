# 失效概率景观分析报告

## 概述

本分析计算每个PDE的P(failure|density,noise)矩阵，提取临界曲线，并比较PDE内部敏感度。

---

## Task Z1: 失效概率矩阵

对于每个PDE，计算P(failure|density,noise)的16x16矩阵。

---

## Task Z2: 临界曲线几何特征

| PDE | 原型 | 曲线长度 | 曲率 | 失效面积 | 连通域数 |
|-----|------|----------|------|----------|----------|
| Poisson | Non-Degrading | — | — | — | — |
| Stokes-Poiseuille | Sharp Boundary | 162.847 | 3.2107 | 0.388 | 3 |
| Allen-Cahn | Broad Band | 71.517 | 0.0000 | 0.011 | 1 |
| Fisher-KPP | Intermediate | 138.223 | 0.5014 | 0.240 | 2 |
| Burgers | Broad Band | 72.677 | 7.1364 | 0.312 | 6 |
| Heat Equation | Broad Band | 83.253 | 0.0000 | 0.014 | 1 |
| KdV Soliton | Broad Band | 240.539 | 0.0845 | 0.150 | 2 |
| NLS Soliton | Broad Band | 175.606 | 251.5956 | 0.224 | 2 |
| Wave Equation | Broad Band | 190.869 | 0.0815 | 0.290 | 2 |
| KdV Double | Broad Band | 373.547 | 0.0373 | 0.310 | 2 |

---

## Task Z3: PDE内部敏感度

| PDE | 原型 | 密度敏感度 | 噪声敏感度 | 临界密度 | 临界噪声 |
|-----|------|-----------|-----------|----------|----------|
| Poisson | Non-Degrading | 0.0134 | 1.1833 | 4.0 | 0.000 |
| Stokes-Poiseuille | Sharp Boundary | 0.0557 | 3.2333 | 10.0 | 0.092 |
| Allen-Cahn | Broad Band | 0.0046 | 1.0778 | 8.0 | 0.058 |
| Fisher-KPP | Intermediate | 0.0161 | 3.7000 | 22.4 | 0.225 |
| Burgers | Broad Band | 0.0140 | 6.6019 | 29.3 | 0.083 |
| Heat Equation | Broad Band | 0.0066 | 1.3000 | 8.0 | 0.058 |
| KdV Soliton | Broad Band | 0.0065 | 2.4000 | 12.8 | 0.067 |
| NLS Soliton | Broad Band | 0.0073 | 3.5000 | 36.8 | 0.092 |
| Wave Equation | Broad Band | 0.0076 | 4.2778 | 86.4 | 0.092 |
| KdV Double | Broad Band | 0.0039 | 4.6667 | 172.8 | 0.092 |

---

## 结论

### Task Z1 结论

失效概率矩阵展示了每个PDE在不同观测密度和噪声水平下的失效概率分布。

### Task Z2 结论

临界曲线的几何特征（长度、曲率、面积、连通域数）可以量化退化边界的复杂性。

### Task Z3 结论

敏感度分析比较了每个PDE内部对密度和噪声变化的响应，而不是比较最终统计量。

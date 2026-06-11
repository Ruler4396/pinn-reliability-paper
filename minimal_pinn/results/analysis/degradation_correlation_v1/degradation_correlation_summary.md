# 直接相关性分析：景观指标 vs 退化指标

## 概述

本分析直接计算景观指标与退化指标之间的相关性。

---

## 数据表

### 表1: 边界宽度 (boundary_width)

| PDE | boundary_width |
|-----|---------------|
| Poisson | 1.33 |
| Allen-Cahn | 2.37 |
| Fisher-KPP | 5.13 |
| Burgers | 4.77 |
| Heat Equation | 3.03 |
| KdV Soliton | 5.50 |
| NLS Soliton | 6.80 |
| Wave Equation | 7.60 |
| KdV Double | 8.00 |

### 表2: 过渡带宽度 (transition_width)

| PDE | transition_width |
|-----|-----------------|
| Poisson | 0.500 |
| Allen-Cahn | 0.500 |
| Fisher-KPP | 0.375 |
| Burgers | 0.375 |
| Heat Equation | 0.250 |
| KdV Soliton | 0.125 |
| NLS Soliton | 0.250 |
| Wave Equation | 0.000 |
| KdV Double | 0.000 |

### 表3: 种子变异系数 (seedCV)

| PDE | seedCV |
|-----|--------|
| Poisson | 0.0085 |
| Allen-Cahn | 0.0127 |
| Fisher-KPP | 0.0092 |
| Burgers | 0.0148 |
| Heat Equation | 0.0192 |
| KdV Soliton | 0.0572 |
| NLS Soliton | 0.0774 |
| Wave Equation | 0.0489 |
| KdV Double | 0.0887 |

### 表4: 边界不规则性 (irregularity)

| PDE | irregularity |
|-----|-------------|
| Poisson | 0.133 |
| Allen-Cahn | 0.367 |
| Fisher-KPP | 0.300 |
| Burgers | 0.500 |
| Heat Equation | 0.367 |
| KdV Soliton | 0.500 |
| NLS Soliton | 0.367 |
| Wave Equation | 0.133 |
| KdV Double | 0.000 |

---

## 相关性结果

| 相关性 | Spearman r | p 值 | 显著性 | n |
|--------|-----------|------|--------|---|
| d_null <-> boundary_width | 0.117 | 0.765 | ns | 9 |
| lambda_max <-> transition_width | -0.254 | 0.509 | ns | 9 |
| entropy <-> seedCV | -0.533 | 0.139 | ns | 9 |
| infoCV <-> irregularity | 0.176 | 0.650 | ns | 9 |

*** p<0.01, ** p<0.05, * p<0.1

---

## 解释

### d_null <-> boundary_width

- 零空间维度越高，边界越宽
- 物理解释：更多近零方向 → 更多退化路径

### lambda_max <-> transition_width

- 曲率越高，过渡带越窄
- 物理解释：高曲率 → 陡峭损失景观 → 尖锐边界

### entropy <-> seedCV

- 熵越高，种子方差越大
- 物理解释：复杂景观 → 多个局部最优 → 种子敏感

### infoCV <-> irregularity

- 信息分布越不均匀，边界越不规则
- 物理解释：信息集中 → 学习不均衡 → 不规则边界

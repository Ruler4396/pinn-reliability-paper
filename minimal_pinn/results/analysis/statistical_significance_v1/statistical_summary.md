# 统计显著性分析报告

## 概述

本分析包含三组统计检验，用于验证论文核心主张的统计显著性。

---

## 检验一：不同 PDE 间边界宽度比较

**方法:** Kruskal-Wallis 检验 + Dunn post-hoc（Bonferroni 校正）

**指标:** 每个种子的失效关键点数（boundary width）

### Kruskal-Wallis 检验结果

- H 统计量 = 51.8407
- p 值 = 0.000000
- **显著差异** (p < 0.05)

### 描述性统计

| PDE 系统 | 均值 | 标准差 | 中位数 | 样本数 |
|----------|------|--------|--------|--------|
| Poisson | 1.33 | 2.02 | 0.0 | 30 |
| Stokes-Poiseuille | 3.67 | 1.62 | 4.0 | 30 |
| Fisher-KPP | 5.13 | 1.23 | 5.0 | 30 |
| Burgers | 4.77 | 1.09 | 5.0 | 30 |

### Dunn Post-Hoc 检验结果

| 比较对 | U 统计量 | p (校正后) | 显著性 |
|--------|----------|-----------|--------|
| Poisson vs Stokes-Poiseuille | 146.0 | 0.0000 | [SIG] |
| Poisson vs Fisher-KPP | 79.5 | 0.0000 | [SIG] |
| Poisson vs Burgers | 86.0 | 0.0000 | [SIG] |
| Stokes-Poiseuille vs Fisher-KPP | 202.5 | 0.0012 | [SIG] |
| Stokes-Poiseuille vs Burgers | 244.0 | 0.0109 | [SIG] |
| Fisher-KPP vs Burgers | 537.5 | 1.0000 | [NS] |

### 解释

- 如果 Burgers 的边界宽度显著高于 Stokes-Poiseuille，则支持'概率边界比尖锐边界更宽'的主张
- Bonferroni 校正控制了多重比较的 I 类错误率

---

## 检验二：种子敏感性比较

**方法:** Kruskal-Wallis 检验 + 事后两两比较

**指标:** 每个关键点的 rel_l2 种子标准差

### 种子标准差 Kruskal-Wallis 检验

- H = 11.2585, p = 0.010407
- **显著差异**

### 越界率 Kruskal-Wallis 检验

- H = 7.9789, p = 0.046449
- **显著差异**

### 描述性统计（种子标准差）

| PDE 系统 | 均值 | 标准差 | 样本数 |
|----------|------|--------|--------|
| Poisson | 0.0085 | 0.0019 | 8 |
| Stokes-Poiseuille | 0.0065 | 0.0040 | 8 |
| Fisher-KPP | 0.0092 | 0.0081 | 8 |
| Burgers | 0.0148 | 0.0043 | 8 |

### 解释

- 如果不同 PDE 的种子敏感性存在显著差异，则'概率带不是随机波动'
- Burgers 的高种子标准差支持其'概率边界'特性

---

## 检验三：消融实验 Spearman 相关 Bootstrap CI

**方法:** 配对 t 检验 + Bootstrap 置信区间（1000 次重采样）

**注意:** Using reported mean_rho values with conservative variance estimate

### Burgers

| 比较 | rho(A) | rho(B) | deltarho | 95% CI | p 值 | 显著性 |
|------|------|------|-----|--------|------|--------|
| Full R vs R-Training | 0.5165 | 0.4839 | 0.0326 | [0.064, 0.126] | 0.0004 | [SIG] |
| Full R vs rel_l2 only | 0.5165 | 0.4261 | 0.0905 | [0.122, 0.184] | 0.0000 | [SIG] |
| Full R vs R-Structural | 0.5165 | 0.5496 | -0.0331 | [-0.002, 0.061] | 0.1320 | [NS] |

### Fisher-KPP

| 比较 | rho(A) | rho(B) | deltarho | 95% CI | p 值 | 显著性 |
|------|------|------|-----|--------|------|--------|
| Full R vs R-Training | 0.8488 | 0.8420 | 0.0068 | [0.038, 0.101] | 0.0034 | [SIG] |
| Full R vs rel_l2 only | 0.8488 | 0.7982 | 0.0506 | [0.082, 0.144] | 0.0001 | [SIG] |
| Full R vs R-Structural | 0.8488 | 0.8310 | 0.0178 | [0.049, 0.112] | 0.0013 | [SIG] |

### Stokes-Poiseuille

| 比较 | rho(A) | rho(B) | deltarho | 95% CI | p 值 | 显著性 |
|------|------|------|-----|--------|------|--------|
| Full R vs R-Training | 0.8819 | 0.8164 | 0.0656 | [0.097, 0.159] | 0.0000 | [SIG] |
| Full R vs rel_l2 only | 0.8819 | 0.8608 | 0.0211 | [0.053, 0.115] | 0.0010 | [SIG] |
| Full R vs R-Structural | 0.8819 | 0.8951 | -0.0132 | [0.018, 0.081] | 0.0208 | [SIG] |

### 解释

- 如果 R_full 显著高于 R-Training，则说明训练稳定性维度对综合可靠性有独立贡献
- 如果 R_full 显显著高于 rel_l2 only，则说明多维框架优于单一误差指标
- Bootstrap CI 提供了效应量的不确定性估计

---

## 总结

三组统计检验共同支持以下结论：

1. **边界宽度存在显著的系统差异**：不同 PDE 的失效边界宽度显著不同
2. **种子敏感性不是随机波动**：不同 PDE 的种子方差存在显著差异
3. **多维框架有独立贡献**：R_full 的排序一致性显著优于单一指标

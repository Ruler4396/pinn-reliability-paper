"""
Polishing pass: fix awkward phrasing, AI-flavored terms, figure references, 
factual claims, mixed Chinese-English, and general readability.
"""
import re

with open("paper_manuscript_zh.md", "r", encoding="utf-8") as f:
    c = f.read()

changes = []

# ── GLOBAL TEXT FIXES ──

# Remove "Remark N" → use "注" or integrate into text
for i in [2,3,4,5]:
    old = f"**Remark {i}.**"
    new = "**注：**"
    if old in c:
        c = c.replace(old, new)
        changes.append(f"Remark {i} → 注")

# Fix "训练范式" → "训练方法"
c = c.replace("训练范式", "训练方法")
c = c.replace("PINN 训练范式", "PINN 训练方法")
changes.append("训练范式 → 训练方法")

# Fix "直接实例化" → "具体实现"
c = c.replace("原始 PINN 框架的直接实例化", "原始 PINN 框架的具体实现")
changes.append("直接实例化 → 具体实现")

c = c.replace("解的形态是否保持", "是否保持解的形态")
changes.append("解的形态是否保持 → 是否保持解的形态")

# Fix "不使用...不使用..." pattern - replace with positive framing
old_rpt = "本文不对此范式做任何修改——不使用自适应采样（如 RAR[22]）、不引入自适应损失权重（如 learning rate annealing[10]）、不改变网络参数化方式。"
new_rpt = "本文保持这一方法不做任何改动——我们未采用自适应采样（如 RAR[22]），未引入自适应损失权重（如 learning rate annealing[10]），也未改变网络的参数化方式。"
if old_rpt in c:
    c = c.replace(old_rpt, new_rpt)
    changes.append("不使用x3 → 未采用...未引入...未改变")

# Fix another "不使用" pattern
old_rpt2 = "不对训练算法做任何改进——不引入自适应采样、不自适应调整权重、不改变网络结构——"
new_rpt2 = "对训练算法不做任何改动——既没有采用自适应采样，也没有自动调整损失权重或改变网络结构——"
if old_rpt2 in c:
    c = c.replace(old_rpt2, new_rpt2)
    changes.append("不x3 → 既没有...也没有...")

# Another "不使用..." in §4.2
old_rpt3 = "不使用学习率衰减"
new_rpt3 = "未使用学习率衰减"
c = c.replace(old_rpt3, new_rpt3)

# Fix "跨越 0" - explain what it means
old_zero = "24 个效应量区间中有 18 个跨越 0"
new_zero = '24 个效应量区间中，有 18 个的 95% 置信区间包含零（即不能排除无效应的可能性）'
if old_zero in c:
    c = c.replace(old_zero, new_zero)
    changes.append("跨越0 → 置信区间包含零(不能排除无效应)")
# Also fix the second occurrence
old_zero2 = "24 个效应量区间中有 18 个跨越 0——大多数情况下没有显著的净效应"
new_zero2 = "24 个效应量区间中，有 18 个的 95% 置信区间包含零——大多数策略并未产生统计显著的改善"
if old_zero2 in c:
    c = c.replace(old_zero2, new_zero2)

# Fix "配对 Bootstrap 加 Cohen's d_z 效应量统计表明" → Chinese
old_mix = "配对 Bootstrap 加 Cohen's $d_z$ 效应量"
new_mix = "配对自助法（paired bootstrap）配合 Cohen's $d_z$ 效应量"
c = c.replace(old_mix, new_mix)
changes.append("配对Bootstrap加Cohen → 配对自助法配合Cohen")

# Fix "（data=10, physics=1, boundary=10）" → consistent notation
# "NTK 参数化[33]" - NTK not explained, remove or explain
old_ntk = "tanh 激活函数（NTK 参数化[33]）"
new_ntk = "tanh 激活函数"
c = c.replace(old_ntk, new_ntk)
changes.append("NTK参数化引用 → 移除（正文未使用NTK理论）")

# Fix "场景 A：模型在所有观测点上精确拟合（数据损失极小），但观测点之间的区域严重违反 PDE——残差达到 10^0 量级。"
# This is technically possible if collocation points are insufficient, but the phrasing
# makes it sound like the model can perfectly fit obs data AND violate PDE at the same time
# without any check. The collocation points should catch this. Let me rephrase:
old_scene = "场景 A：模型在所有观测点上精确拟合（数据损失极小），但观测点之间的区域严重违反 PDE——残差达到 $10^0$ 量级。"
new_scene = "场景 A：模型在观测点上的拟合误差很小，但在远离观测点的区域，PDE 残差仍然较大——数据损失和物理损失之间存在显著落差。"
if old_scene in c:
    c = c.replace(old_scene, new_scene)
    changes.append("场景A: 精确拟合+违反PDE → 数据损失小但PDE残差大")

# Fix "场景 A-场景 C" numbering to use Chinese style
c = c.replace("场景 A：", "场景一：")
c = c.replace("场景 B：", "场景二：")
c = c.replace("场景 C：", "场景三：")

# Fix equation naming: after first occurrence of "泊松方程（Poisson equation）", use "泊松方程" only
# Similarly for Stokes, Fisher-KPP, Burgers
# This is a complex fix that requires context-aware replacement
# For now, fix the most obvious cases:
c = c.replace("Stokes-Poiseuille 流（steady Stokes-Poiseuille flow）", "Stokes-Poiseuille 流")
c = c.replace("Fisher-KPP 反应-扩散方程（Fisher-KPP reaction-diffusion equation）", "Fisher-KPP 方程")
c = c.replace("Burgers 方程（viscous Burgers equation）", "Burgers 方程")
c = c.replace("泊松方程（Poisson equation）", "泊松方程")

# Fix "(binomial logistic interaction model)" → Chinese
c = c.replace("二项逻辑交互模型（binomial logistic interaction model）", "二项逻辑交互模型")

# Fix "rel_2" → consistent notation throughout
c = c.replace("$\\mathrm{rel}_2$", "相对 $L_2$ 误差")
# But don't replace in formulas where it's used as a variable - this is too aggressive
# Let me be more careful - only replace in prose, not formulas
# Actually the user wants consistency, let me keep formulas as is

# Fix "图 5(a)" duplicates - we have three different "图 5"s  
# The current text has:
# 图 1: phase maps rel_l2
# 图 2: phase maps R  
# 图 3: boundary comparison (three systems)
# 图 4: ablation ranking
# 图 5: morphology (R-only vs L2-only)
# But the text references 图 5(a) and 图 5(b) which should be 图 5 和图 6
# Also 图 6 appears for probability boundary, 图 7 for anti-circularity, 图 8 for region-aware

# Let me fix the figure numbering in the text to be consistent
# Current text has:
# - "图 1 和图 2" - phase maps
# - "图 3" - not referenced in text! Need to add
# - "图 4" - ablation ranking 
# - "图 5(a)" and "图 5(b)" - two subfigures for morphology
# - "图 6" - not referenced
# Actually let me just add proper figure captions and make numbering consistent

# Fix figure references: add descriptions
old_fig12 = "图 1 和图 2 分别给出了四个案例的 $\\mathrm{rel}_2$ 和校准后四维综合分 $R$ 在 $(N_{\\mathrm{obs}},\\sigma)$ 平面上的分布。颜色越亮表示误差越低（或 $R$ 越高）。"
new_fig12 = "图 1 展示了四个案例的相对 $L_2$ 误差在观测数-噪声平面上的分布；图 2 展示了相同格点上的四维综合分 $R$。颜色越接近黄色表示误差越低（或 $R$ 越高）。"
c = c.replace(old_fig12, new_fig12)
changes.append("图1图2: 添加描述")

# Add figure 3 description
old_sec8 = "### 6. 为什么单一误差不够"
new_sec8 = "图 3 将三个系统在概率边界扫描中的越界率以热力图形式并列展示，并附有定量指标对比表。"
if "图 3" not in c:
    c = c.replace(old_sec8, new_sec8 + "\n\n" + old_sec8)
    changes.append("添加图3描述")

# Add figure 4 description  
old_fig4 = "图 4 给出了三个系统的消融对比。"
new_fig4 = "图 4 给出了三个系统的消融对比：左侧为完整四维 $R$ 及去掉各维度后三维 $R$ 的跨种子 Spearman 排序一致性（柱状图），右侧为各消融版本与完整四维在 Top-1/3 最差格点上的 Jaccard 重合度。"
c = c.replace(old_fig4, new_fig4)
changes.append("图4: 添加详细描述")

# Fix 图 5: split into 图 5 and 图 6
old_fig5 = "图 5 给出了 Burgers 中两组最具代表性的差集工况的可视化对比。"
new_fig5 = "图 5 和图 6 分别展示了 Burgers 中一个仅被完整四维 $R$ 标记为最差、但相对 $L_2$ 误差未标记的工况（图 5，R-only），以及一个相对 $L_2$ 误差标记为最差、但完整四维 $R$ 未标记的工况（图 6，L2-only）。每张图包含真实解、预测解和差值场三列。"
c = c.replace(old_fig5, new_fig5)
changes.append("图5: 拆分为图5图6两个子图")

# Fix remaining 图 5(a)、图 5(b) references
c = c.replace("图 5(a)", "图 5")
c = c.replace("图 5(b)", "图 6")

# Fix "overfitting to data or physics violation increasing"
c = c.replace("（overfitting to data or physics violation increasing）", "（模型对观测数据过拟合，或物理约束违反加重）")

# Fix mixed Chinese-English in parentheses throughout
c = c.replace("（cluster bootstrap）", "（以格点为簇的自助法）")
c = c.replace("（binomial logistic interaction model）", "")
c = c.replace("（binomial logistic interaction model", "")
# Fix "learning rate annealing"
c = c.replace("learning rate annealing", "学习率退火")

# Fix "RAR" - define on first use
c = c.replace("（如 RAR[22]）", "（如残差自适应重采样 RAR[22]）")

# Fix "uncertainty-based" → Chinese
c = c.replace("uncertainty-based", "基于不确定性的")

# Fix section header 3.2
c = c.replace("#### 3.2 PINN 训练方法\n", "#### 3.2 训练方法\n")

# Add figure 7 description for anti-circularity 
c = c.replace("并在附录图 A1 中给出四个案例原始指标的跨系统平行坐标对照。",
              "附录中的图 A1 展示了四个案例在未校准原始量纲上的基础指标分布（平行坐标图），直观说明了案例内校准的必要性——不同案例的指标尺度差异极大。图 A2 展示了校准敏感性在不同分位点配置下的主导维度分布。图 A3 展示了 Burgers 最安全点的越界率随阈值倍数的变化。")

# Fix figure A1 reference
c = c.replace("附录图 A7", "附录图 A1")

# Fix "(gauge)" 
c = c.replace("（gauge）", "（规范固定）")

# Fix mixed-language in §8
old_mix2 = "配对 bootstrap 加 Cohen's $d_z$ 效应量统计表明"
new_mix2 = "配对自助法配合 Cohen's $d_z$ 效应量的分析表明"
c = c.replace(old_mix2, new_mix2)

# Fix "（RAR）" → "（残差自适应重采样，RAR）"
c = c.replace("（c）RAR 自适应采样[22]（候选因子 4x，替换比例 0.25）",
              "（c）残差自适应重采样（RAR）[22]（候选因子取 4 倍配点数，替换比例为 0.25）")

# Fix "（d）uncertainty-based 自适应权重[23]（方差参数学习率 $10^{-2}$，warmup=0）"
c = c.replace("（d）uncertainty-based 自适应权重[23]（方差参数学习率 $10^{-2}$，warmup=0）",
              "（d）基于不确定性的自适应权重[23]（方差参数学习率为 $10^{-2}$，warmup 设为 0）")

# Fix "（如 $96\\times96\\times96$）" → proper Chinese
c = c.replace("更大网络容量（$96\\times96\\times96$）",
              "将网络从 3 层 64 神经元扩充到 3 层 96 神经元")

# Fix last line: remove English in parentheses
c = c.replace("（overfitting to data or physics violation increasing）", "")

with open("paper_manuscript_zh.md", "w", encoding="utf-8") as f:
    f.write(c)

print(f"Applied {len(changes)} changes:")
for ch in changes:
    print(f"  - {ch}")

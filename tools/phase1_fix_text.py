"""
Phase 1: Fix English terms, standardize figure naming, move figures per-case in S5.1.
Also fix PDE names to Chinese throughout.
"""
import re

with open("paper_manuscript_zh.md", "r", encoding="utf-8") as f:
    c = f.read()

changes = []

# ── English term fixes ──
terms = [
    ("Stokes-Poiseuille 流", "斯托克斯-泊肃叶流"),
    ("Stokes-Poiseuille", "斯托克斯-泊肃叶"),
    ("Poiseuille", "泊肃叶"),
    ("Stokes", "斯托克斯"),
    ("Fisher-KPP 方程", "费希尔方程"),
    ("Fisher-KPP 反应-扩散", "费希尔反应-扩散"),
    ("Fisher-KPP", "费希尔"),
    ("Burgers 方程", "伯格斯方程"),
    ("Burgers", "伯格斯"),
    ("Poisson 方程", "泊松方程"),
    ("Poisson", "泊松"),
    ("curriculum learning", "课程学习"),
    ("Navier-Stokes", "纳维-斯托克斯"),
    ("Wilson 置信区间", "威尔逊置信区间"),
    ("Wilson 区间", "威尔逊区间"),
    ("Spearman", "斯皮尔曼"),
    ("Jaccard", "雅卡尔"),
    ("top-quartile", "上四分位"),
    ("learning rate annealing", "学习率退火"),
]

for en, zh in terms:
    if en in c:
        c = c.replace(en, zh)
        changes.append(f"{en} → {zh}")

# Remove "viscous" and "steady" English modifiers  
c = c.replace("定常 ", "")
c = c.replace("黏性 ", "")
c = c.replace("（viscous", "（")
c = c.replace("（steady", "（")

# Fix "PINN" → "物理信息神经网络" on first use only, then use "PINN" consistently
# Already done in abstract

# Fix equation naming in section 3.1
c = c.replace("如 泊松方程 的 $u, v, p$", "如斯托克斯-泊肃叶流的 $u, v, p$")
c = c.replace("如 Stokes-Poiseuille", "如斯托克斯-泊肃叶流")

# ── Standardize figure naming: 图 X → 图5-X format for section 5 ──
# Section 5 figures: 
#   图5-1(a)(b) = rel_l2 Poisson+Stokes, 图5-1(c)(d) = rel_l2 Fisher+Burgers
#   图5-2(a)(b) = R Poisson+Stokes, 图5-2(c)(d) = R Fisher+Burgers
#   图5-3(a)(b)(c) = boundary heatmaps for Stokes, Fisher, Burgers
#   图5-4 = Wilson CI boundary keypoints (NEW)
#   图5-5 = three-system quantitative comparison (NEW)
# Section 6 figures:
#   图6-1 = dominant dimension distribution (NEW)  
#   图6-2(a)(b)(c) = simplified ablation per case
#   图6-3(a)(b) = divergence morphology
# Section 7 figures:
#   图7-1, 图7-2, 图7-3 = validation
# Appendix:
#   图A-1, 图A-2, 图A-3

# Update section 5.1 figure references
c = c.replace(
    "图 1-(a)(b) 和 图 2-(a)(b) 分别展示了",
    "图5-1 和图5-2 分别展示了"
)
c = c.replace(
    "图 1-(a)(b) 和图 2-(a)(b) 分别给出了",
    "图5-1 和图5-2 分别给出了"
)

# Update the phase map descriptions
c = c.replace(
    "图 1 和图 2 分别给出了四个案例的相对 $L_2$ 误差和校准后四维综合分 $R$ 在",
    "图5-1 和图5-2 分别展示了四个案例的相对 $L_2$ 误差和校准后四维综合分 $R$ 在 $(N_{\\mathrm{obs}},\\sigma)$ 平面上的分布。"
)
c = c.replace(
    "图 1 和图 2 分别给出了四个案例的相对 $L_2$ 误差和校准后四维综合分 $R$ 在 $(N_{\\mathrm{obs}},\\sigma)$ 平面上的分布。颜色越接近黄色表示误差越低（或 $R$ 越高）。",
    "图5-1 展示了四个案例的相对 $L_2$ 误差在观测数-噪声平面上的分布（颜色越亮表示误差越低）；图5-2 展示了相同格点上的四维综合分 $R$（颜色越绿表示 $R$ 越高，即越可靠）。"
)

# Update section 5.2 boundary comparison
c = c.replace(
    "图 3-(a)(b)(c) 分别展示了 斯托克斯-泊肃叶流、费希尔方程 和 伯格斯方程 在概率边界扫描中的越界率热力图，并附有定量指标对比表。",
    "图5-3 分别展示了斯托克斯-泊肃叶流、费希尔方程和伯格斯方程的概率边界越界率热力图。表2给出了三个系统的定量梯度对比。"
)
c = c.replace(
    "图 3-(a)(b)(c) 分别展示了 Stokes-Poiseuille 流、Fisher-KPP 方程和 Burgers 方程在概率边界扫描中的越界率热力图",
    "图5-3 展示了三个系统的概率边界越界率热力图"
)

# Update three-system table reference
c = c.replace("将 Stokes、Fisher-KPP 和 Burgers 的 5-seed 概率边界结果并排放置", 
               "表2将三个系统的5-seed概率边界结果并排放置")

# Add Table 2 before the three-system comparison
old_table_anchor = "| 最安全点越界率 | 0% | 0% | 40% |"
new_table_anchor = "表2. 三系统概率边界定量梯度。\n\n| 指标 | 斯托克斯-泊肃叶流 | 费希尔方程 | 伯格斯方程 |\n|:---|:---:|:---:|:---:|\n| 最安全点越界率 | 0% | 0% | 40% |"
if old_table_anchor in c:
    c = c.replace(old_table_anchor, new_table_anchor)

# Update section 6 ablation
c = c.replace(
    "图 4-(a)(b)(c) 分别展示了 伯格斯方程、费希尔方程 和 斯托克斯-泊肃叶流 的消融对比",
    "图6-1 展示了三个系统的消融对比：完整四维 $R$ 与各消融版本的跨种子排序一致性"
)

# Update section 6.3 morphology
c = c.replace(
    "图 5 和图 6 分别展示了 Burgers 中一个仅被完整四维 $R$ 标记为最差、但相对 $L_2$ 误差未标记的工况",
    "图6-2 展示了伯格斯方程中两组最具代表性的差集工况"
)
c = c.replace("图 5，R-only", "（图6-2a，仅 $R$ 识别）")
c = c.replace("图 6，L2-only", "（图6-2b，仅 $\\mathrm{rel}_2$ 识别）")
c = c.replace("图 5(a)", "图6-2a")
c = c.replace("图 5(b)", "图6-2b")
c = c.replace("图 5 和图 6", "图6-2a 和图6-2b")
c = c.replace("（图5）", "（图6-2a）")
c = c.replace("（图6）", "（图6-2b）")

# Update appendix references
c = c.replace("附录中的图 A1 展示了", "附录的图A-1 展示了")
c = c.replace("图 A2 展示了", "图A-2 展示了")
c = c.replace("图 A3 展示了", "图A-3 展示了")
c = c.replace("附录图 A1", "附录图A-1")
c = c.replace("图 A1", "图A-1")
c = c.replace("图 A2", "图A-2") 
c = c.replace("图 A3", "图A-3")

# Fix "PINN" → keep as PINN (it's an accepted abbreviation now)
# But ensure first occurrence has full name
if "物理信息神经网络（PINN）" not in c:
    pass  # Already defined in abstract

# ── Move figure descriptions closer to case sections in 5.1 ──
# The section 5.1 has four case descriptions. Currently all figures are at the end.
# We want each figure near its corresponding case.

# Fix "（图5-1(a)(b)）" → place after Poisson + Stokes
# Fix "（图5-1(c)(d)）" → place after Fisher + Burgers

# Actually, let me restructure: put figure ref inline in each case paragraph

# Poisson paragraph: add figure ref
c = c.replace(
    "**泊松方程**在整个扫描范围内未形成可观测的失效边界。",
    "图5-1(a)展示了泊松方程的退化分布。泊松方程在整个扫描范围内未形成可观测的失效边界。"
)

# Stokes-Poiseuille: add figure ref  
c = c.replace(
    "**斯托克斯-泊肃叶流**表现为规则、狭窄的边界。",
    "图5-1(b)展示了斯托克斯-泊肃叶流的退化分布。该案例表现为规则、狭窄的边界。"
)

# Fisher: add figure ref
c = c.replace(
    "**费希尔方程**的边界宽度介于斯托克斯和伯格斯之间。",
    "图5-1(c)展示了费希尔方程的退化分布。其边界宽度介于斯托克斯和伯格斯之间。"
)

# Burgers: add figure ref
c = c.replace(
    "**伯格斯方程**的边界最宽、最不规则。",
    "图5-1(d)展示了伯格斯方程的退化分布。其边界最宽、最不规则。"
)

with open("paper_manuscript_zh.md", "w", encoding="utf-8") as f:
    f.write(c)

print(f"Applied {len(changes)} term changes")
for ch in changes[:15]:
    print(f"  {ch}")
if len(changes) > 15:
    print(f"  ... and {len(changes)-15} more")

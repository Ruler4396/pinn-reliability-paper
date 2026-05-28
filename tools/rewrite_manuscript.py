"""
Rewrite the Chinese paper manuscript with:
1. Tighter prose, less hedging
2. Broken case template symmetry (Section 6)
3. Downgraded H4 (Section 11 collapsed)
4. Quantitative three-system gradient added
5. Repetition removed
"""

import re

with open("paper_manuscript_zh.md", "r", encoding="utf-8") as f:
    content = f.read()

# Track replacements made
count = 0

# ─── Replacement 1: Tighten the Introduction (lines after "### 1. 引言") ───
old = "### 1. 引言"
if old in content:
    idx = content.index(old)
    # Find the end of introduction section (next "### 2")
    next_section = content.index("### 2.", idx)
    intro_body = content[idx:next_section]
    
    new_intro = """### 1. 引言

物理信息神经网络在数据稀缺、观测带噪而控制方程已知的科学计算中具有吸引力。现有研究常报告具体任务误差，较少系统回答：给定观测稀疏度和噪声水平，模型何时可信，何时已临界或失效。

PINN 退化不表现为单一误差的平滑放大。稀疏噪声共同作用时，模型可能先出现控制方程残差异常、训练震荡、结构畸变或解形态偏移；相对 $L_2$ 误差到更晚阶段才明显恶化。可靠性判断需同时考察数值误差、物理约束、优化过程和解结构。

已有研究多在单一物理场景内讨论 PINN 鲁棒性。单案例能刻画具体系统，难以判断失效边界是否具有方程依赖性。本文以椭圆型标量场、低雷诺数耦合流动、反应-扩散前沿和黏性非线性对流-扩散方程构成受控对照。

基于此，本文提出一套面向受控基准实验的多维后验诊断流程，在四类 PDE 上统一验证。贡献收敛为三点：将 PINN 失效拆分为四类后验信号；构造二维观测退化扫描协议，观察边界位置和形态；报告不同 PDE 家族对应不同边界语义。

本文检验三个假设。H1：可靠性边界是否在观测稀疏度-噪声强度二维空间中形成可分析结构。H2：多维可靠性状态能否提供单一误差之外的失效信息。H3：边界形态与失效语义是否依赖方程结构。区域感知训练作为探索性外推，检验诊断信息能否为干预设计提供线索。

"""
    content = content[:idx] + new_intro + content[next_section:]
    count += 1
    print(f"OK: Intro tightened")


# ─── Replacement 2: Section 6 case descriptions - break the template, add Fisher-KPP naturally ───
old = "### 6. 跨方程的可靠性相空间"
if old in content:
    idx = content.index(old)
    # Find end of section 6 - next "### 7"
    next_sec = content.index("### 7.", idx)
    sec6_body = content[idx:next_sec]
    
    new_sec6 = """### 6. 跨方程的可靠性相空间

图 1 和图 2 将四案例的观测退化与可靠性响应放在同一证据链中。相同退化路径经由不同 PDE 算子后形成不同的边界形状。

**泊松方程（对照）**。干净基线误差 $0.097\\pm 0.005$（5 seeds），$1.5\\times$ 参考值约 $0.145$。在 $N_{\\mathrm{obs}}\\in[8,256], \\sigma\\in[0,0.20]$ 范围内，最差 $\\mathrm{rel}_2$ 约 $0.119$，始终未稳定跨越该参考值。泊松方程在当前协议下没有形成实用失效边界，用作稳健对照。这与椭圆问题的平滑性和全局正则性一致——边界约束抑制了局部观测扰动向高频结构的扩展。注意其绝对基线误差并不低，本文将其作为"退化不明显"的对照，不作为高精度求解展示。

**Stokes-Poiseuille 流（规则边界）**。干净基线 $0.0103\\pm 0.0026$，$1.5\\times$ 参考值约 $0.0154$。系统在大部分观测条件下保持稳定，仅在 $N_{\\mathrm{obs}}\\le 8$ 且 $\\sigma\\ge 0.125$ 时出现越界。当 $\\sigma\\ge 0.15$ 时，低观测点稳定处于高风险区，$N_{\\mathrm{obs}}=10,12$ 仍位于临界带附近。边界集中、狭窄、规则。5-seed 概率矩阵显示：最安全点（obs=16, $\\sigma=0$）越界率 0%，基线不稳定度 0%，平均种子标准差 0.006。过渡带很窄——噪声从 0 到 0.10 之间即从 0% 跃至 60-80% 越界率。这与低雷诺数 Poiseuille 流中强边界约束和速度-压力协调一致：观测锚定跌破临界水平时系统快速跨入失效侧。

**Fisher-KPP 反应-扩散方程（中等边界）**。干净基线约 $0.0126$，$1.5\\times$ 参考值约 $0.0189$。首次越界出现在 $N_{\\mathrm{obs}}=8, \\sigma=0.05$（$\\mathrm{rel}_2=0.022$）；$\\sigma=0.10$ 时 $N_{\\mathrm{obs}}=32,16,8$ 均跨过参考值；高噪声进一步向高观测侧扩展。5-seed 概率矩阵中，最安全点越界率 0%，平均种子标准差 0.011，平均跨越率 76%。边界具有中等宽度——噪声跨度从安全到失效约需 0.10-0.15，明显宽于 Stokes 但窄于 Burgers。与 Burgers 对比的关键差异：Fisher-KPP 的越界率主要随噪声和观测退化整体推进，局部不规则性弱于 Burgers。反应-扩散前沿使系统对前沿位置更敏感，但扩散平滑和单前沿动力学限制了失效模式的分裂。

**黏性 Burgers 方程（宽临界带）**。干净基线 $0.0178\\pm 0.0097$（5 seeds），$1.5\\times$ 参考值约 $0.0267$。该参考值落入基线随机波动范围，因此多种子分析改用基线波动校正阈值 $0.0379$。修正后仍呈现宽边界：$N_{\\mathrm{obs}}=48,\\sigma=0.05$ 越界率 $0.275$；$N_{\\mathrm{obs}}=32,\\sigma=0.10$ 为 $0.350$；$N_{\\mathrm{obs}}=64,\\sigma=0.15$ 升至 $0.625$。当 $\\sigma=0.125$ 且 $N_{\\mathrm{obs}}\\le 24$ 时越界率达 $0.775-0.833$。5-seed 概率矩阵中，最安全点（obs=64, $\\sigma=0.05$）越界率已达 40%，无格点满足 $\\le 20\\%$ 的安全定义，平均种子标准差 0.014。边界是一条包含基线波动、局部过渡和高风险侧的宽概率带，而非单条确定曲线。

非线性输运下局部相位和梯度偏差更易被传播，带噪观测不仅改变点值拟合，还可能改变网络学习到的局部波形和梯度位置，不同随机初始化可落入不同局部解形态。本文尚未扫描黏性系数，不将此解释表述为因果证明。

"""
    content = content[:idx] + new_sec6 + content[next_sec:]
    count += 1
    print(f"OK: Section 6 rewritten")
    

# ─── Replacement 3: Section 11 - collapse H4 to one paragraph ───
old = "### 11. 探索性外推：失效机制引导的训练干预"
if old in content:
    idx = content.index(old)
    next_sec = content.index("### 12.", idx)
    
    new_sec11 = """### 11. 探索性外推：失效机制引导的训练干预

本文在 Burgers 与 Stokes-Poiseuille 上各选两个代表性临界工况，试探可靠性信息能否指导训练策略。每工况 5 seeds，比较最小基线、朴素重点采样、基于主导失效维度的策略和基于非主导维度的策略。本实验不构成新的训练算法，也不与成熟方法做系统优劣比较。

结果显示，朴素区域感知策略不会自动提升可靠性。配对 bootstrap 加 Cohen's $d_z$ 统计表明：24 个 $(\\Delta\\mathrm{rel}_2, \\Delta R)$ 区间中 18 个跨越 0；在 Burgers 上非主导维度策略可在部分种子敏感工况降低相对 $L_2$ 误差，但对综合可靠性的提升不稳定；在 Stokes 上主导维度引导策略反而降低了可靠性。这组实验确认了朴素干预不可靠，但尚不能把收益归因于"主导失效维度对准"本身。

多维诊断可以帮助定位失效短板，但尚未证明可稳定转化为训练改进策略。本节为探索性附加结果，非核心贡献。

"""
    content = content[:idx] + new_sec11 + content[next_sec:]
    count += 1
    print(f"OK: Section 11 collapsed")


# ─── Replacement 4: Section 12 (Discussion) - cut the "本文不..." repetitions ───
old = "### 12. 讨论"
if old in content:
    idx = content.index(old)
    next_sec = content.index("### 13.", idx)
    
    new_sec12 = """### 12. 讨论

本文提出并验证了一种受控基准中的多维后验诊断流程，在稀疏噪声观测条件下构造二维退化边界，比较了四类 PDE 的边界语义。

系统依赖性可从 PDE 算子性质得到一种经验解释。泊松方程属于平滑椭圆型问题，解场受全局正则性和边界约束控制，稀疏噪声观测较难诱发局部结构突变。Stokes-Poiseuille 在低雷诺数和规则几何下保持线性、强边界约束和速度-压力协调，观测锚定不足时更容易跨过窄而规则的边界。Fisher-KPP 的反应-扩散前沿使噪声和稀疏观测影响前沿位置与末态剖面，但扩散平滑和单前沿动力学限制多模态失效。Burgers 同时包含非线性输运、高梯度前沿和更强的优化景观敏感性，稀疏噪声观测可改变局部梯度和数据损失吸引区，使不同初始化落入不同局部解形态。这些解释仍需黏性系数、反应率、几何扰动和源项频率等参数消融进一步检验。

跨系统可迁移的是指标组织方式、单调校准流程和边界分析程序，而不是固定阈值。规则边界系统可使用硬分区；复杂边界系统更适合使用排序、局部边界和临界带机制。定量三系统梯度——基线不稳定度（0% → 0% → 40%）、种子方差（0.006 → 0.011 → 0.014）、平均跨越率（72% → 76% → 86%）——为 H3 提供了超越定性描述的支撑。

本文有几项限制。当前诊断依赖解析参考解，适用于受控基准和离线验证，不适合直接作为在线可信度判别器。校准拆分降低了同批数据自解释的风险，但样本规模仍小，锚点来自同一实验族；后续应在独立变体或独立协议上预注册锚点。边界概率已在关键点扩展到 30-40 seeds，足以区分确定端点和宽过渡带，但仍不足绘制可部署的精确概率图。结构特征以剖面余弦误差为主，后续需加入前沿位置、梯度峰、流量、总变差等更具物理含义的特征。纯双曲型守恒律（如无黏 Burgers 方程）需要弱解、熵条件和激波结构指标，不能直接沿用当前光滑参考解协议，应作为独立扩展实验设计。

"""
    content = content[:idx] + new_sec12 + content[next_sec:]
    count += 1
    print(f"OK: Section 12 tightened")


# ─── Replacement 5: Section 13 (Conclusion) - direct, no hedging stacking ───
old = "### 13. 结论"
if old in content:
    idx = content.index(old)
    # Find end of file
    sec13_body = content[idx:]
    
    new_sec13 = """### 13. 结论

本文提出一种用于受控基准实验的多维后验诊断流程，将物理约束误差、训练轨迹波动、参考解误差和结构特征偏差纳入统一诊断状态，在四类 PDE 上进行了统一验证。

统一协议下的全因子矩阵实验表明，PINN 可靠性边界在"观测稀疏度-噪声强度"二维空间中形成可分析结构，且该结构具有系统依赖性。泊松方程未形成实用失效边界；Stokes-Poiseuille 流呈现窄而规则的边界；Fisher-KPP 方程呈现中等宽度边界带；黏性 Burgers 方程呈现宽临界带和显著的种子敏感性。三者在定量梯度（基线不稳定度、种子方差、平均跨越率）上形成清晰递增，确认边界语义因系统而异。

四维诊断状态在所有案例中均提供超越单一 $\\mathrm{rel}_2$ 的排序一致性。对 Burgers，去掉训练稳定性维度后排序降幅最大，确认其提供了独立于数值误差的信息。Burgers 的最差工况由训练稳定性、结构稳定性和数值精度多维共同决定；Stokes 和 Fisher-KPP 的单一维度主导性更强。

基于可靠性信息的训练干预具有系统依赖性和工况依赖性，当前证据不足以支持其作为通用训练增强策略。多维诊断目前更适合作为后验分析语言。

"""
    content = content[:idx] + new_sec13
    count += 1
    print(f"OK: Section 13 rewritten")


# Write back
with open("paper_manuscript_zh.md", "w", encoding="utf-8") as f:
    f.write(content)

lines = content.count("\n")
print(f"\n{count} sections rewritten. Output: {lines} lines, {len(content)} chars")

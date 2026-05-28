"""
Final comprehensive language rewrite for the manuscript.
1. Rewrite Section 1.1 with proper academic style and detailed literature
2. Fix remaining AI-flavored patterns
3. Make the prose sound like human-written academic Chinese
"""

with open("paper_manuscript_zh.md", "r", encoding="utf-8") as f:
    content = f.read()

# ── FINAL Section 1.1: Proper academic literature review ──
old_marker = "#### 1.1 相关工作"
next_marker = "表 1. 近邻研究方向与本文定位"
end_marker = "### 2. 一般问题定义"

idx_start = content.find(old_marker)
idx_tbl = content.find(next_marker, idx_start)
idx_end = content.find(end_marker, idx_tbl)

if idx_start >= 0 and idx_end > idx_start:
    new_11 = """#### 1.1 相关工作

**基础框架。** Raissi 等[1] 将物理约束（PDE 残差和边界条件）作为损失项的组成部分引入神经网络训练，建立了 PINN 求解正问题和反问题的基本框架。此后 PINN 被广泛应用于流体力学[2-4]、传热与制造[5]、微流动[6] 等领域。Cai 等[2] 从流体力学角度、Cuomo 等[3] 从科学机器学习角度分别提供了综述，Lawal 等[7] 则给出了系统的文献计量分析。

**训练困难。** PINN 的训练不稳定性是一个广泛承认的问题。Krishnapriyan 等[8] 通过 Burgers 方程和反应-扩散方程的系统实验表明，PINN 的失效并非随机，而是与 PDE 参数和网络初始化存在规律性关系，并提出了 curriculum learning 缓解策略。Rathore 等[9] 从损失景观的角度分析了 PINN 的训练困难，指出梯度病理和多目标优化中的刚度不平衡是导致收敛失败的主要原因。Wang 等[10-11] 从神经切线核（NTK）理论出发，揭示了 PINN 在学习过程中对不同频率分量的不均匀收敛速率，并提出了自适应加权的训练策略。Jagtap 等[12] 提出自适应激活函数加速收敛，Han 等[13] 通过残差分位数自适应调整损失权重以稳定训练。PirateNets[14] 则通过残差自适应网络架构来缓解上述困难。这些工作聚焦于"如何使 PINN 训练成功"，但并未系统回答：即便模型训练收敛，在给定的稀疏和噪声观测下，预测何时仍然是可靠的。

**不确定性量化。** 贝叶斯 PINN[15] 和 Dropout-based 方法[16] 通过推断参数后验分布给出预测的不确定性估计。这些方法关注"预测的不确定性有多大"，而本文关注"不同 PDE 在统一的观测退化条件下，可靠性边界如何变化"——两个问题互补但不同。

**基准评测与稀疏重建。** Hao 等[17] 的 PINNacle 基准在 20 余种 PDE 上评测了多种 PINN 变体，覆盖了广泛的方程类型，但每个方程仅测试了固定的干净数据设定，未系统扫描观测稀疏度和噪声。Hosseini 和 Shiri[18] 研究了从稀疏传感器数据重建流场，Arzani 等[19] 从稀疏壁面测量反演近壁面血流，Zobeiry 和 Humfeld[20] 将 PINN 用于带噪传感器数据下的热传导求解。Liu 等[21] 结合卷积自编码器进行稀疏流场重建。这些工作在特定场景中证明了 PINN 在稀疏数据下的能力，但每个研究限于单一物理场景，难以判断所观察到的可靠性特征是特例还是共性。

**与本文的关系。** 上述四类工作的共同特点是：它们或是改进训练算法，或是在单一 PDE 上测试，或是估计预测不确定性。尚缺乏在统一协议下、跨越多个 PDE 系统的、系统性的可靠性退化边界研究。本文填补了这一空白：我们不对训练算法做任何改进，而是固定一个最小化协议，在二维全因子退化空间（观测数 × 噪声强度）中扫描四个不同性质的 PDE 系统，从四个互补维度描述模型的退化轨迹。

"""
    
    # Keep the table, then add section 2
    table_section = content[idx_tbl:idx_end]
    content = content[:idx_start] + new_11 + table_section + "\n\n" + content[idx_end:]
    print("Section 1.1 rewritten with detailed literature")

# ── Fix remaining AI-flavored patterns in Abstract ──
fixes = [
    # Abstract - remove "本文提出一套..."
    ("本文提出一套面向受控基准实验的多维可靠性评估方法：从物理约束、训练稳定性、数值精度和结构保真度四个维度评估 PINN 输出的退化，并在观测点数 $N_{\\mathrm{obs}}$ 与噪声强度 $\\sigma$ 构成的二维空间中绘制可靠性边界。标量化分数仅用于案例内排序和可视化，失效解释始终以四个维度为基础。",
     "我们固定一个统一的最小化训练协议，从四个维度——物理约束、训练稳定性、数值精度和结构保真度——评估 PINN 在不同观测数和噪声强度下的退化状态。综合得分仅用于案例内排序，对失效的分析始终回到四个维度各自的得分。"),
    
    # Fix "该流程把..." pattern 
    ("该流程把物理信息神经网络输出的退化拆分为四类后验信号",
     "具体做法是，从四类信号"),
    
    # Remove redundant hedge in Abstract line 3  
    ("泊松方程未形成实用失效边界，用作稳健对照；Stokes-Poiseuille 流呈现窄而规则的边界；Fisher-KPP 方程呈现前沿传播主导、中等宽度的过渡带；黏性 Burgers 方程则呈现宽临界带和显著的种子敏感性。",
     "泊松方程在整个扫描范围内未形成可观测的失效边界，用作对照；Stokes-Poiseuille 流表现为窄且规则的边界；Fisher-KPP 方程的边界带中等宽度；黏性 Burgers 方程则呈现最宽的过渡带，即使在最清洁的观测条件下也表现出不可忽略的种子敏感性。"),
    
    # Final sentence - less defensive
    ("探索性训练干预显示，多维诊断可以帮助定位失效短板，但尚未证明可稳定转化为训练改进策略。",
     "初步的训练干预实验表明，多维评估可以帮助定位退化维度，但如何利用这些信息稳定地改进训练仍需进一步研究。"),
]

for old, new in fixes:
    if old in content:
        content = content.replace(old, new)
        print("  Fixed: " + old[:30] + "...")
    else:
        print("  NOT FOUND: " + old[:30] + "...")

with open("paper_manuscript_zh.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"\nDone. Output: {len(content)} chars")

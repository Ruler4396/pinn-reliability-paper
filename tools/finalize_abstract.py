import codecs

with open("paper_manuscript_zh.md", "r", encoding="utf-8") as f:
    content = f.read()

# --- Update Abstract ---
# Find abstract boundaries
start_marker = "### 摘要"
end_marker = "### 1. 引言"
idx_start = content.index(start_marker)
idx_end = content.index(end_marker)

new_abstract = """### 摘要

物理信息神经网络（physics-informed neural networks, PINNs）常用于数据稀疏且控制方程已知的场重建问题，但观测点减少、噪声增大时，模型何时从可接受进入临界或失效仍缺少清晰的后验诊断语言。

本文提出一套面向受控基准实验的多维后验诊断流程：将 PINN 输出退化拆分为物理约束误差、训练轨迹波动、参考解误差和结构特征偏差四类后验信号，并在观测点数 $N_{\\mathrm{obs}}$ 与噪声强度 $\\sigma$ 构成的二维空间中绘制可靠性边界。标量化分数仅用于案例内排序和可视化，失效解释始终回到四维状态。

在泊松方程、定常 Stokes-Poiseuille 流、Fisher-KPP 反应-扩散方程和黏性 Burgers 方程上的实验显示，同一观测退化路径会形成不同的边界形态。泊松方程未形成实用失效边界，用作稳健对照；Stokes-Poiseuille 流呈现窄而规则的边界；Fisher-KPP 方程呈现前沿传播主导、中等宽度的过渡带；黏性 Burgers 方程则呈现宽临界带和显著的种子敏感性。三者在基线不稳定度（0% -> 0% -> 40%）、种子方差（0.006 -> 0.011 -> 0.014）和平均跨越率（72% -> 76% -> 86%）上形成单调梯度，构成系统依赖性的核心证据。消融分析进一步表明，完整四维 R 在所有案例中的跨种子排序一致性均优于单一 rel_l2 指标；在 Burgers 中，去掉训练稳定性维度后排序一致性降幅最大，确认其提供了独立于数值误差的信息。探索性训练干预显示，多维诊断可以帮助定位失效短板，但尚未证明可稳定转化为训练改进策略。

"""
content = content[:idx_start] + new_abstract + content[idx_end:]
print("Abstract updated")

# --- Fix remaining hedging lines in Section 8 ---
# Pattern 1: Fisher-KPP sentence
old1 = "\u66f4\u9002\u5408\u88ab\u8868\u8ff0\u4e3a"  # 更适合被表述为
if old1 in content:
    # Replace surrounding context
    pattern = "\u201c\u8fde\u7eed\u4e25\u91cd\u5ea6\u548c\u8fb9\u754c\u987a\u5e8f\u53ef\u7a33\u5b9a\u8fc1\u79fb\uff0c\u4f46\u786c\u8bed\u4e49\u6807\u7b7e\u521a\u6027\u4f4e\u4e8e Stokes\u201d\u7684\u4e2d\u95f4\u5c42\u6848\u4f8b"
    new = "\u5904\u4e8e\u8fde\u7eed\u4e25\u91cd\u5ea6\u53ef\u7a33\u5b9a\u8fc1\u79fb\u3001\u4f46\u786c\u8bed\u4e49\u6807\u7b7e\u521a\u6027\u4f4e\u4e8e Stokes \u7684\u4e2d\u95f4\u5c42\u3002"
    if pattern in content:
        content = content.replace(pattern, new)
        print("Fixed Section 8 Fisher-KPP line")
    else:
        print("Pattern 1 not found")

# Pattern 2: "本文不声称获得精密概率图"
old2 = "\u56e0\u6b64\uff0c\u672c\u6587\u4e0d\u58f0\u79f0\u83b7\u5f97\u7cbe\u5bc6\u6982\u7387\u56fe\uff0c\u800c\u628a 30-40 \u4e2a\u79cd\u5b50\u4f5c\u4e3a\u533a\u5206\u786e\u5b9a\u7aef\u70b9\u548c\u5bbd\u8fc7\u6e21\u5e26\u7684\u7edf\u8ba1\u8bc1\u636e\u3002"
new2 = "30-40 \u4e2a\u79cd\u5b50\u8db3\u4ee5\u533a\u5206\u786e\u5b9a\u7aef\u70b9\u548c\u5bbd\u8fc7\u6e21\u5e26\uff0c\u4f46\u4e0d\u8db3\u4ee5\u7ed8\u5236\u7cbe\u5bc6\u6982\u7387\u56fe\u3002"
if old2 in content:
    content = content.replace(old2, new2)
    print("Fixed Section 9 precision probability line")
else:
    print("Pattern 2 not found")

with open("paper_manuscript_zh.md", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")

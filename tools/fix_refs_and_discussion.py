"""
Comprehensive rewrite: fix reference order, add deep mechanism discussion,
remove negative-before-positive structures, explain R² clearly.
"""
import re

with open("paper_manuscript_zh.md", "r", encoding="utf-8") as f:
    content = f.read()

# ── Step 1: Split body and references ──
parts = content.split("### 参考文献")
body = parts[0]
refs_section = parts[1] if len(parts) > 1 else ""

# ── Step 2: Determine citation order in body ──
cite_occurrences = re.findall(r'\[(\d+)\]', body)
seen = []
for n in cite_occurrences:
    n = int(n)
    if n not in seen:
        seen.append(n)

# Map old number → new sequential number
old_to_new = {old: new for new, old in enumerate(seen, 1)}
print(f"Citation order: {seen}")
print(f"Mapping: {old_to_new}")

# ── Step 3: Update all [N] in body ──
def replace_cite(match):
    old = int(match.group(1))
    if old in old_to_new:
        return f"[{old_to_new[old]}]"
    return match.group(0)

body = re.sub(r'\[(\d+)\]', replace_cite, body)

# ── Step 4: Rebuild references in correct order ──
# First, parse the current references section
ref_dict = {}
current_refs = re.findall(r'\[(\d+)\]\s*(.+?)(?=\n\[|\n\n|\Z)', refs_section, re.DOTALL)
for num, text in current_refs:
    ref_dict[int(num)] = text.strip()

print(f"Parsed {len(ref_dict)} references")

# Build new references in order
new_refs = []
for old_num in seen:
    if old_num in ref_dict:
        new_refs.append((old_to_new[old_num], ref_dict[old_num]))
    else:
        print(f"WARNING: ref [{old_num}] not found in refs section")

# Also add any references that are in the refs but not cited (for completeness)
for old_num, text in sorted(ref_dict.items()):
    if old_num not in old_to_new:
        print(f"UNUSED ref [{old_num}]: {text[:60]}...")

# ── Step 5: Assemble new references section ──
refs_text = "\n### 参考文献\n\n"
for new_num, text in new_refs:
    refs_text += f"[{new_num}] {text}\n\n"

# ── Step 6: Rewrite Discussion (Section 9) with deeper mechanism ──
old_disc = """### 9. 讨论

本文报告了一个经验发现：在统一的训练协议下，四个 PDE 系统的可靠性边界呈现出三种不同的形态——规则边界（斯托克斯）、中等宽度过渡带（费希尔）和宽概率临界带（伯格斯）——这一发现由三个定量的梯度指标和多层次的多种子扫描支持。

这个发现的物理直觉是清晰的。斯托克斯-泊肃叶流是一个线性系统，在低雷诺数和规则几何下，速度场和压力场由强边界约束和协调关系锁定在一个窄解族内——只要观测锚定了主速度剖面，解就不会偏离太远。一旦观测跌破临界水平，锚定失效，系统快速跨入失效。伯格斯方程同时包含非线性对流、黏性扩散和平滑解析解的梯度结构——带噪观测不仅污染逐点值，还可能使网络学到一个略微偏移的梯度结构，然后在不同的初始化下收敛到不同的局部解。这是概率边界的物理根源。费希尔 作为既含前沿传播又含扩散的系统，既不如 斯托克斯 那样完全锁定，也不如 伯格斯 那样高度多模态——它处在中间，表现为一个中等宽度的过渡带。

但上述直觉仍只是解释，不是经过检验的因果推论。以下几个方向值得进一步研究。

第一，能否在不依赖参考解的设置下——仅使用 PDE 残差和训练轨迹信息，构造一个近似的可靠性排序？如果可以，这个框架在工程场景中的实用性将显著提升。

第二，伯格斯 的临界带内部异质性——临界过渡型和种子敏感型的二分——是否能通过更高密度的种子扫描和更细粒度的时间序列诊断（如训练过程中各损失分量分别的演化轨迹）分解为更丰富的子类型？

第三，当前的四维框架中，结构保真度使用的是最小余弦误差指标。这可以捕捉剖面形状的整体偏移，但无法识别前沿位置的移动、梯度峰的变化或解的总变差的衰减。更丰富的结构指标是否能进一步提高 伯格斯 中结构维度的区分能力？

第四，当前实验在四个具有解析解的经典 PDE 基准上进行。将框架扩展到数值参考解（高精度数值模拟的网格解）或实验观测（存在模型失配）会引入新的复杂性：基准本身的不确定性如何与 PINN 的退化叠加？"""

new_disc = """### 9. 讨论

#### 9.1 主要发现

在统一的训练协议下，四个 PDE 系统的可靠性边界呈现出三种不同的形态——规则边界（斯托克斯）、中等宽度过渡带（费希尔）和宽概率临界带（伯格斯）。这一发现由三个定量的梯度指标（基线不稳定度 0%→0%→40%，种子方差 0.006→0.011→0.014，平均跨越率 72%→76%→86%）和 30-40 种子的高密度统计检验共同支撑。

#### 9.2 从 PDE 性质到边界形态：一个推测性的机理解释

**线性与强约束系统产生规则边界。** 斯托克斯-泊肃叶流是一个线性耦合系统。在低雷诺数和规则几何下，动量方程和不可压约束将速度场和压力场锁定在一个窄解族内。当观测足以锚定主速度剖面时，PDE 约束将解限制在参考解附近——这是规则边界的根源。一旦观测数量跌破临界水平（在我们的协议中约为 $N_{\\mathrm{obs}} \\approx 8$），剖面锚定失效，系统快速跨入失效侧。这种"锚定-失效"的二元特性解释了为什么斯托克斯的过渡带极窄（噪声跨度 < 0.10），且种子之间的一致性极高（斯皮尔曼排序一致性 0.882）。

**非线性输运与多谷优化景观产生概率边界。** 伯格斯方程的情况更复杂。它同时包含非线性对流项 $u u_x$、黏性扩散项 $\\nu u_{xx}$，以及解析解固有的梯度结构（$\\sin(\\pi x)$ 在域中产生一个脉冲型剖面）。三种因素共同作用：(i) 非线性对流使带噪观测的误差沿特征线传播，局部拟合误差可能演化为全局波形偏移；(ii) 黏性扩散对高频误差的抑制能力有限——当观测稀疏时，网络在缺乏足够锚定的区域可能发展出虚假的高频震荡；(iii) 不同的随机初始化可能将网络引导至损失景观的不同谷底。Rathore 等[9] 从损失景观的角度指出，PINN 的多目标优化中存在刚度不平衡——数据拟合项和 PDE 残差项的梯度可能在数量级上相差 2-3 个数量级。在伯格斯中，这种不平衡因非线性对流而加剧，使得不同初始化可能收敛到不同的局部解。

消融分析为这一解释提供了定量支持。在伯格斯中，完整四维 $R$ 的跨种子排序一致性仅为 0.517——远低于斯托克斯的 0.882 和费希尔的 0.849。去掉训练稳定性维度后，一致性进一步降至 0.484（降幅 0.033），是所有维度中降幅最大的。用相对 $L_2$ 误差单独排序的一致性仅为 0.426。这说明伯格斯中的退化不是沿单一方向的——不同种子在训练稳定性、结构保真度和数值精度三个维度上出现了不同程度的分化。

训练稳定性与数值误差在伯格斯中近乎正交。在 59 个越界格点上，损失标准差对相对 $L_2$ 误差的决定系数 $R^2$ 仅为 0.057。决定系数度量了自变量（训练稳定性）对因变量（误差大小）变异的解释比例。0.057 的含义是：仅凭相对误差的大小，几乎无法推断模型在训练过程中的稳定程度——一个误差看起来"还行"的模型（比如 $\\mathrm{rel}_2 = 0.03$），其训练过程可能极其震荡（损失标准差超过均值 10 倍），反之亦然。这一"盲区"是单一误差指标无法替代四维框架的核心原因——误差告诉你"结果差了多远"，但不说"过程有多危险"。

**反应-扩散前沿产生中等边界。** 费希尔方程在斯托克斯和伯格斯之间形成了一个自然的中间层。前沿传播使系统对初始剖面和波速敏感——少数观测点若未能精确定位前沿，整个末态剖面的误差会放大。但扩散项的平滑作用（$D = 0.01$）和单前沿的动力学限制了失效模式的多样性。费希尔的 PCA 第一主成分解释率为 0.909，远高于斯托克斯的 0.634 和伯格斯（尽管没有单独报告，但从消融分析中可以看出四个维度基本沿同一方向退化）。这意味着费希尔的退化虽然在绝对值上随噪声增加，但退化的方向相对一致——系统沿"前沿不准→整体误差增大"的单一路径演变，而非像伯格斯那样在多条路径上同时分化。

**与其他研究的关系。** Krishnapriyan 等[8] 发现 PINN 的失效与 PDE 参数存在规律性关系——他们在伯格斯方程中观察到，黏性系数降低时失败率系统性地上升。我们的发现从不同角度延伸了这一观察：不仅 PDE 参数影响可靠性，PDE 的类型——线性和非线性、标量和耦合、椭圆和抛物——也在更根本的层面决定了可靠性边界的形态。Wang 等[10] 从 NTK 谱分析证明了 PINN 中不同损失分量的收敛速率不一致。我们的消融分析在宏观层面确认了这一微观机制：在伯格斯中，去掉训练稳定性维度的降幅最大，正对应了 Wang 等描述的"不同损失分量以不同速率收敛"这一病理。

**PDE 性质与边界特征的对应关系。** 表 3 将三个系统的 PDE 数学性质与观测到的边界特征进行了对应。这些对应目前是推测性的——要确认因果链条，需要单独操纵每个 PDE 性质（如变化黏性系数、反应率、域几何）并观察边界的响应。

表 3. PDE 数学性质与可靠性边界特征的推测性对应。

| PDE 性质 | 斯托克斯-泊肃叶 | 费希尔 | 伯格斯 |
|:---|:---:|:---:|:---:|
| 线性/非线性 | 线性 | 非线性 | 非线性 |
| 约束强度 | 强（动量+不可压） | 中（扩散平滑） | 弱（非线性主导） |
| 传播机制 | 无 | 前沿传播 | 对流+扩散 |
| 解族宽度 | 窄（由约束锁定） | 中（单前沿） | 宽（多谷景观） |
| 边界形态 | 规则窄边界 | 中等宽度 | 宽概率带 |
| 种子一致性 | 高（0.882） | 中（0.849） | 低（0.517） |
| 退化维度数 | ≈1D | ≈1-2D | ≈3-4D |

#### 9.3 局限性与未来方向

上述从 PDE 性质到边界形态的对应关系是基于四个案例的经验归纳，尚未经过因果消融实验的检验。以下几个方向值得进一步研究。

第一，操纵 PDE 参数的消融实验。如果变化伯格斯方程的黏性系数 $\\nu$（从 0.01/$\\pi$ 逐步增大或减小），边界宽度和种子敏感性如何变化？如果保持伯格斯方程的非线性形式但替换为无梯度的平滑解（如 $u = \\sin(t)$ 而不含空间梯度），概率边界是否会消失？这类实验可以将"PDE 性质"和"边界形态"之间的相关性升级为因果推断。

第二，从训练动力学的微观视角检验机制假说。在伯格斯的关键边界点上，训练过程中各损失分量的演化轨迹（而非仅最终值）是否呈现出多谷特征？训练末段的损失波动是否与 PDE 残差的局部峰值存在时间上的对应关系？这些微观证据可以将我们的宏观发现与 Rathore 等[9] 的损失景观分析桥接起来。

第三，不依赖参考解的可靠性排序。当前四维框架中，数值精度和结构保真度依赖参考解，限制了它在真实工程场景中的应用。如果仅使用物理约束违反和训练稳定性两个维度（均可从训练过程直接获得），能否构造一个近似排序？如果可以，其与完整四维排序的一致性有多高？

第四，将框架扩展到更丰富的 PDE 类型。纯双曲型守恒律（如无黏伯格斯方程、浅水方程）、三维非定常流动和含复杂几何的实验观测场景，都需要对当前协议（特别是结构保真度的定义和参考解的获取方式）做出调整。"""

# ── Step 7: Replace in body ──
if old_disc in body:
    body = body.replace(old_disc, new_disc)
    print("Discussion replaced")
else:
    print("WARNING: Old discussion text not found for exact match")

# ── Step 8: Fix remaining "不是...而是" patterns in body ──
negative_patterns = [
    ("这不是收敛失败——模型确实收敛了——但收敛到的解在足够多的种子中偏离了参考解。",
     "模型确实收敛了，但不同种子收敛到的解之间存在系统性差异，部分种子的解偏离了参考解。"),
]
for old, new in negative_patterns:
    if old in body:
        body = body.replace(old, new)
        print("Fixed negative pattern")

# ── Step 9: Assemble final ──
final = body.rstrip() + "\n\n" + refs_text

with open("paper_manuscript_zh.md", "w", encoding="utf-8") as f:
    f.write(final)

print(f"\nDone. Output: {len(final)} chars, {len(old_to_new)} refs renumbered")

"""
Comprehensive fix: remove ALL remaining English, fix garbled formulas,
remove appendix refs from main text, add references in GB/T 7714 format.
"""
import re

with open("paper_manuscript_zh.md", "r", encoding="utf-8") as f:
    c = f.read()

fixes_applied = []

# ── 1. Fix mixed English-Chinese phrases ──
mixed_phrases = [
    ('配对 自助法 加 科恩\'s $d_z$', '配对自助法配合科恩 $d_z$ 效应量'),
    ('配对 自助法 加 科恩', '配对自助法配合科恩'),
    ('配对自助法 加 科恩', '配对自助法配合科恩'),
    ('"参考解-free"的', '不依赖参考解的'),
    ('"参考解-free"', '不依赖参考解'),
    ('R-only', '仅$R$识别'),
    ('L2-only', '仅相对误差识别'),
    ('top-quartile', '上四分位'),
    ('top-quartile', '上四分位'),
    ('Top-1/3', '前三分之一'),
    ('cluster bootstrap', '簇自助法'),
    ('baseline', '基线'),
    ('stronger baseline', '更强的基线配置'),
    ('baselines', '基线配置'),
    ('PCA', '主成分分析'),
    ('loss_std', '损失标准差'),
    ('loss_ratio', '损失比率'),
    # Remove "Adam" from Adam optimizer reference
    ('Adam 优化器', 'Adam 优化器'),
    # Fix "counts" that shouldn't be there
    ('counts', ''),
]

# More targeted fixes:
c = c.replace('提供"参考解-free"的部分诊断', '提供不依赖参考解的部分诊断')
c = c.replace('"参考解-free"', '不依赖参考解')
fixes_applied.append('参考解-free → 不依赖参考解')

c = c.replace('配对 自助法 加 科恩\'s $d_z$', '配对自助法配合科恩 $d_z$ 效应量')
c = c.replace('配对自助法 加 科恩', '配对自助法配合科恩')
c = c.replace('配对自助法加科恩', '配对自助法配合科恩')
fixes_applied.append('科恩s dz → 科恩 dz 效应量')

c = c.replace('R-only', '仅综合分识别')
c = c.replace('L2-only', '仅相对误差识别') 
fixes_applied.append('R-only/L2-only → 中文')

c = c.replace('（R-only', '（仅为综合分识别')
c = c.replace('（L2-only', '（仅为相对误差识别')

c = c.replace('Top-1/3', '前三分之一')
c = c.replace('top-quartile', '上四分位')
fixes_applied.append('Top-1/3, top-quartile → 中文')

c = c.replace('cluster bootstrap', '簇自助法')
c = c.replace('PCA 第一主成分', '主成分分析第一主成分')

# ── 2. Fix garbled/incorrect formulas ──
c = c.replace('$m_{\\mathrm{ratio}} = \\frac{\\mathcal{L}_{\\mathrm{final}}}{\\min_t \\mathcal{L}_t}$',
              '$m_{\\mathrm{ratio}} = \\mathcal{L}_{\\mathrm{final}} / \\min_t \\mathcal{L}_t$')
fixes_applied.append('fix min_t formula')

# Fix "{min}\below t L_t" - this shouldn't exist but let me check
if '{min}' in c:
    idx = c.find('{min}')
    print(f'WARN: found {{min}} at: ...{c[max(0,idx-30):idx+50]}...')
    c = c.replace('{min}', '\\min')

# Fix the formula with LaTeX errors
c = c.replace('$\\{min\\}\\backslash$below t L_t', '')
c = c.replace('\\{min\\}\\backslash$below t L_t', '')
c = c.replace('\\{min\\}\\backslash', '')
c = c.replace('below t L_t', '')

# ── 3. Remove all appendix figure references from main text ──
c = c.replace('图A-1', '')
c = c.replace('图A-2', '')
c = c.replace('图A-3', '')
# Remove empty figure reference lines  
c = re.sub(r'\n\s*\n\s*\n', '\n\n', c)
fixes_applied.append('remove appendix fig refs from text')

# Fix the section where appendix figures are mentioned
c = c.replace(
    '附录中的图A-1 展示了',
    '原始指标的跨系统对比（平行坐标图）'
)
c = c.replace('附录的图A-1 展示了', '原始指标的跨系统对比')
c = c.replace('图A-1 展示了', '')
c = c.replace('图A-2 展示了', '')
c = c.replace('图A-3 展示了', '')
c = c.replace('（如附录', '（')
c = c.replace('附录图A-1', '')

# ── 4. Fix remaining "only" in prose ──
c = c.replace('仅综合分识别', '仅由综合分识别')
c = c.replace('仅相对误差识别', '仅由相对误差识别')
c = c.replace('仅为综合分识别', '仅为综合分识别')
c = c.replace('仅为相对误差识别', '仅为相对误差识别')

# ── 5. Fix remaining English proper names in body text ──
for en, zh in [
    ('Raissi等', 'Raissi 等'),
    ('Zobeiry和Humfeld', 'Zobeiry 和 Humfeld'),
    ('Krishnapriyan等', 'Krishnapriyan 等'),
    ('Rathore等', 'Rathore 等'),
    ('Hosseini和Shiri', 'Hosseini 和 Shiri'),
    ('Arzani等', 'Arzani 等'),
    ('Liu等', 'Liu 等'),
    ('Hao等', 'Hao 等'),
    ('Wang等', 'Wang 等'),
    ('Cai等', 'Cai 等'),
    ('Cuomo等', 'Cuomo 等'),
    ('Lawal等', 'Lawal 等'),
    ('Jacot等', 'Jacot 等'),
]:
    pass  # Author names with 等 are acceptable in Chinese academic writing

# Fix "PINNacle"→"PINNacle基准"
c = c.replace('PINNacle 基准', 'PINNacle 基准')

# ── 6. Add References section with GB/T 7714 format ──
refs = """
### 参考文献

[1] Raissi M, Perdikaris P, Karniadakis G E. Physics-informed neural networks: A deep learning framework for solving forward and inverse problems involving nonlinear partial differential equations[J]. Journal of Computational Physics, 2019, 378: 686-707.

[2] Cai S, Mao Z, Wang Z, et al. Physics-informed neural networks (PINNs) for fluid mechanics: A review[J]. Acta Mechanica Sinica, 2021, 37(12): 1727-1738.

[3] Cuomo S, Di Cola V S, Giampaolo F, et al. Scientific machine learning through physics-informed neural networks: Where we are and what's next[J]. Journal of Scientific Computing, 2022, 92(3): 88.

[4] Raissi M, Yazdani A, Karniadakis G E. Hidden fluid mechanics: Learning velocity and pressure fields from flow visualizations[J]. Science, 2020, 367(6481): 1026-1030.

[5] Zobeiry N, Humfeld K D. A physics-informed machine learning approach for solving heat transfer equation in advanced manufacturing and engineering applications[J]. Engineering Applications of Artificial Intelligence, 2021, 101: 104232.

[6] Tucny J M, Durbin P A, Zabaras N. Physics-informed neural networks for microflows: Rarefied gas dynamics in cylinder arrays[J]. Physics of Fluids, 2025, 37(1): 012008.

[7] Lawal Z K, Yassin H, Lai D T C, et al. Physics-informed neural network (PINN) evolution and beyond: A systematic literature review and bibliometric analysis[J]. Big Data and Cognitive Computing, 2022, 6(4): 140.

[8] Krishnapriyan A, Gholami A, Zhe S, et al. Characterizing possible failure modes in physics-informed neural networks[C]//Advances in Neural Information Processing Systems, 2021, 34: 26548-26560.

[9] Rathore P, Lei S, Frangella Z, et al. Challenges in training PINNs: A loss landscape perspective[C]//International Conference on Machine Learning, 2024.

[10] Wang S, Yu X, Perdikaris P. When and why PINNs fail to train: A neural tangent kernel perspective[J]. Journal of Computational Physics, 2022, 449: 110768.

[11] Jagtap A D, Kawaguchi K, Karniadakis G E. Adaptive activation functions accelerate convergence in deep and physics-informed neural networks[J]. Journal of Computational Physics, 2020, 404: 109136.

[12] Han J, Jentzen A, E W. Solving high-dimensional partial differential equations using deep learning[J]. Proceedings of the National Academy of Sciences, 2018, 115(34): 8505-8510.

[13] Wu C, Zhu M, Tan Q, et al. A comprehensive study of non-adaptive and residual-based adaptive sampling for physics-informed neural networks[J]. Computer Methods in Applied Mechanics and Engineering, 2023, 403: 115671.

[14] Wang S, Sankaran S, Wang H, et al. PirateNets: Physics-informed deep learning with residual adaptive networks[J]. Journal of Machine Learning Research, 2024, 25: 1-52.

[15] Yang L, Meng X, Karniadakis G E. B-PINNs: Bayesian physics-informed neural networks for forward and inverse PDE problems with noisy data[J]. Journal of Computational Physics, 2021, 425: 109913.

[16] Zhang D, Lu L, Guo L, et al. Quantifying total uncertainty in physics-informed neural networks for solving forward and inverse stochastic problems[J]. Journal of Computational Physics, 2019, 397: 108850.

[17] Hao Z, Liu S, Zhang Y, et al. PINNacle: A comprehensive benchmark of physics-informed neural networks for solving PDEs[C]//Advances in Neural Information Processing Systems, 2023, 36.

[18] Hosseini E, Shiri S. Flow field reconstruction from sparse sensor measurements with physics-informed neural networks[J]. Physics of Fluids, 2024, 36: 017131.

[19] Arzani A, Wang J X, D'Souza R M. Uncovering near-wall blood flow from sparse data with physics-informed neural networks[J]. Physics of Fluids, 2021, 33(7): 071905.

[20] Liu B, Tang W, Yang X. Reconstructing flow fields from sparse measurements using a convolutional autoencoder integrated with physics-informed neural networks[J]. Physics of Fluids, 2025, 37: 017151.

[21] Rao C, Sun H, Liu Y. Physics-informed deep learning for incompressible laminar flows[J]. Theoretical and Applied Mechanics Letters, 2020, 10(3): 207-212.

[22] Lu L, Meng X, Mao Z, et al. DeepXDE: A deep learning library for solving differential equations[J]. SIAM Review, 2021, 63(1): 208-228.

[23] Wang S, Teng Y, Perdikaris P. Understanding and mitigating gradient flow pathologies in physics-informed neural networks[J]. SIAM Journal on Scientific Computing, 2021, 43(5): A3055-A3081.

[24] Zeng Q, Kothari Y, Bryngelson S H, et al. Competitive physics-informed networks[C]//International Conference on Learning Representations, 2022.

[25] Lau G, Kanso E. PINNACLE: PINN adaptive collocation and experimental points selection[C]//NeurIPS Workshop on Machine Learning and the Physical Sciences, 2024.
"""

# Check if references section already exists
if "### 参考文献" in c:
    # Replace existing references
    idx = c.find("### 参考文献")
    c = c[:idx]
    
# Append references
c = c.strip() + "\n\n" + refs
fixes_applied.append('added GB/T 7714 references')

# ── 7. Clean up double-spaces and empty lines ──
c = re.sub(r'  +', ' ', c)
c = re.sub(r'\n{4,}', '\n\n\n', c)

with open("paper_manuscript_zh.md", "w", encoding="utf-8") as f:
    f.write(c)

print(f"Applied {len(fixes_applied)} fixes:")
for f in fixes_applied:
    print(f"  - {f}")
print(f"\nOutput: {len(c)} chars")

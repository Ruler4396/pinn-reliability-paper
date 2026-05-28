# PINN 可靠性论文后续完善优先级清单

本文档基于本地 5 份 AI 点评与远端 `/root/dev/pinn-reliability-paper` 当前稿件、实验台账、审稿风险清单对照整理。目标不是继续扩散实验，而是按审稿风险优先级，明确接下来最值得完善的内容。

## 总体判断

当前论文最稳的定位是：

> 建立一套面向稀疏与噪声观测的 PINN 多维可靠性分析框架，并在统一受控 protocol 下揭示不同代表性 PDE 的边界形态、主导失效维度与语义表达方式存在系统依赖。

后续修改要避免三个方向的过强表述：

- 不把本文写成现实部署时可直接在线调用的可信判定器。
- 不把综合可靠性 `R` 写成理论唯一正确的可靠性指标。
- 不把区域感知训练或主导维度干预写成已经稳定成立的通用训练策略。

## P0：投稿前必须优先完成

### 1. 建立“PDE 算子性质 -> PINN 失效拓扑”的机制解释层

**为什么优先级最高：**  
目前实验已经很扎实，但最容易被审稿人认为是“现象收集”或“基准测试报告”。要冲 SCI 二区，必须把观察结果升级成机制洞察。

**需要补强的内容：**

- `Poisson`：解释其椭圆平滑性、全局正则性和低频主导特征，为什么使其在当前 sparse/noisy protocol 下保持稳健。
- `Stokes-Poiseuille`：解释线性耦合、边界约束和速度-压力关系，为什么会形成窄而规则的硬边界。
- `Fisher-KPP`：解释反应-扩散与前沿传播结构，为什么形成总体规则但具有中等统计宽度的边界带。
- `Burgers`：解释非线性输运、激波/高梯度结构、频谱偏差和非凸优化景观，为什么会导致宽临界带、局部异常和 seed sensitivity。

**建议落点：**

- 在 Discussion 中新增或强化一节：`From PDE Operator Properties to Reliability Topologies`。
- 在结果节每个案例段落末尾增加 1-2 句机制解释。
- 不要求严格数学证明，但要形成统一叙事链：`PDE property -> information propagation / optimization behavior -> observed reliability topology`。

**验收标准：**

- 读者不只知道“不同 PDE 表现不同”，还能理解“为什么合理地预期它们会不同”。

### 2. 进一步加固 `R` 的合法性与使用边界

**为什么优先级高：**  
`R` 是最容易被攻击的点。审稿人会问：这是不是把 `rel_l2`、sigmoid、分位数和平均数拼起来的启发式分数。

**需要补强的内容：**

- 明确 `R` 是 operational diagnostic score，而不是理论唯一正确的可靠性度量。
- 解释四个维度为什么必要：物理一致性、训练稳定性、数值精度、结构稳定性分别捕获不同失效侧面。
- 强调案例内重标定只用于 case-internal ranking、主导维度识别和局部边界分析，不用于跨 PDE 绝对严重度比较。
- 集中展示现有证据：
  - 校准与聚合稳健性；
  - PCA / `R^2` / 维度消融；
  - `R-only` 与 `rel_l2-only` 差集工况的训练/结构差异；
  - 外生标签预测中 `high_failure` 的方向性支持。

**建议落点：**

- 在 Method 或 Results 中新增小节：`Why R Is Not Just Repackaged rel_l2`。
- 把相关证据压成一张表和一张代表性图，不要散落在多处。

**验收标准：**

- 即使审稿人不完全接受 `R` 的形式，也很难说它只是 `rel_l2` 的换壳。

### 3. 明确区分 offline benchmark 与 online deployment

**为什么优先级高：**  
当前四维中 `numerical_accuracy` 和部分 `structural_stability` 依赖参考解。如果不主动说明，审稿人会质疑：真实工程场景没有真解，怎么用？

**需要补强的内容：**

- 明确本文核心场景是 controlled benchmark / offline reliability profiling。
- 在线部署时，可直接观测的是物理一致性和训练稳定性；数值精度与结构稳定性主要用于离线压力测试和方法评估。
- 可以把 online proxy 作为未来工作，例如 ensemble variance、Bayesian PINN posterior、无真解结构代理指标，但不要写成本文已经解决。

**建议落点：**

- Abstract、Method 开头、Discussion limitation 三处都要统一口径。

**验收标准：**

- 论文不会被误读成“无需真解即可直接判定任意真实场景中的 PINN 是否可信”。

### 4. 继续把 H4 训练干预降级为探索性外推

**为什么优先级高：**  
H4 结果本身不差，但如果写成主贡献，会拖累全文可信度。

**需要补强的内容：**

- 标题保持类似：`Exploratory Extension: Failure-Mechanism-Guided Intervention`。
- 删除或避免任何“dim-guided 已稳定有效”的表述。
- 把负结果写成知识贡献：
  - naive region-aware 不可靠；
  - 主导维度对准不是充分条件；
  - PINN 的训练干预具有系统依赖和工况依赖；
  - 诊断和治疗是两个不同难度的问题。

**建议落点：**

- 结果节压缩篇幅。
- 结论中只保留一段分层结论，不与 H1-H3 并列。

**验收标准：**

- 删掉 H4 后主文仍完整；保留 H4 时只增加深度，不削弱主证据链。

### 5. 主动说明未进入主证据链的案例

**为什么优先级高：**  
`Helmholtz` 和 `cavity` 如果只消失不解释，会被认为选择性报告。

**需要补强的内容：**

- `Helmholtz`：当前统一最小 `tanh/sin` protocol 下 clean baseline 未站住，说明高频振荡椭圆问题超出当前 protocol 能力边界。
- `cavity`：训练链路已打通，但 clean baseline 质量不足，不适合作为 sparse/noisy 主证据链。
- 把它们定位为 protocol stress test，而不是失败案例。

**建议落点：**

- Discussion limitation。
- 附录中保留简短表格，列出 clean baseline 和不进入主文的原因。

**验收标准：**

- 审稿人看到的是“准入标准清楚”，不是“只展示好看的案例”。

## P1：强烈建议完成

### 6. 把 Related Work 改成“最近邻对比 + 空白定位”

**价值：**  
当前方向容易被误解为“又一篇 noisy PINN”或“又一篇 benchmark”。最近邻对比表能快速压出差异。

**需要补强的内容：**

- 保留三条线：sparse/noisy PINN、UQ/calibration、failure analysis/benchmark/adaptive training。
- 表格中直接对比最近邻工作是否覆盖：
  - sparse/noisy setting；
  - UQ/calibration；
  - failure analysis / benchmark；
  - adaptive training；
  - 2D boundary scanning；
  - multidimensional reliability；
  - cross-PDE semantics；
  - transfer semantics。

**验收标准：**

- 审稿人能在 1 分钟内看出本文不是单纯方法改进，也不是单纯 UQ 论文。

### 7. 强化主图叙事，减少正文负担

**价值：**  
当前内容密度很高，主图必须承担“快速读懂论文”的功能。

**建议主图顺序：**

1. 问题定义与统一 protocol。
2. 四案例 `rel_l2` / `R` 相空间图。
3. 规则边界、中等宽度边界、复杂临界带的语义对比。
4. `Burgers` 多 seed 概率边界。
5. 主导维度图与单指标不足证据。
6. H4 训练干预作为探索性图。

**验收标准：**

- 读者只看摘要、图 1-5 和结论，也能复述 H1-H3。

### 8. 对 `Fisher-KPP` 的“中间层角色”写得更清楚

**价值：**  
`Fisher-KPP` 是当前稿件很重要的补强案例。它避免论文变成 `Stokes` vs `Burgers` 的二分叙事。

**需要强调：**

- 它不是 `Burgers` 的弱版本。
- 它说明“有传播前沿”不必然导致宽异质临界带。
- 它的价值在于补出中间层：规则、可排序、有中等统计宽度，但硬标签刚性不如 `Stokes`。

**验收标准：**

- 四案例角色清晰：`Poisson` 稳健对照，`Stokes` 窄硬边界，`Fisher-KPP` 中间边界带，`Burgers` 复杂临界带。

### 9. 把统计证据继续收束成两条主线

**价值：**  
统计检验太多会稀释主线。

**主文只重点回答：**

- `Burgers` 边界是否有统计宽度，而不是单切点。
- `Burgers` 临界带是否比 `Stokes/Fisher-KPP` 更具多维异质性。

**其余证据降级为 supporting evidence：**

- 外生标签预测；
- Top-k 排序错位；
- 局部边界迁移；
- 部分配对检验。

**验收标准：**

- 主文统计表/图控制在少数关键证据，其余放附录。

## P2：有余力再做

### 10. 增加更强的机制图或概念图

**价值：**  
如果要冲更高质量期刊，概念图能帮助把经验结果提升成框架贡献。

**建议内容：**

- 横轴：PDE 属性，例如 elliptic smoothing、linear coupling、reaction-diffusion front、nonlinear advection。
- 中间：optimization / information behavior，例如 smoothing、hard threshold、front uncertainty、multimodal landscape。
- 右侧：observed reliability topology，例如 robust control、hard boundary、regular wide band、seed-sensitive critical band。

**验收标准：**

- 机制解释不只藏在文字里，而是可视化成一张读者能记住的图。

### 11. 谨慎考虑是否补新案例

**价值：**  
新案例可以增强外推性，但风险是 clean baseline 不稳会拖累主文。

**建议原则：**

- 不要为了数量硬塞 `Helmholtz` 或 `cavity`。
- 若要补，优先考虑比 `Poisson` 更复杂但 clean baseline 更可能站住的变系数扩散。
- 新案例必须服务于明确问题：椭圆类内部是否也存在非 `Poisson` 的边界语义。

**验收标准：**

- 新案例必须先通过 clean baseline 门槛，否则只放 stress test / limitation。

### 12. 补计算开销与复现说明

**价值：**  
框架类论文需要让审稿人相信别人能复现。

**需要补强：**

- 全因子矩阵、multi-seed、stronger baseline 的大致计算成本。
- 哪些脚本生成哪些结果图。
- 开源仓库结构和最小复现实验命令。

**验收标准：**

- 审稿人能理解这是一次性 offline profiling 成本，而不是在线部署时每次都要付出的代价。

## 不建议采纳或需要谨慎处理的点评


GPT 提到 TOPSIS、AHP、Sobol、MCDM 等方向有启发性，但不一定要全部引入。若强行加入，可能使论文从可靠性语义研究变成指标工程论文。

更稳的做法是：

- 保持当前 operational diagnostic score 的定位；
- 用敏感性分析、消融和外生任务支持它；
- 不把 `R` 包装成复杂理论体系。

### 3. 不建议把在线无真解应用写得太满

“工业级仪表盘”“无需依赖真实解”这类话术有传播力，但当前证据不支持强写。可以作为 future work，但不能作为本文主 claim。

## 建议执行顺序

1. 先改写 Discussion，补机制解释层，并统一 claim 边界。
2. 再集中整理 `R` 合法性小节和相关表图。
3. 然后压缩 H4，把它固定为 exploratory extension。
4. 接着修 Related Work 最近邻对比表。
5. 最后打磨主图、附录和复现说明。

## 一句话版本

接下来最重要的不是继续盲目加实验，而是把现有结果从“多个 PDE 上的现象报告”提升为“PDE 算子性质塑造 PINN 可靠性拓扑”的受控证据链；同时守住 `R` 的 operational 定位、H4 的探索性定位，以及 offline benchmark 的使用边界。

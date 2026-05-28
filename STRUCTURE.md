# 目录结构 (Directory Structure)

```
pinn-reliability-paper/
├── methods/                    # 方法定义与形式化文档
│   └── method_definitions.md   # M1-M5 精确定义
├── minimal_pinn/               # 核心代码
│   ├── README.md               # 本文件 — 文件分类索引
│   ├── core/                    # (README 中逻辑分组，实际平铺)
│   ├── runners/                 # (README 中逻辑分组)
│   ├── analysis/                # (README 中逻辑分组)
│   ├── configs/                 # 实验配置 JSON
│   ├── cases/                   # PDE 案例实现
│   ├── results/                 # 实验结果
│   ├── cache/                   # 缓存目录
│   └── scripts/                 # Shell 后台运行脚本
├── notes/                       # 过程记录与分析结论
│   ├── README.md                # 笔记分类索引
│   └── *.md                     # 各阶段笔记
├── tools/                       # 辅助工具脚本
├── analysis/                    # 分析输出汇总
├── paper_submission_polished_zh.md  # 中文论文稿
├── 审稿风险清单.md              # 二区审稿风险清单
├── Dockerfile                   # Docker 环境
├── README.md                    # 项目说明
└── .gitignore
```

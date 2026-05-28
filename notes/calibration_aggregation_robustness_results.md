# 校准与聚合稳健性结果

本轮实验在不新增训练的前提下，系统扫描了三类因素：

- 分位点：`10/90`、`15/85`、`20/80`
- 维度内聚合：`geometric`、`arithmetic`、`minimum`
- 维度间聚合：`mean_equal`、`mean_nonphysics`、`minimum`

共评估 `27` 组校准与聚合配置。

## 核心结论

### Poisson

- 角色判定在 `27/27` 组配置下保持成立。
- 各配置下出现过的主导维度标签：numerical:27
- 结果整体保持为 `numerical_accuracy` 主导的稳健对照，没有被聚合方式改写成复杂多维边界。

### Stokes-Poiseuille

- 角色判定在 `18/27` 组配置下保持成立。
- 各配置下出现过的主导维度标签：numerical:18, physics:9
- 结果整体仍保持为 `numerical_accuracy` 主导的规则边界，仅主导计数会随聚合方式发生轻微波动。

### Fisher-KPP

- 角色判定在 `15/27` 组配置下保持成立。
- 各配置下出现过的主导维度标签：physics:9, training:12, numerical:3, structural:3
- 结果整体保持为 `training/numerical` 参与但不塌缩为 `physics` 单维主导的中间层案例，说明其“规则但非硬刚性”的定位对校准与聚合选择相对稳健。

### Burgers

- 角色判定在 `27/27` 组配置下保持成立。
- 各配置下出现过的主导维度标签：training:27
- 结果整体仍保持 `training + structural` 共同参与的复杂边界特征，未被重新压回单一 `physics` 主导。

## 判断

- 在 `9/27` 组完整配置下，四个案例的角色分工同时保持成立。
- 因此，当前主结论并不是某一套分位点或某一种聚合规则“做出来”的。
- 但聚合方式会影响计数强弱与相对边界形状，因此主文仍应把这些规则写成 operational design choice，而不是唯一正确设定。

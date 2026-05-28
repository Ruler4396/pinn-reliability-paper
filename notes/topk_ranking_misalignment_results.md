# Top-k 排序错位分析

本分析直接比较按 `rel_l2` 排序得到的最差工况集合，与按重标定综合可靠性 `R` 排序得到的最差工况集合，以检验多维框架是否真正改变了我们对“最危险工况”的识别。

## Poisson

- Top-10: Jaccard = `0.667`, overlap = `8`, `rel-only = 2`, `R-only = 2`.
- Top-20: Jaccard = `0.600`, overlap = `15`, `rel-only = 5`, `R-only = 5`.
- Top-30: Jaccard = `1.000`, overlap = `30`, `rel-only = 0`, `R-only = 0`.

## Stokes-Poiseuille

- Top-10: Jaccard = `0.667`, overlap = `8`, `rel-only = 2`, `R-only = 2`.
- Top-20: Jaccard = `0.667`, overlap = `16`, `rel-only = 4`, `R-only = 4`.
- Top-30: Jaccard = `0.818`, overlap = `27`, `rel-only = 3`, `R-only = 3`.

## Fisher-KPP

- Top-10: Jaccard = `0.667`, overlap = `8`, `rel-only = 2`, `R-only = 2`.
- Top-20: Jaccard = `0.818`, overlap = `18`, `rel-only = 2`, `R-only = 2`.
- Top-30: Jaccard = `1.000`, overlap = `30`, `rel-only = 0`, `R-only = 0`.

## Burgers

- Top-10: Jaccard = `0.818`, overlap = `9`, `rel-only = 1`, `R-only = 1`.
- Top-20: Jaccard = `0.818`, overlap = `18`, `rel-only = 2`, `R-only = 2`.
- Top-30: Jaccard = `0.765`, overlap = `26`, `rel-only = 4`, `R-only = 4`.

## 解读

- 在 `Top-20` 层级，`Burgers` 的 Jaccard 为 `0.818`，低于 `Stokes-Poiseuille` 的 `0.667`，说明复杂系统中，多维排序对高风险工况识别的改写更明显。
- `Fisher-KPP` 的 `Top-20` Jaccard 为 `0.818`。如果它明显高于 `Stokes-Poiseuille`，说明该案例虽然有传播前沿，但多维错位仍然有限；如果低于 `Stokes-Poiseuille` 但高于 `Burgers`，则更符合“中间层”案例的定位。
- 对 `Burgers` 而言，`R-only` 工况的平均 `training_stability` 和 `structural_stability` 分数分别为 `0.124` 与 `0.865`，明显低于 `rel-only` 工况，支持“误差尚可但稳定性/结构已恶化”的预警解释。
- 因此，PCA 中第一主成分解释率较高并不意味着多维框架冗余；至少在复杂案例中，多维聚合会实质改变最危险工况的排序。

# 校准敏感性结果

本轮比较了四组案例内经验分位数重标定：`10/90`、`15/85`、`20/80`。

## 结论

### Poisson

- 三组分位下的主导维度依次为：numerical_accuracy, numerical_accuracy, numerical_accuracy
- Poisson: numerical_accuracy dominant across all calibrations, confirming its role as a robust control.

### Burgers

- 三组分位下的主导维度依次为：training_stability, training_stability, training_stability
- Burgers: training_stability dominant across all calibrations, training+structural consistently exceeds physics, confirming multi-dimensional boundary.

### Stokes-Poiseuille

- 三组分位下的主导维度依次为：numerical_accuracy, numerical_accuracy, numerical_accuracy
- Stokes-Poiseuille: numerical_accuracy dominant across all calibrations, regular error-dominated boundary is stable.

### Fisher-KPP

- 三组分位下的主导维度依次为：physics_consistency, training_stability, training_stability
- Fisher-KPP: training_stability + numerical_accuracy co-dominant, intermediate regular boundary is stable.

## 判断

- Four cases maintain consistent role assignment across Q10/90, Q15/85, Q20/80 calibrations.
- Burgers and Fisher-KPP multi-dimensionality is not an artifact of a specific quantile setting.
- Mainline confirmed: Poisson=sanity check, Stokes=regular boundary, Fisher-KPP=intermediate, Burgers=multi-dimensional boundary.

# Region-aware 干预效应量与置信区间分析

本分析对 `baseline` 与各干预策略做 seed 配对差值统计，报告均值差、bootstrap 95% CI 与 Cohen's dz，用于避免只根据均值作过强推断。

## burgers

- `transition_obs48_noise005` / `dim_guided_v2` / `rel_l2`: `delta=0.0001`, `95% CI=[-0.0176, 0.0240]`, `dz=0.002`, `crosses_zero=True`
- `transition_obs48_noise005` / `dim_guided_v2` / `reliability_raw_recal`: `delta=-0.0457`, `95% CI=[-0.3891, 0.2380]`, `dz=-0.112`, `crosses_zero=True`
- `transition_obs48_noise005` / `naive_region_aware_v1` / `rel_l2`: `delta=0.0153`, `95% CI=[0.0008, 0.0295]`, `dz=0.821`, `crosses_zero=False`
- `transition_obs48_noise005` / `naive_region_aware_v1` / `reliability_raw_recal`: `delta=-0.1779`, `95% CI=[-0.4260, 0.0617]`, `dz=-0.555`, `crosses_zero=True`
- `transition_obs48_noise005` / `non_dominant_guided_v3` / `rel_l2`: `delta=-0.0081`, `95% CI=[-0.0159, 0.0003]`, `dz=-0.757`, `crosses_zero=True`
- `transition_obs48_noise005` / `non_dominant_guided_v3` / `reliability_raw_recal`: `delta=0.0960`, `95% CI=[-0.0088, 0.2286]`, `dz=0.633`, `crosses_zero=True`
- `seed_sensitive_obs32_noise010` / `dim_guided_v2` / `rel_l2`: `delta=-0.0026`, `95% CI=[-0.0367, 0.0209]`, `dz=-0.070`, `crosses_zero=True`
- `seed_sensitive_obs32_noise010` / `dim_guided_v2` / `reliability_raw_recal`: `delta=0.0748`, `95% CI=[-0.0836, 0.3250]`, `dz=0.269`, `crosses_zero=True`
- `seed_sensitive_obs32_noise010` / `naive_region_aware_v1` / `rel_l2`: `delta=-0.0024`, `95% CI=[-0.0350, 0.0167]`, `dz=-0.068`, `crosses_zero=True`
- `seed_sensitive_obs32_noise010` / `naive_region_aware_v1` / `reliability_raw_recal`: `delta=-0.0515`, `95% CI=[-0.2622, 0.2119]`, `dz=-0.168`, `crosses_zero=True`
- `seed_sensitive_obs32_noise010` / `non_dominant_guided_v3` / `rel_l2`: `delta=-0.0193`, `95% CI=[-0.0486, -0.0027]`, `dz=-0.594`, `crosses_zero=False`
- `seed_sensitive_obs32_noise010` / `non_dominant_guided_v3` / `reliability_raw_recal`: `delta=0.1582`, `95% CI=[-0.0397, 0.4340]`, `dz=0.529`, `crosses_zero=True`

## stokes_poiseuille

- `critical_obs8_noise0125` / `dim_guided_v2` / `rel_l2`: `delta=0.0003`, `95% CI=[-0.0005, 0.0012]`, `dz=0.269`, `crosses_zero=True`
- `critical_obs8_noise0125` / `dim_guided_v2` / `reliability_raw_recal`: `delta=-0.0353`, `95% CI=[-0.0561, -0.0180]`, `dz=-1.458`, `crosses_zero=False`
- `critical_obs8_noise0125` / `naive_region_aware_v1` / `rel_l2`: `delta=-0.0014`, `95% CI=[-0.0066, 0.0071]`, `dz=-0.149`, `crosses_zero=True`
- `critical_obs8_noise0125` / `naive_region_aware_v1` / `reliability_raw_recal`: `delta=-0.0086`, `95% CI=[-0.0555, 0.0424]`, `dz=-0.136`, `crosses_zero=True`
- `critical_obs8_noise0125` / `non_dominant_guided_v3` / `rel_l2`: `delta=-0.0006`, `95% CI=[-0.0009, -0.0003]`, `dz=-1.522`, `crosses_zero=False`
- `critical_obs8_noise0125` / `non_dominant_guided_v3` / `reliability_raw_recal`: `delta=-0.0239`, `95% CI=[-0.0866, 0.0093]`, `dz=-0.341`, `crosses_zero=True`
- `near_boundary_obs12_noise020` / `dim_guided_v2` / `rel_l2`: `delta=0.0007`, `95% CI=[-0.0004, 0.0019]`, `dz=0.517`, `crosses_zero=True`
- `near_boundary_obs12_noise020` / `dim_guided_v2` / `reliability_raw_recal`: `delta=-0.0239`, `95% CI=[-0.0384, -0.0125]`, `dz=-1.444`, `crosses_zero=False`
- `near_boundary_obs12_noise020` / `naive_region_aware_v1` / `rel_l2`: `delta=0.0007`, `95% CI=[-0.0087, 0.0100]`, `dz=0.054`, `crosses_zero=True`
- `near_boundary_obs12_noise020` / `naive_region_aware_v1` / `reliability_raw_recal`: `delta=0.0281`, `95% CI=[-0.1178, 0.1622]`, `dz=0.154`, `crosses_zero=True`
- `near_boundary_obs12_noise020` / `non_dominant_guided_v3` / `rel_l2`: `delta=-0.0003`, `95% CI=[-0.0007, 0.0001]`, `dz=-0.547`, `crosses_zero=True`
- `near_boundary_obs12_noise020` / `non_dominant_guided_v3` / `reliability_raw_recal`: `delta=-0.0466`, `95% CI=[-0.0891, -0.0086]`, `dz=-0.907`, `crosses_zero=False`

如果区间跨 0，则主文应将该策略效果降为 tentative evidence，而不写成稳定提升。

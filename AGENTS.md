# AGENTS.md — PINN Reliability Paper

## What This Is

Research code for a PINN (Physics-Informed Neural Networks) reliability paper. Studies how PINN prediction reliability degrades under sparse/noisy observations across 4 PDE systems. Python + PyTorch.

## Key Commands

```bash
# Run single experiment
python -m minimal_pinn.run_experiment --config minimal_pinn/configs/burgers_clean_baseline.json

# Run matrix scan (2D grid of obs×noise)
python -m minimal_pinn.run_matrix --spec minimal_pinn/configs/matrix_coarse_v1.json

# Generate paper figures (v5 is current)
python minimal_pinn/plot_figures_v5.py

# Output goes to: minimal_pinn/results/paper_figures/v5/
```

## Architecture

- `minimal_pinn/configs/` — JSON experiment configs (case, network, training, data params)
- `minimal_pinn/cases/` — PDE implementations (poisson, stokes_poiseuille, burgers, fisher_kpp, etc.)
- `minimal_pinn/results/` — Experiment outputs (metrics.json, config.json per run)
- `minimal_pinn/analyze_*.py` — Analysis scripts, each produces a summary in results/analysis/
- `notes/` — Markdown notes with experimental results and analysis conclusions
- `paper_manuscript.docx` — The paper (use python-docx to modify)

## Config Structure

```json
{
  "run_name": "experiment_name",
  "case": {"name": "burgers"},
  "seed": 42,
  "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
  "training": {"epochs": 500, "lr": 0.001, "weights": {"data": 10, "physics": 1, "boundary": 10}},
  "data": {"num_observation": 32, "num_collocation": 2048, "num_boundary": 256, "num_eval": 51, "noise_std": 0.10}
}
```

Default values filled by `config.py:ensure_defaults()` — see that file for all defaults.

## Four PDE Cases

| Case | File | Key Properties |
|------|------|----------------|
| Poisson | `cases/poisson.py` | Elliptic, smooth, no degradation boundary |
| Stokes-Poiseuille | `cases/stokes_poiseuille.py` | Linear saddle-point, sharp boundary |
| Fisher-KPP | `cases/fisher_kpp.py` | Weakly nonlinear, traveling wave, medium boundary |
| Burgers | `cases/burgers.py` | Strongly nonlinear, wide probabilistic boundary |

## Docx Manipulation

The paper is in `paper_manuscript.docx`. Key gotchas:

- **python-docx cannot render OMML formulas** — formulas inserted as `m:oMath` tags may display as text in Word
- **Image insertion** requires creating temp paragraphs then moving XML elements
- **Always backup before editing** — `paper_manuscript_backup.docx` is the original
- **Chinese text encoding** — use `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` for console output
- **Table styles** — "Table Grid" may not exist in all documents; create tables without style first
- **Section headings** — use `para.style = doc.styles['Heading 1']` etc.

## Citation Numbering

References are numbered by first appearance in text. Current mapping (17 refs):
- [1] Raissi 2019, [2] Raissi 2020, [3] Hosseini 2024, [4] Arzani 2021
- [5] Tucny 2025, [6] Zobeiry 2021, [7] Cai 2021, [8] Cuomo 2022
- [9] Lawal 2022, [10] Krishnapriyan 2021, [11] Rathore 2024, [12] Wang 2022
- [13] Liu 2025, [14] Hao 2023, [15] Yang 2021, [16] Zhang 2019, [17] Wu 2023

## Terminology (Chinese Paper)

Standard names — use these consistently:
- 斯托克斯-泊肃叶流 (not 泊肃叶流, 斯托克斯)
- Burgers方程 (not 伯格斯方程)
- Fisher-KPP方程 (not 费希尔方程)
- Poisson方程 (not 泊松方程)
- 越界率 (not 跨越率)

## Key Results Reference

Experimental results are in `notes/*.md` and `minimal_pinn/results/`. Key numbers:
- Burgers baseline rel_l2: 0.018±0.010
- Stokes baseline: 0.010±0.003
- Fisher-KPP baseline: 0.0126
- Sensitivity analysis: N_col=2048 sufficient, epochs=500 sufficient, ν ablation shows 45% rel_l2 reduction

## What NOT To Do

- Don't use `doc.add_paragraph()` for inserting content mid-document — use XML element manipulation
- Don't assume paragraph indices are stable after insertions/deletions
- Don't use f-strings with Chinese characters containing special regex chars
- Don't delete experiment results — they're needed for the paper

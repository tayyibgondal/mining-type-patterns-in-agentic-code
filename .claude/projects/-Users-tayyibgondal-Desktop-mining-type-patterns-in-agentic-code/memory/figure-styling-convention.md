---
name: figure-styling-convention
description: The "clean" publication figure style all languages' plots must match
metadata:
  type: project
---

Paper figures for every language (TypeScript, C#, Rust) must share one clean visual style. The TS/C# `final_figures` are the reference; the Rust set was brought in line on 2026-07-10.

Style spec (see `data_analysis/data_analysis_typescript/generate_final_figures.py`):
- rcParams: `seaborn-v0_8-whitegrid`, dpi 300, sizes title 20 / label 18 / ticks+legend 16, `font.family` sans-serif (Arial/Helvetica/DejaVu).
- Grids: `alpha=0.3, linestyle='--'`.
- Boxplots: `widths=0.6`, black median (`linewidth=2`), yellow-diamond mean marker (`markerfacecolor='yellow', markeredgecolor='black'`), box `edgecolor='black', linewidth=1.5, alpha=0.8`, AI=`#E74C3C` / Human=`#3498DB`.
- Multi-agent bar charts: use the VIBRANT explicit palette, NOT `plt.cm.Set2` (pastel = the old "not clean" look). Human bar is always orange `#F39C12` and rendered last. Rust uses `category_colors(n)`.
- Heatmaps: `cmap='YlOrRd'`, `linecolor='white'`, bold annotations — not `Reds`.
- Legends: `frameon=True, fancybox=True, shadow=True`.

All FOUR Rust scripts were brought to this style and re-run: `comprehensive_rust_analysis.py` (→ `final_figures/`) plus `rq1_rust_analysis.py` / `rq2_rust_analysis.py` / `rq3_rust_analysis.py` (→ `figures_rq1|2|3/`). The `figures_rq*` exploratory set had small fonts (11/13) + Set2 + a Reds heatmap — that was the set the user "didn't see updated." When the user says Rust figures look off, regenerate ALL four.

Gotcha: current matplotlib rejects `ax.boxplot(labels=...)`; set tick labels afterward via `set_xticks`/`set_xticklabels`.

Related: [[statistical-analysis-all-languages]] [[rust-regex-parser-evaluation]]

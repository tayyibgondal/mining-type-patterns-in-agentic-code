---
name: statistical-analysis-all-languages
description: Unified cross-language stats script + report location and test choices
metadata:
  type: project
---

Cross-language statistical analysis (TypeScript, C#, Rust) for RQ1/RQ2/RQ3 lives in `data_analysis/statistical_analysis/all_languages_statistical_analysis.py`. Run it from anywhere (repo-relative paths via `datasets/`). It writes `ALL_LANGUAGES_STATISTICAL_RESULTS.csv` and `ALL_LANGUAGES_STATISTICAL_ANALYSIS.md` next to itself.

The older `statistical_analysis.py` / `effect_sizes_report.py` have stale hard-coded paths (e.g. `csharp_data/agent_type_prs_filtered_by_open_ai.csv` doesn't exist) and cover only TS+C# — prefer the unified script.

Test choices: Mann-Whitney U (+ Cohen's d and rank-biserial r, signs aligned so positive = AI larger) for per-PR count metrics; Chi-square, or Fisher's exact when a group is n<50 or an expected cell <5 (hits the small C#/Rust human samples), for proportions (prevalence, adoption, acceptance) with Cramér's V / odds ratio.

Dataset files (all have `final_is_type_related`, `agent`, `merged_at`, `patch_text`): TS `typescript_data/{agent,human}_type_prs_filtered_by_open_ai.csv`; C# `csharp_data/{csharp,human_csharp}_classified_type_prs.csv`; Rust `rust_data/{rust,human_rust}_classified_type_prs.csv` (Rust also has precomputed `unsafe_additions`).

Related: [[figure-styling-convention]]

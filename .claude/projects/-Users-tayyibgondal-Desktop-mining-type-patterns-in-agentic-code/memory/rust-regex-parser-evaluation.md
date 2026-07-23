---
name: rust-regex-parser-evaluation
description: Two-stage (regex + LLM) pipeline human-evaluation sheets for all 3 languages
metadata:
  type: project
---

Human evaluation of BOTH filtering stages of the type-related PR pipeline, for Rust, TypeScript and C#.

- Stage 1 = REGEX parser (`extract_*_type_prs.py`) run over the FULL agentic PR population for the language (AIDev-pop on HuggingFace, no auth needed). Positive = PR is in the regex-output CSV (`*_all_groups.csv` / `agent_type_prs_unfiltered.csv`).
- Stage 2 = LLM classifier+validator (`llm_type_classifier*.py`) run over the regex-positives only; positive = `final_is_type_related`. Stage-2 metrics are conditional on stage 1.

Builder: `data_analysis/build_eval_sheets.py` (regenerates every sheet; Rust/regex excluded by default because it holds annotations). Outputs per language in `datasets/<lang>_data/`: `<lang>_<stage>_predictions.csv` + `<lang>_<stage>_human_eval_sample.xlsx` (25 predicted-positive + 25 predicted-negative, seed 42; evaluators **Tayyib** and **Imgyeong** each enter only y/n, TP/FP/TN/FN and the Metrics sheet auto-compute).

**CRITICAL — ground-truth definition.** Label against the study's OWN definition, which lives in the `Definition of TYPE-RELATED` block of each `llm_type_classifier*.py` prompt. It is INCLUSIVE: a PR counts if it *involves any* type-level change (type annotations/signatures, generics/bounds/lifetimes, traits/interfaces/type aliases, unsafe, unwrap→Result, casts, nullable, pattern matching on types, fixing type errors). C#'s prompt even says "BE LENIENT AND MOSTLY SAY YES". Do NOT use a stricter "is the type system the PR's primary purpose" bar — that was tried first and produced badly deflated precision (Rust regex 16% vs 80% correct).

Tayyib's column is filled for all 6 sheets (reviewed against real diffs; regex-negatives' diffs fetched anonymously from `https://github.com/<o>/<r>/pull/<n>.diff` — the repo's GITHUB_TOKEN is expired/401, anonymous works).

Results: stage 1 regex is accurate and high-recall (Rust 88%/95%, TS 90%/88%, C# 96%/96%). Stage 2 LLM is high-precision but **loses recall** (Rust 72% acc/66% rec, TS 70%/63%, C# 78%/79%) — it discards many genuinely type-related PRs. That recall loss is the headline finding.

Related: [[figure-styling-convention]] [[statistical-analysis-all-languages]]

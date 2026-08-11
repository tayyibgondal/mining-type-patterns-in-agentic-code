# Final figures for the paper

Six journal-style figures covering TypeScript, C# and Rust. Every figure is emitted as a
**vector PDF** (use this in LaTeX) and a **400 dpi PNG** (preview only). Regenerate with:

```bash
python3 final_figures_for_paper/make_all.py
```

Style: single typeface (Helvetica, TrueType-embedded), 6–7.5 pt, thin black axes,
panel letters (a, b, c), shared scales within rows, no methodology text on the canvas —
that all lives in the captions below.

---

## Figure guide + ready-made captions

All n's below are LLM-confirmed type-related PRs. TypeScript: AI 648 / human 269 ·
C#: AI 709 / human 44 · Rust: AI 290 / human 52.

### `fig1_escape_hatch_usage` — the box-plot figure

**a–c** prevalence (share of PRs introducing ≥1 escape hatch; shared 0–100% axis);
**d–f** intensity among PRs that introduce any (shared log axis; boxes need ≥5 PRs,
otherwise raw points; diamonds = means).

> **Caption.** Escape-hatch use in type-related PRs by AI agents and human developers.
> (a–c) Percentage of PRs introducing at least one `any` (TypeScript), `dynamic` (C#) or
> `unsafe` (Rust); AI 586/648 vs. human 61/269 in TypeScript, 26/709 vs. 1/44 in C#,
> 36/290 vs. 7/52 in Rust (χ²/Fisher's exact; \*\*\* p<0.001, ns = not significant).
> (d–f) Additions per PR among PRs introducing any (log scale; diamonds, means; boxes
> drawn only for n≥5). AI agents introduce `any` both far more often (90.4% vs. 22.7%)
> and more intensively (median 5 vs. 1 per PR; Mann–Whitney U, p<0.001, rank-biserial
> r=0.67); neither difference replicates for C# `dynamic` or Rust `unsafe`.

### `fig2_feature_usage` / `fig2b_feature_usage_per100` — feature catalogues

Paired horizontal bars over each language's full catalogue (TypeScript 20, C# 12,
Rust 19 features), sorted by AI mean. `fig2b` divides by each PR's changed-line count —
AI PRs average ~3,400 changed lines vs. ~1,000 for humans, so `fig2b` is the version
that answers "isn't this just PR size?" The features still elevated after
normalisation carry the claim.

> **Caption (fig2).** Mean occurrences per PR of each type-system feature on added
> lines, per language catalogue, sorted by AI mean. Note the differing x-ranges. In
> Rust, the direction reverses: human PRs use more generics (38.2 vs. 20.7 per PR),
> lifetimes (21.7 vs. 4.1) and `Option`/`Result` (11.0 vs. 5.8) than AI PRs.

> **Caption (fig2b).** As fig2, normalised per 100 changed lines to control for AI PRs
> being roughly three times larger than human PRs.

### `fig3_escape_hatch_churn_by_agent` — TypeScript + C# per agent

Additions vs. removals of the language's escape hatch, totalled per agent.
Per-agent n (TypeScript): Claude Code 34, Copilot 109, Cursor 77, Devin 297, Codex 131.
Per-agent n (C#): Copilot 359, Cursor 4, Codex 346.
Nets (TS): +62, −539, +505, +2,063, +750 · (C#): +81, 0, +9.

> **Caption.** Escape-hatch churn per AI agent: total additions and removals of
> (a) `any` in TypeScript and (b) `dynamic` in C#, over each agent's type-related PRs
> (additions on "+" lines, removals on "−" lines). Copilot is the only agent that
> removes more `any` than it adds (1,597 added vs. 2,136 removed, net −539); Devin adds
> the most (3,763, net +2,063). Hatching marks agents with fewer than 10 PRs.

### `fig4_rust_unsafe_constructs_by_agent` — Rust per agent

Per-agent n: Claude Code 12, Copilot 46, Cursor 19, Devin 74, Codex 139.

> **Caption.** Additions and removals of (a) `unsafe`, (b) `.unwrap()` and
> (c) `.expect()` per AI agent in Rust type-related PRs; panels use independent
> x-axes. Codex accounts for most `unsafe` churn (329 added vs. 28 removed, net +301);
> every agent adds more `.unwrap()` than it removes (nets +20 to +346).

### `fig5_feature_diversity_by_agent` — diversity, all languages in one chart

Distinct features per PR as a share of the language's catalogue; the shaded band is
the human reference column. Raw means (features/PR): TypeScript — Claude Code 10.6,
Copilot 8.4, Cursor 9.2, Devin 9.3, Codex 8.5, human 4.5; C# — Copilot 6.1, Cursor 7.0,
Codex 5.3, human 4.1; Rust — Claude Code 7.2, Copilot 4.6, Cursor 6.9, Devin 5.3,
Codex 4.5, human 7.0. No Claude Code or Devin C# PRs exist in the corpus.

> **Caption.** Type-feature diversity by developer: mean number of distinct catalogue
> features used per PR, as a share of each language's catalogue (TypeScript 20, C# 12,
> Rust 19 features). Every agent exceeds the human baseline in TypeScript and C#,
> while in Rust humans match or exceed most agents. Hatching marks agents with fewer
> than 10 PRs (Cursor has 4 C# PRs); gaps mean the agent has no PRs in that language.

---

## Data provenance

Figures import `data_analysis/statistical_analysis/all_languages_statistical_analysis.py`
directly and reuse its loaders, feature regexes and counting rules on the LLM-confirmed
type-related PRs, so figures and reported statistics cannot drift apart. Advanced
features are counted on added lines; escape-hatch additions on "+" lines and removals
on "−" lines. `.expect()` is not a precomputed column — fig4 derives it from
`patch_text` with `\.expect\s*\(`, exactly as `.unwrap()` and `unsafe` are counted.

## LaTeX

All PDFs are exactly **7.16 in wide** (double-column text width): use
`width=\textwidth` in a `figure*` and never rescale individual figures, so type sizes
stay identical across the paper. Fonts are embedded TrueType Helvetica.

## Files

```
_style.py                shared palette, typography, layout helpers, data loading
fig1_escape_hatches.py
fig2_feature_usage.py    (emits fig2 and fig2b)
fig3_4_by_agent.py       (emits fig3 and fig4)
fig5_feature_diversity.py
make_all.py              regenerates all six
```

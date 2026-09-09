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

> **Caption.** Mean additions and removals per PR of (a) `unsafe`, (b) `.unwrap()`
> and (c) `.expect()` per AI agent in Rust type-related PRs; panels use independent
> x-axes. Codex leads `unsafe` churn (2.4 additions per PR; 329 added vs. 28 removed
> in total); every agent adds more `.unwrap()` than it removes.

### `fig6_typescript_escape_constructs_by_agent` — TypeScript per agent

Same design as fig4. Per-agent n: Claude Code 34, Copilot 109, Cursor 77, Devin 297,
Codex 131. Additions/removals — `any`: 624/562, 1,597/2,136, 849/344, 3,763/1,700,
1,308/558 · non-null `!`: 35/26, 191/99, 158/72, 877/179, 215/119 ·
`@ts-ignore`+`@ts-expect-error`: 124/2, 21/37, 29/13, 127/125, 98/29 (agent order as above).

> **Caption.** Mean additions and removals per PR of (a) `any`, (b) the non-null
> assertion operator and (c) `@ts-ignore` / `@ts-expect-error` suppression directives
> per AI agent in TypeScript type-related PRs; panels use independent x-axes. Copilot
> is the only agent that removes more `any` than it adds (total 1,597 vs. 2,136);
> Devin leads non-null assertions (3.0 added per PR vs. 0.6 removed); Claude Code adds
> suppression directives almost without ever removing them (3.6 vs. 0.06 per PR;
> 124 vs. 2 in total).

### `fig7_csharp_escape_constructs_by_agent` — C# per agent

Same design as fig4. Per-agent n: Copilot 359, Cursor 4, Codex 346 (no Claude Code or
Devin C# PRs). Additions/removals — `dynamic`: 160/79, 1/1, 19/10 · null-forgiving
`!`: 654/361, 0/0, 298/11 · `#nullable disable`: 672/266, 0/0, 0/0.

> **Caption.** Mean additions and removals per PR of (a) `dynamic`, (b) the
> null-forgiving operator and (c) `#nullable disable` directives per AI agent in C#
> type-related PRs; panels use independent x-axes. Copilot is the only agent that uses
> `#nullable disable` (1.9 added per PR; 672 vs. 266 in total); Codex adds the
> null-forgiving operator while almost never removing it (0.86 vs. 0.03 per PR).
> Cursor's bars rest on 4 PRs (hatched).

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
fig3_4_by_agent.py       (emits fig3, fig4, fig6, fig7)
fig5_feature_diversity.py
make_all.py              regenerates all six
```

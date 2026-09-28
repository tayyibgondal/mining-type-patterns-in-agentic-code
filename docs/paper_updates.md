# Paper updates: what changed in the re-run

Every claim in the FSE 2027 draft whose number or wording changes as a result of
the catalogue rebuild and corpus replacement. The LaTeX lives in Overleaf, so
this file is the hand-off. Updated as each phase lands.

Status: pipeline complete end to end. Corpus, catalogue, Stage 1, Stage 2,
statistics, all eight figures and both tables regenerated. Outstanding: the
occurrence-level validation annotation, and two parser fixes awaiting a
decision (Section 9).

---

## 1. Table 1 is wrong in the current draft

The "Original" column reports **33,596 agent PRs for both TypeScript and C#**.
Those cannot both be right, and neither is. Counted directly from the AIDev
tables, filtering repositories by language and PRs to the five studied agents:

| Language | Draft "Original" | Actual | Repos |
|---|---|---|---|
| TypeScript | 33,596 | **13,643** | 1,422 |
| C# | 33,596 | **5,837** | 470 |
| Rust | 1,079 | **3,199** | 338 |

The reviewer report already flagged the duplicate 33,596 as unexplained. It is
not a rounding or vintage artifact: AIDev holds 71,190 agent PRs in total across
all languages, and OpenAI Codex alone accounts for 35,521 of them, so 33,596 is
an all-language quantity that reached a per-language row. The identical value in
two rows is the tell.

Rust moves the other way, from 1,079 up to 3,199, which is consistent with AIDev
having grown since the original collection. The TypeScript and C# figures cannot
be explained that way, because the draft's numbers are larger than the totals
available today.

**Action:** regenerate Table 1 from `scripts/stage1_extract.py` output. Never
transcribe it by hand.

## 2. The human corpus is replaced, not extended

| Language | Draft human n | New human n | Source |
|---|---|---|---|
| TypeScript | 235 (269 rows, 101 unique after de-dup) | **12,690** | GitHub scrape |
| C# | 195 | **15,260** | GitHub scrape |
| Rust | 145 | **15,417** | GitHub scrape |

PR-level overlap with the old human sets is exactly zero, because the time
windows are disjoint. All three languages now draw their human baseline from one
source and one procedure, which removes the cross-language source confound
Section 6 currently concedes.

Two consequences for Section 4.1 and Section 6:

- **Acceptance is no longer 100% by construction.** The new corpus carries
  rejected and pending PRs (TypeScript 9,952 / 2,596 / 142; C# 12,199 / 2,922 /
  139; Rust 12,747 / 2,629 / 41). RQ3 becomes answerable for all three
  languages, and the dagger footnote on Table 3 can go.
- **A temporal gap opens.** Human PRs span 2011-2021, agent PRs 2024-2026. This
  follows the paper's own stated criterion of collecting human PRs before the
  Copilot release, but it must be stated as a threat rather than left implicit.

The scrape also excludes bot and ghost authors and rollup PRs, and caps at 300
PRs per repository. Section 4.1 currently claims a 3,000 cap and does not
mention the author or rollup filters. Update the criteria list to match.

## 3. RQ3 reverses

Table 3 reports 83.2% of TypeScript human PRs merged; the RQ3 prose reports
25.3% and concludes agents are accepted more often. The 25.3% came from counting
189 metadata-stripped duplicate rows, which collapse to 21 real PRs, as
unmerged. The direction of the finding inverts under the corrected figure.

`pr_key` (`<language>:<owner/repo>#<number>`) is now the primary key at every
stage, with a uniqueness assertion at each write. The RQ3 narrative and the
Conclusion sentence built on it must be rewritten once the new numbers land.

## 4. The construct catalogue changed

Now 85 constructs defined once in `catalogue/constructs.py`, against 23 / 25 / 23
described in Section 4.3. Each carries a tier, a failure mode, a family, and a
documentation, linter or literature citation.

**Counts move substantially.** On 300 TypeScript agent PRs, measured old rule
against new:

| Construct | Old | New | Why |
|---|---|---|---|
| `any` additions | 2,171 | 4,320 | old pattern was `:\s*any` only, missing `as any`, `any[]`, generic arguments |
| non-null `!` additions | 271 | 833 | old stats pattern was `!\.` only; the figure script used a broader pattern that also matched logical negation, so the two disagreed |
| type assertions | not counted | 2,533 | absent from the old catalogue |
| `unknown` | not counted | 1,341 | absent from the old catalogue |
| `@ts-ignore` | not counted | 32 | absent from the old catalogue |

The nine-times-more-often claim for `any` in the abstract and RQ1 will move.
Direction is unknown until the human arm is recounted the same way.

**Dropped, having failed the type-directed test:** decorators and abstract
classes in TypeScript; `var`, attributes, delegates, inheritance and `typeof` in
C#; `match`, `if let`, `derive`, struct definitions, impl blocks and
smart-pointer wrappers in Rust. Decorators were the highest bar in the old
Figure 3 for TypeScript agents, so that figure changes shape.

**Reclassified:** optional chaining and nullish coalescing move from
expressiveness to Tier D safety, where they are the safe counterpart to the
non-null assertion. Reporting them beside `!` is a new and sharper contrast.

**Added:** the suppression family, absent entirely before, covering
`@ts-ignore`, `@ts-expect-error`, `@ts-nocheck`, `#pragma warning disable`,
`#nullable disable` and `#[allow]`. Reported on its own unit of files affected,
never pooled with per-occurrence constructs.

**Split:** Rust `unsafe` becomes six counters including `unsafe impl Send` and
`unsafe impl Sync`, which prior work singles out as where soundness arguments
most often fail.

## 5. Section 4.3 and 4.4 need rewriting

- Stage 1 now consults the catalogue, so the filter and the counters can no
  longer disagree about what a construct is. The retention predicate itself is
  unchanged in form.
- Comments and string literals are stripped before matching. The old Rust
  `unsafe` counter matched the word inside `// SAFETY:` prose; the old C#
  generics counter matched HTML tags inside string literals.
- **A format bug worth reporting as a lesson, not hiding:** AIDev writes diff
  headers as `=== path (+1/-1) ===` while GitHub diffs use `diff --git`. A
  parser handling only the latter returns zero constructs for every agent PR and
  looks like a clean result.

**Stage 1 retention is now consistent across arms**, which it was not before:

| Language | Agent | Human |
|---|---|---|
| TypeScript | 7,582 / 13,643 (55.6%) | 6,683 / 12,690 (52.7%) |
| C# | 3,075 / 5,837 (52.7%) | 7,085 / 15,260 (46.4%) |
| Rust | 1,927 / 3,199 (60.2%) | 10,577 / 15,417 (68.6%) |

The old spread was 12.9% to 64%, and that variance was an artifact of the two
arms coming from different sources rather than a property of the code.

## 6. Stage 2 changes (pending)

Three defects in the current pipeline that Section 4.4 does not disclose:

1. **The C# classifier prompt contains** `CRITICAL: BE LINIENT AND MOSTLY SAY
   YES EVEN IF YOU FIND A MINIMAL EVIDENCE.` TypeScript and Rust have no such
   line, and it contradicts the same prompt's closing instruction. Section 4.4's
   claim that the prompts "are structurally identical and differ only in this
   definition" is false as written, and C#'s higher measured Stage 2 recall is
   plausibly an artifact of it.
2. **Rust was classified with Gemini 2.0 Flash while TypeScript and C# used
   GPT-4o-mini.** An undisclosed cross-language model confound.
3. **Timeouts silently became negatives** without setting the error flag, so a
   transport failure is indistinguishable from a genuine rejection.

The re-run uses one model for all three languages, prompts generated from the
catalogue so no leniency drift is possible, structured outputs, three runs with
majority vote and reported run-to-run agreement, retries, and a resumable cache.

## 7. Results that changed direction

### RQ2: the `any` finding depends entirely on the denominator

| Metric | AI | Human | Direction |
|---|---|---|---|
| Additions per PR | 5.61 | 1.36 | agents 4.1x higher |
| Per 100 changed lines | 1.16 | 2.26 | **humans higher** |
| Per 100 lines, repository-clustered | 1.60 | 3.73 | **humans higher** |
| Restricted to 20 shared repositories | 1.11 | 1.93 | **humans higher** |

The abstract and RQ1 currently claim agents introduce `any` "roughly 9x more
often". On the rebuilt corpus it is 4.1x per PR, and all three size- or
repository-controlled normalisations reverse the direction. Section 6 already
commits the paper to reporting the disagreement rather than choosing the
favourable denominator. They now disagree, so that commitment binds.

### RQ3 reverses in all three languages

Humans are merged more often everywhere: 77.5% against 52.5% in TypeScript,
77.7% against 62.3% in C#, 82.2% against 61.2% in Rust. This matches the
corrected Table 3 rather than the RQ3 prose, and removes the claim that code
with weaker type hygiene is merged more readily.

**Do not push this result hard.** The human corpus predates the Copilot release
and was found by searching top-starred repositories, which surfaces merged work
far more readily than abandoned work. The gap is confounded by both era and
sampling procedure, and Threats must say so.

### The strongest genuine agent effect is the C# null-forgiving operator

Present in 32.5% of agent PRs against 5.6% of human ones (Cramer's V 0.357),
with 3.69 additions per PR against 0.76. It survives the per-line
normalisation, unlike `any`. It does not survive repository matching, where
humans come out higher; report both.

### Rust shows no `unsafe` difference

Prevalence 8.9% against 8.3%, p = 0.56. The repository-matched Rust cell
contains only 14 agent PRs and should not be reported at all.

### Pipeline quality figures worth reporting

- **99.0% of PRs received an identical verdict across all three independent
  classifier samples.** This is the run-to-run stability the Hindle guidelines
  require and the old single-run pipeline could not report.
- The validator rejected 12-25% of what the classifier accepted, so the
  two-agent design still does real work rather than rubber-stamping.
- Zero transport errors across 73,855 calls.

## 8. Figures and tables are now generated, not transcribed

All eight figures read construct counts from the columns the extractor wrote,
via `catalogue`, rather than recounting from `patch_text` with private copies
of the regexes. `scripts/make_tables.py` generates Table 1 and Table 3.
Nothing in either is hand-entered.

Two bugs found while rewiring them:

- `fig2b` divided construct counts by the `changes` column. In the rebuilt
  schema `changes` is the number of changed **files**, not lines, so the
  normalised figure disagreed with the reported statistics. It now uses the
  same denominator as the analysis, lines added in countable source files.
- Four figure scripts still imported the retired statistics module.

## 9. Open

- Stage 2 scale and spend (see the cost note in the session log).
- Occurrence-level precision and recall per construct, Phase 4.
- All statistics and figures, Phases 5 and 6.

---

# Statistical analysis and figure rebuild (2026-09-28)

## New section

`FSE2027/fse-sections/4-data-processing-procedure.tex` gains `\subsection{Statistical Analysis}` (`\label{sec:stats}`) covering unit of analysis, test selection, the four normalisations, multiplicity, what each RQ estimates, and the results. The full pre-registered plan lives in `docs/statistical_methodology.md`.

## New tests

Two additions to `analysis/`, both in `stats.py` as `profile_test` and wired into `run_analysis.py`:

- **Usage-profile permutation test.** 10,000 label shuffles on the L1 distance between the two groups' mean per-100-line rate vectors. One omnibus answer per language per family. This is the test that answers "do they use type constructs / escape hatches similarly" as a reader asks it. The family volume tests could not, because two groups can match on total volume while spending it on different constructs.
- **Spearman rho between the two profiles**, reported beside it, to separate "they rank the catalogue differently" from "they rank it the same and lean harder".

RQ3 also gains repo-matched acceptance and per-agent acceptance against the pooled human rate.

Test count went from 129 to 153.

## The finding that changes how earlier numbers should be read

**Agent PRs are much larger than human PRs.** Median counted lines added:

| Language | Agent | Human |
|---|---|---|
| TypeScript | 200 | 39 |
| C# | 226 | 96 |
| Rust | 168 | 55 |

Every per-PR construct count is therefore partly a measure of PR size. Most RQ1 and RQ2 results reverse direction between the per-PR view and the per-100-changed-lines view. The paper now shows both panels side by side in every construct figure rather than picking one, and says so in the text.

The cleaner decomposition, which the new figures make visible: **agents spread escape hatches across more PRs, humans use them more densely in the PRs where they appear.** In Rust all eight escape hatches have a higher human conditional median. In TypeScript `any` appears in 42.5% of agent PRs against 26.3% of human PRs, but the conditional median rate is 0.97 against 2.71.

## Headline results now in the paper

| | TypeScript | C# | Rust |
|---|---|---|---|
| RQ1 expressiveness profile | p < 0.001, rho 0.96 | p < 0.001, rho 1.00 | p < 0.001, rho 0.71 |
| RQ1 safety profile | p = 0.018, rho 0.94 | p = 0.001, rho 0.60 | p = 0.53 (ns), rho 0.90 |
| RQ2 escape profile | p < 0.001, rho 0.90 | p < 0.001, rho 0.50 | p < 0.001, rho 0.86 |
| RQ2 suppression, share of PRs | 6.8 vs 6.4% (ns) | 14.9 vs 5.1% *** | 13.8 vs 6.2% *** |
| RQ3 merged share | 52.5 vs 77.6% *** | 62.3 vs 77.7% *** | 61.2 vs 82.2% *** |
| RQ3 repo-matched | 34.6 vs 79.7% *** | 63.6 vs 84.6% *** | underpowered, n(AI)=14 |

C# null-forgiving is the strongest group effect anywhere: 32.5% vs 5.6% prevalence, Cramer's V 0.357.

Carrying a Tier A escape hatch does not predict rejection. In C# agent PRs it predicts *higher* acceptance (69.0 vs 57.6%). Whatever drives the acceptance gap, it is not reviewers catching escape hatches.

## Figures

Typography scale raised from 8/8.5/7.5/9/10 pt to 11/12/10.5/13/14.5 pt, and every figure is now included at `\textwidth` instead of `0.8\textwidth`. At the old scale the tick labels landed near 5.5 pt on the printed page.

Renumbered and partly rebuilt. Twelve figures, all from `python3 final_figures_for_paper/make_all.py`:

| New | What | Was |
|---|---|---|
| fig1 | headline escape hatch, 4 columns x 3 rows | fig1, 3x2, rebuilt |
| fig2-4 | per-language construct usage, per PR and per 100 lines | fig2 + fig2b, merged and split by language |
| fig5 | construct diversity by agent | fig5 |
| fig6-8 | per-language escape-hatch prevalence and conditional intensity | **new** |
| fig9 | escape-hatch churn by agent | fig3 |
| fig10-12 | per-agent escape constructs | fig4, fig6, fig7 |

Substantive changes beyond layout:

- **fig1** now has four columns, not three. C# contributes both `dynamic` and the null-forgiving operator, because `dynamic` is rare in both arms and showing only the mapped construct reported the quiet half of the language. It also gained a third row so the per-PR and per-line views sit above each other.
- **fig2-4** replace the old three-panel fig2. Three languages side by side left about a third of an inch of bar for constructs with thirty-character names, which is not readable at any font size. fig2b is absorbed as panel b.
- **fig6-8 are the new box plots.** Prevalence bars beside conditional-intensity boxes, because an unconditional box on a zero-inflated count has its median and both quartiles on zero.
- **fig9** C# panel switched from `dynamic` to the null-forgiving operator. The old panel was effectively blank.
- **fig5** lost its hardcoded `ylim(0, 60)`, which assumed the old catalogue size and left half the canvas empty.

## Still outstanding

Not touched by this pass, carried forward:

- Section 5 prose still carries pre-rerun numbers (2.16 vs 0.24 for `any`, the 83.2 vs 25.3 RQ3 split, the old Rust means). The figures and Section 4 are current; Section 5 is not.
- Section 4.4's Stage 2 text still says GPT-4o-mini accepted 648 of 1,083 TypeScript PRs. Those are pre-rerun counts.
- The two parser fixes (cue list missing bare "type"/"types", `.d.ts` exclusion dropping pure-typing PRs).
- Whitespace-only-line filter. Reformatting PRs still inflate gross additions.
- Test-directory exclusion beyond Rust panic macros.

## Write-up pass (2026-09-28, second)

Everything below is now regenerated from the current corpus. No pre-rerun number survives in the paper.

**Section 5 rewritten and reordered.** RQ1 is now type constructs, RQ2 escape hatches, RQ3 acceptance, matching the introduction's list. Every number comes from `analysis/results/statistical_results.csv`. The old RQ ordering (escape hatches first) is gone.

**Section 4 corrections:**

| Was | Now |
|---|---|
| Corpus table: TS 33,596 → 1,083 → 648 | 13,643 → 7,582 → 5,618 |
| Stage 2 accepted 648/1,083 TS, 709/1,392 CS, 290/790 RS | 5,618/7,582, 1,917/3,075, 1,220/1,927 |
| Stage 1 precision 92.0 / 96.0 / 80.0 | 76.0 / 68.0 / 92.0 |
| Stage 2 recall 76.7 / 92.0 / 88.5 | 54.5 / 51.1 / 54.3 |
| Cohen's kappa row (0.92-1.00) | removed; labels are one reviewed pass, second annotator pending |
| "consensus gold standard" | "manual annotation, stratified 25/25" |

Added: the three-run agreement figure (99.0%), and an explicit statement that Stage 2 recall near 52% makes the corpus a precision-filtered subset rather than a census, so prevalence means prevalence *within construct-related PRs*.

**Section 6 threats:** the last three paragraphs described the retired corpus and were factually wrong. Replaced. The old "709 agentic C# PRs against 44 human ones" and "human acceptance near 100% by construction" and "we do not test C#/Rust for RQ3" are gone. New threats: the 2011-2021 vs 2024-2026 temporal gap (and what it buys, namely one uniform human collection procedure), low Stage 2 recall, repository clustering with author-level dependence still uncontrolled, the thin Rust repo-matched arm (n=14), and the unimplemented whitespace-only-line filter.

**Abstract:** `[SUMMARY OF THE RESULTS]` placeholder filled.

**Introduction:** RQ wording sharpened to match Section 5. Typo "we wna to answer" fixed. Headline-construct sentence now names C#'s null-forgiving operator alongside `dynamic`, with the reason.

**Conclusion:** rewritten. The old version claimed agents rely on `any` "substantially more than humans", which is only true per PR and reverses per line.

**One claim corrected during the pass.** A first draft said the prevalence/intensity split covers "17 of the 18" constructs. Checked against the data: humans have the higher conditional median for **all 18**, and agents have the higher prevalence for **14** (the exceptions are the bare `Function` type, `dynamic`, `RefCell` and `transmute`, all rare in both arms). Fixed in the results, abstract and conclusion.

Paper builds clean at 27 pages, no undefined references.

## Figure geometry and table provenance (2026-09-28, third)

### The sizing bug

The paper is `acmsmall`, a single-column journal class. Its `\textwidth` is 395.82 pt = **5.4975 in**, not the 7.16 in I had been drawing on. Every figure was therefore scaled to 77% on the page, and earlier still to 61% when they were included at `0.8\textwidth`. That is why the fonts never looked right at any setting: an 8 pt tick label was landing at 4.9 pt.

Worse, because each figure's height was computed from its own row count with no shared budget, page heights ran from 2.0 in to 5.5 in with no pattern.

### The fix

`final_figures_for_paper/_style.py` now owns the geometry:

```
TEXT_W   = 5.4975   # exactly \textwidth, so the page scale factor is 1.0
FIG_H_S  = 2.50     # <=5 rows, or a single panel
FIG_H_M  = 3.85     # 5 to 10 rows
FIG_H_L  = 5.30     # 10+ rows, and the headline figure
```

Every figure is drawn at `TEXT_W` and built to hit one of the three heights exactly. Row height is now *derived* from the fixed figure height rather than the other way round, which also made the row rhythm consistent across figures of the same family (0.20-0.27 in per row for the construct charts, 0.50-0.51 in for the distribution charts).

Font scale dropped from 11/12/10.5/13/14.5 pt to **8.5/9/8/9.5/11 pt**. That is not a reduction in rendered size, it is an increase: at scale 1.0 against 10 pt body text these are large figure labels, where the old 11 pt rendered at 8.4 pt.

Final geometry, all twelve:

| Height | Figures |
|---|---|
| 2.50 in | fig5, fig9, fig10, fig11, fig12 |
| 3.85 in | fig3, fig6, fig7 |
| 5.30 in | fig1, fig2, fig4, fig8 |

### Float backlog

`FIG_H_L` was first set to 6.00 in, which is 75% of the 7.97 in text block. LaTeX could not place a figure that large beside any useful amount of prose, so the queue backed up and the results section rendered as four pages of solid text followed by a wall of figures. Two changes:

- `FIG_H_L` capped at 5.30 in, two thirds of the text height.
- Float parameters relaxed in the preamble (`topnumber` 3, `totalnumber` 4, `topfraction` 0.92, `textfraction` 0.06, `floatpagefraction` 0.70) and placement changed from `[h]` to `[htbp]`.

Figures now interleave with prose from page 12 through 25 instead of queueing.

### Dataset table verified and made reproducible

The six "Original" counts in Table 1 were **hardcoded** in `scripts/make_tables.py` as `SOURCE_TOTALS`, which is precisely the failure that module's own docstring exists to prevent. Counted them from source:

| | Table said | Source says |
|---|---|---|
| TS agent | 13,643 | 13,643 |
| TS human | 12,690 | 12,690 |
| C# agent | 5,837 | 5,837 |
| C# human | 15,260 | 15,260 |
| Rust agent | 3,199 | 3,199 |
| Rust human | 15,417 | 15,417 |

All six were correct. `SOURCE_TOTALS` is now replaced by `source_totals()`, which counts agent PRs from the AIDev `pull_request` table (repos whose language matches, author among the five studied agents) and human PRs from the scrape CSVs deduplicated on `(repo, pr_number)`. The numbers can no longer drift from the data.

Both tables are now generated and `\input` into the paper from `FSE2027/fse-tables/`, rather than being maintained by hand in the `.tex`. Fixed a latent bug while doing it: the generator emitted a bare `C#` in the acceptance table header, which is a hard LaTeX compile error, not a cosmetic one. It now escapes through a `tex()` helper.

Paper builds clean at 28 pages, zero errors, zero undefined references, zero overfull boxes.

## Consistent styling, palette and page spacing (2026-09-28, fourth)

### What was inconsistent

An audit of the five figure scripts found that each one was making its own styling decisions:

| | Was |
|---|---|
| Legend position | `lower center` in four scripts, `upper center` in two |
| Left spine | hidden in fig2 and fig9-12, kept in fig6-8, all three are horizontal bar charts |
| Row separators | drawn in fig2 and fig6-8, absent from fig9-12 |
| Grid | each script passed its own `axis=` string to `tidy()` |
| Log axes | `set_xscale('log')` raw, so matplotlib drew eight minor ticks per decade, rendering as a grey smear that varied by data span |
| Greys | `#a8a8a8`, `#cccccc`, `#f2f2f2` hardcoded beside the named `INK_3` and `GRID` |
| Hatch | `'////'` written out in two places |

### The contract

`_style.py` now owns all of it and the figure scripts call it:

- **`tidy(ax, orient)`** takes `'v'` or `'h'` for the direction the data runs, and derives the grid axis, which spines survive and which tick marks are suppressed. The category axis loses its spine and its ticks, because nothing is measured along it. One argument instead of five independent decisions.
- **`row_separators(ax, y)`** for every row-based chart, or none.
- **`log_axis(ax, which)`** sets the scale and kills the minor locator.
- **`bottom_legend(fig, ...)`** is the single legend position in the paper.
- `HATCH_SMALL_N` and the `INK`/`INK_2`/`INK_3`/`GRID`/`BAND` neutral ramp replace every hardcoded literal.

### Palette

Replaced the hand-picked hues with **Okabe-Ito**, the standard colour-vision-deficient safe qualitative palette. It is separable under deuteranopia, protanopia and tritanopia, and it is a set a reviewer can look up rather than take on trust.

| Role | Was | Now |
|---|---|---|
| AI agents | `#eb6834` | `#D55E00` vermillion |
| Human developers | `#2a78d6` | `#0072B2` blue |
| Removals | `#1baf7a` | `#009E73` bluish green |
| Grid | `#e2e2e2` | `#dcdcdc` |

Scripts now reference role names (`C_AI`, `C_HUMAN`, `C_ADD`, `C_REMOVE`, `C_LANG`), never a hex value, so a future palette change is one edit.

One honest limitation: vermillion and blue sit closer in luminance than ideal, so they separate less well in greyscale than in colour. Group is never carried by colour alone. Paired marks are always ordered AI first and both are labelled.

### Page spacing

acmart sets `\flushbottom`, which forces every page to end at the same height by stretching the glue between paragraphs, headings and floats. On a page carrying a figure that produces visibly uneven paragraph spacing. Added `\raggedbottom`, which pushes the slack to the bottom of the page instead and keeps inter-paragraph spacing constant.

Combined with the earlier float-parameter change, figures now interleave with prose from page 11 through 24 rather than queueing.

Paper builds clean at 28 pages, zero errors.

### Audit follow-up

A read-only sweep of the five figure scripts after the refactor confirmed zero remaining hex colours, hatch strings, `set_*scale('log')` calls, `fig.legend` calls or bare numeric font sizes. It caught two leftovers that the refactor missed:

- **`'white'` in eight places**, used as an edge colour to knock a hairline out of a marker against the page. It is the same value as the existing `SURFACE` constant and now uses that name, so a dark-background variant would be one edit rather than eight.
- **Dead `GRID` imports** in `fig2_feature_usage.py` and `fig6_8_escape_distributions.py`, left behind once grid and separator drawing moved into `tidy()` and `row_separators()`.

Two direct calls remain and are deliberate: `axvspan` for the shaded human reference band in fig5, and the `spines[...]` loop that makes the invisible P-value gutter axes in fig6-8. Neither is a styling decision a helper should own.

# Statistical methodology for the three research questions

This document fixes the test plan before the numbers are read. It covers what
the unit of analysis is, what each research question estimates, which test
answers it, which effect size travels with it, and how multiplicity is handled.

## 1. Unit of analysis

The pull request is the unit. Every stage of the pipeline de-duplicates on
`pr_key`, which is `f"{language}:{repo_full_name}#{number}"`, and the analysis
asserts `len(frame) == frame.pr_key.nunique()` before any test runs. A PR
contributes one observation to one language and one group.

Group is binary. `AI` is a PR opened by one of the five coding agents in AIDev.
`Human` is a PR from the human scrape. The two arms are never pooled.

## 2. Why nonparametric

Per-construct counts are zero inflated and heavy tailed. Most PRs add a given
construct zero times, and a small number of PRs add it hundreds of times. The
mean is not a stable summary of such a variable and the t-test's normality
assumption does not hold even approximately. So:

- comparisons of counts and rates use the Mann-Whitney U test,
- comparisons of shares use the chi-square test of independence, with an exact
  Fisher fallback when any expected cell drops below five or either arm has
  fewer than fifty PRs,
- every proportion carries a Wilson score interval, because several construct
  prevalences sit close to zero where the normal interval leaves [0, 1],
- every mean carries a bootstrap percentile interval over 2,000 resamples.

We report the median next to the mean throughout. For several constructs the
human mean is the larger of the two while the AI distribution is stochastically
larger. That is a real feature of zero-inflated data, not an error. A handful of
very large human PRs pull the human mean up while the bulk of human PRs sit at
zero. Cliff's delta reads the bulk, the mean reads the tail, and the paper
reports both rather than picking the flattering one.

## 3. Normalisation

Four views of the same quantity, reported together, because no single one is
safe on its own.

| View | Definition | What it controls |
|---|---|---|
| Per PR | gross additions of the construct | nothing; the raw behaviour |
| Per 100 changed lines | `100 * additions / max(lines_added, 1)` | PR size |
| Repo-clustered | collapse each repository to its mean, then test | within-repository dependence |
| Repo-matched | restrict to repositories present in both arms | codebase, review culture, project norms |

`lines_added` counts only lines the parser actually counted, in files of the
target language, so files in other languages do not dilute the rate.

The headline metric is gross additions. Removals are reported separately and net
change is secondary. Under a net metric a refactor that replaces ten `any`
annotations with concrete types scores zero, which is the opposite of what it
did.

## 4. Effect sizes

No p-value is reported without one. At these corpus sizes a trivial difference
clears p < 0.001, so significance alone carries no information.

- Mann-Whitney U carries Cliff's delta, thresholds 0.147 / 0.33 / 0.474 for
  negligible / small / medium / large. Cohen's d is stored as a secondary value
  but not used for the claims, since it assumes a scale the counts do not have.
- Chi-square carries Cramer's V. Fisher carries the odds ratio.
- Repo-clustered tests carry Cliff's delta over the repository means.

## 5. Multiplicity

The per-construct tests are a family. TypeScript alone runs 22 of them for RQ1
and 6 for RQ2. Within each language and each research question the per-construct
p-values are corrected with the Benjamini-Hochberg procedure at a 5% false
discovery rate. Family-level and headline tests are pre-registered single
comparisons and are reported uncorrected, which the tables mark.

## 6. RQ1: do agents and humans use type constructs similarly?

The estimand is the usage profile over the expressiveness and safety families.
"Similarly" needs two things answered, and one test cannot do both.

**Volume.** Do the groups reach for type constructs at the same rate? Three
family-level Mann-Whitney tests per family: total additions per PR, distinct
constructs per PR, and additions per 100 changed lines. Plus the repo-clustered
variant of the rate.

**Shape.** Given that they use type constructs, do they reach for the same ones?
Two statistics, both new in this revision.

1. A permutation test on the profile distance. Build the vector of group mean
   per-100-line rates over the constructs in the family, one entry per
   construct. Take the L1 distance between the AI vector and the human vector.
   Shuffle the group labels 10,000 times and recompute. The p-value is the share
   of shuffles whose distance reaches the observed one. This is one omnibus
   answer per language per family, and it is the test that answers the question
   as the reader asks it.
2. Spearman rank correlation between the two mean-rate vectors. A high rho with
   a significant permutation p means the groups agree on which constructs matter
   and disagree only on how hard they lean on them. A low rho means the
   preference ordering itself differs.

Then one Mann-Whitney per construct, BH corrected within the family, for the
reader who wants to know which construct drives the omnibus result.

Constructs the catalogue marks `reliable=False` are reported with their measured
precision and excluded from the tests. They are never deleted from the
catalogue.

## 7. RQ2: do agents and humans use escape hatches similarly?

Same two-part structure, applied to the escape and suppression families, with
four constraints the taxonomy imposes.

**Tier A and Tier B are never summed.** Tier A waives a guarantee outright.
Tier B relocates it to a runtime check. A sum over both produces a number with
no meaning, so each tier gets its own aggregate.

**Suppression has its own unit.** The metric is the share of PRs containing at
least one directive, not occurrences per 100 lines. One `#nullable disable`
waives an unbounded number of checks, so counting occurrences understates it and
normalising by lines understates it further.

**The headline construct carries the language.** TypeScript `any`, C# `dynamic`
and the null-forgiving operator, Rust `unsafe` in any of its five forms. Each
gets prevalence, per-100-line rate, the repo-clustered rate, and additions and
removals per PR as separate tests.

**Conditional intensity is reported separately from prevalence.** For a zero
inflated construct the unconditional box plot collapses onto zero and shows
nothing. So the distribution figures plot the per-100-line rate among the PRs
that use the construct at least once, and annotate prevalence above each pair.
Prevalence answers how many PRs reach for the hatch. Conditional intensity
answers how hard they lean on it once they do. Reporting only their product
hides which of the two is moving.

## 8. RQ3: acceptance

The outcome is binary, merged against not merged, read from `merged_at`. The old
human corpus was 100% merged by construction, which made this question
unanswerable. The new scrape carries rejected and pending PRs in all three
languages, so it is answerable in all three.

- Merged share, AI against human, chi-square with Cramer's V and Wilson
  intervals on both proportions.
- The repo-matched variant, restricted to repositories present in both arms.
  This is the test that survives the objection that the two arms come from
  different projects with different merge cultures.
- Per-agent merged share, with Wilson intervals, to show whether one agent
  drives the pooled number.
- Within each group, acceptance of PRs carrying a Tier A escape hatch against
  those carrying none. This is the question behind the question. It asks whether
  review catches the hatch, and it is a within-group comparison so it is not
  confounded by the group difference in merge rate.

Acceptance is an outcome of the review process, not a property of the code. A
lower agent merge rate is evidence about how projects treat agent PRs. It is not
evidence that the code is worse, and the paper does not claim it is.

## 9. What this design does not do

No causal claim. The two arms differ in time window, in author population and
in project selection, and no test here removes those differences. Repo-matching
narrows the gap and is the strongest available check, but 20 shared TypeScript
repositories is a robustness analysis, not an identification strategy.

No per-author clustering. Repository is the clustering unit. Author-level
dependence remains, and it is listed under threats.

No regression adjustment. The pre-registered design is a comparison of
distributions with explicit normalisations, not a model with covariates. Adding
covariates would invite the reader to read the coefficients causally.

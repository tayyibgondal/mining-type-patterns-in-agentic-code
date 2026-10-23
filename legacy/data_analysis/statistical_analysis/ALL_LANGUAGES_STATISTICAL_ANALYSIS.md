# Comprehensive Statistical Analysis — All Languages

Statistical comparison of AI-agent vs. human developers on type-related pull requests across **TypeScript**, **C#**, and **Rust**.

**Significance:** `*` p<0.05, `**` p<0.01, `***` p<0.001, `ns` not significant.  
**Effect sizes:** Cohen's *d* / rank-biserial *r* (continuous, Mann-Whitney), Cramer's *V* / odds ratio (categorical).


## RQ1 — Escape-Hatch Type Usage (`any` / `dynamic` / `unsafe`)

| Language | Metric | Test | AI | Human | p-value | Sig | Effect size |
|---|---|---|---|---|---|---|---|
| TypeScript | 'any' prevalence | Chi-square | 90.4% | 22.7% | 1.206e-92 | *** | V=0.674 |
| TypeScript | 'any' intensity (per PR) | Mann-Whitney U | 5.00 (med) | 1.00 (med) | 5.111e-18 | *** | d=0.40, r=0.67 |
| C# | 'dynamic' prevalence | Fisher's exact | 3.7% | 2.3% | 1 | ns | OR=1.64 |
| C# | 'dynamic' intensity (per PR) | Mann-Whitney U | 2.00 (med) | 1.00 (med) | 0.3434 | ns | d=0.00, r=0.58 |
| Rust | 'unsafe' prevalence | Chi-square | 12.4% | 13.5% | 1 | ns | V=0.000 |
| Rust | 'unsafe' intensity (per PR) | Mann-Whitney U | 3.00 (med) | 4.00 (med) | 0.2656 | ns | d=-0.09, r=-0.27 |

## RQ2 — Advanced Feature Usage

| Language | Metric | Test | AI | Human | p-value | Sig | Effect size |
|---|---|---|---|---|---|---|---|
| TypeScript | Feature diversity (unique/PR) | Mann-Whitney U | 9.06 | 4.47 | 3.093e-58 | *** | d=1.37, r=0.67 |
| TypeScript | Feature volume (total/PR) | Mann-Whitney U | 237.16 | 76.79 | 3.431e-64 | *** | d=0.29, r=0.71 |
| TypeScript | Non-null assertion (!.) adoption | Fisher's exact | 19.8% | 0.0% | 1.396e-21 | *** | OR=inf |
| C# | Feature diversity (unique/PR) | Mann-Whitney U | 5.72 | 4.14 | 0.0003905 | *** | d=0.65, r=0.32 |
| C# | Feature volume (total/PR) | Mann-Whitney U | 391.37 | 109.66 | 7.956e-05 | *** | d=0.24, r=0.35 |
| C# | Null-forgiving operator (!) adoption | Fisher's exact | 20.0% | 4.5% | 0.009015 | ** | OR=5.26 |
| Rust | Feature diversity (unique/PR) | Mann-Whitney U | 4.99 | 7.04 | 0.0001836 | *** | d=-0.56, r=-0.32 |
| Rust | Feature volume (total/PR) | Mann-Whitney U | 47.78 | 95.96 | 0.003252 | ** | d=-0.32, r=-0.26 |
| Rust | unsafe impl adoption | Fisher's exact | 0.7% | 1.9% | 0.3913 | ns | OR=0.35 |

## RQ3 — PR Acceptance

| Language | Metric | Test | AI | Human | p-value | Sig | Effect size |
|---|---|---|---|---|---|---|---|
| TypeScript | PR acceptance rate | Chi-square | 45.8% | 25.3% | 1.094e-08 | *** | V=0.189 |
| C# | PR acceptance rate | Fisher's exact | 56.7% | 100.0% | 5.479e-11 | *** | OR=0.00 |
| Rust | PR acceptance rate | Fisher's exact | 60.3% | 100.0% | 9.199e-11 | *** | OR=0.00 |

## Notes

- **Mann-Whitney U** is used for per-PR count metrics because they are right-skewed with heavy outliers (normality violated); it compares distributions/medians rather than means.

- **Fisher's exact test** replaces chi-square whenever a group is small (n<50) or an expected cell count is <5, which applies to the smaller human samples (notably C# and Rust).

- Intensity rows (RQ1b) are computed on PRs with at least one escape addition, matching the box-plots; prevalence rows (RQ1a) use all PRs.

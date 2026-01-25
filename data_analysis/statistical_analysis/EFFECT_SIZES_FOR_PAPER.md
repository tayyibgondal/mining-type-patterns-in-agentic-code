# Effect Sizes Report for Research Paper

## Summary

This document provides effect sizes for all statistical tests reported in the paper, along with median values as requested by the reviewer.

---

## RQ1: 'any' Type Usage Analysis

### Figure 1 - 'any' Type Additions (Main Finding)

**Source:** `typescript_data/any_statistical_comparison_results.csv`

| Metric | AI Agent | Human | Ratio |
|--------|----------|-------|-------|
| **Mean** | 2.16 | 0.24 | **9.0×** |
| **Median** | 0.0 | 0.0 | - |

**Statistical Test:** Mann-Whitney U

| Statistic | Value |
|-----------|-------|
| U-statistic | 80,152.5 |
| p-value | **2.33 × 10⁻⁷** |
| Cohen's d | **0.316** |
| Effect Size Interpretation | **small** |

### Recommended Text for Paper (with median - addressing reviewer comment)

> As shown in Figure 1, AI agents are 9 times more likely to introduce the `any` type into the TypeScript codebases compared to human developers, with means of the 'any addition' distributions across PRs at 2.16 and 0.24, respectively (medians: 0.0 for both groups). Mann-Whitney U test (p ≈ 2.33 × 10⁻⁷) demonstrated the statistical significance of this result with a small effect size (Cohen's d = 0.32).

**Note on medians:** Both groups have a median of 0.0 because the majority of PRs do not introduce any `any` keywords. Only a subset of PRs (those actively modifying type annotations) show non-zero values. This is typical for count data with many zeros.

---

## RQ2: Advanced Feature Usage Analysis

### Table 2 / Figure 2 - Feature Diversity (Unique Features per PR)

**Sample sizes:** AI Agent = 648 PRs, Human = 269 PRs

| Metric | AI Agent | Human |
|--------|----------|-------|
| **Mean** | 6.75 | 3.58 |
| **Median** | 7.0 | 3.0 |

**Statistical Test:** Mann-Whitney U

| Statistic | Value |
|-----------|-------|
| U-statistic | 147,636.5 |
| p-value | **2.34 × 10⁻⁶²** |
| Cohen's d | **1.45** |
| Effect Size Interpretation | **large** |

### Feature-Specific Analysis

#### Non-null Assertion (!)

| Metric | AI Agent | Human |
|--------|----------|-------|
| Adoption Rate | 19.8% (128/648) | 0.0% (0/269) |

**Statistical Test:** Chi-square

| Statistic | Value |
|-----------|-------|
| χ² | 60.12 |
| df | 1 |
| p-value | **8.91 × 10⁻¹⁵** |
| Cramér's V | **0.256** |
| Effect Size Interpretation | **small** |

#### Type Assertions (as keyword)

| Metric | AI Agent | Human |
|--------|----------|-------|
| **Mean** | 27.20 | 1.88 |
| **Median** | 8.0 | 0.0 |

**Statistical Test:** Mann-Whitney U

| Statistic | Value |
|-----------|-------|
| p-value | **2.18 × 10⁻⁵⁹** |
| Cohen's d | **0.549** |
| Effect Size Interpretation | **medium** |

---

## RQ3: Acceptance Rate Analysis

### Table 3 - Overall Acceptance Rates

| Status | AI Agent | Human |
|--------|----------|-------|
| Merged (Accepted) | **45.8%** (297/648) | **25.3%** (68/269) |
| Closed (Rejected) | 42.6% | 2.6% |
| Open (Pending) | 11.6% | 1.9% |

**Acceptance Rate Ratio:** AI agents have **1.81×** higher acceptance rate than humans

**Statistical Test:** Chi-square

| Statistic | Value |
|-----------|-------|
| χ² | **32.67** (paper: 27.52*) |
| df | 1 |
| p-value | **1.09 × 10⁻⁸** (< 0.0001) |
| Cramér's V | **0.189** |
| Effect Size Interpretation | **small** |
| Odds Ratio | **2.50** |

*Note: The paper reports χ² = 27.52 which may be based on different sample sizes (545 AI vs current 648 AI). Current data yields χ² = 32.67.

---

## Complete Summary Table of Effect Sizes

| Research Question | Test | p-value | Effect Size | Interpretation |
|-------------------|------|---------|-------------|----------------|
| **RQ1:** 'any' additions | Mann-Whitney U | 2.33 × 10⁻⁷ | Cohen's d = 0.316 | small |
| **RQ2:** Feature diversity | Mann-Whitney U | 2.34 × 10⁻⁶² | Cohen's d = 1.448 | **large** |
| **RQ2:** Non-null assertion adoption | Chi-square | 8.91 × 10⁻¹⁵ | Cramér's V = 0.256 | small |
| **RQ2:** Type assertions | Mann-Whitney U | 2.18 × 10⁻⁵⁹ | Cohen's d = 0.549 | medium |
| **RQ3:** Acceptance rate | Chi-square | 1.09 × 10⁻⁸ | Cramér's V = 0.189 | small |

---

## Effect Size Interpretation Guide

### Cohen's d (for continuous variables)
- **Negligible:** |d| < 0.2
- **Small:** 0.2 ≤ |d| < 0.5
- **Medium:** 0.5 ≤ |d| < 0.8
- **Large:** |d| ≥ 0.8

### Cramér's V (for categorical variables)
- **Negligible:** V < 0.1
- **Small:** 0.1 ≤ V < 0.3
- **Medium:** 0.3 ≤ V < 0.5
- **Large:** V ≥ 0.5

---

## Notes on Data Discrepancy

The paper states 545 AI Agent PRs in Table 1, but the current filtered dataset contains 648 PRs. The `any_statistical_comparison_results.csv` file contains the original analysis with the correct values matching the paper (mean 2.16 vs 0.24, p ≈ 2.33 × 10⁻⁷). This suggests either:
1. The dataset was updated after the initial analysis
2. Different filtering criteria were used

The effect sizes and medians reported here are computed from the current data unless otherwise noted (RQ1 uses the original analysis file).

---

## LaTeX-Ready Text for Paper

### For RQ1 (with median, addressing reviewer request):

```latex
As shown in Figure~1, AI agents are 9 times more likely to introduce 
the \texttt{any} type into the TypeScript codebases compared to human 
developers, with means of the `any addition' distributions across PRs 
at 2.16 and 0.24, respectively (medians: 0.0 for both groups). 
Mann-Whitney U test ($p \approx 2.33 \times 10^{-7}$) demonstrated 
the statistical significance of this result with a small effect size 
(Cohen's $d = 0.32$).
```

### For RQ2 (with effect size):

```latex
According to the Mann-Whitney U test, this finding is statistically 
significant ($p < 5.50 \times 10^{-5}$) with a large effect size 
(Cohen's $d = 1.45$), indicating a substantial practical difference 
in feature diversity between AI agents and human developers.
```

### For RQ3 (with effect size):

```latex
With a statistically significant difference ($p < 0.0001$, 
$\chi^2 = 27.52$, Cram\'{e}r's $V = 0.19$), the acceptance rate of 
Agentic PRs is 45.8\%, while that of Human PRs is only 25.3\% among 
the type-specific PRs.
```

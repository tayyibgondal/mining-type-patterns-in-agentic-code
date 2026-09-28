"""Statistical helpers.

Test selection is carried over unchanged from
`data_analysis/statistical_analysis/all_languages_statistical_analysis.py`,
which was already sound: chi-square with an automatic Fisher fallback under
small cells, Mann-Whitney U for skewed count data, and Cohen's d, rank-biserial
r and Cramer's V as effect sizes.

Four things the reviewers asked for are added here:

  * Wilson confidence intervals on every proportion, since the old report gave
    point estimates only;
  * Cliff's delta, which is the right effect size for the ordinal comparisons
    and does not assume a scale the count data does not have;
  * Benjamini-Hochberg correction, because the per-construct tests are run
    dozens of times per language and were previously uncorrected;
  * a cluster-aware variant that treats the repository rather than the PR as
    the independent unit, because PRs from one repository are not independent.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import (chi2_contingency, fisher_exact, mannwhitneyu, norm,
                         spearmanr)


# --------------------------------------------------------------------------
# Effect sizes
# --------------------------------------------------------------------------

def cohens_d(a, b) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if len(a) < 2 or len(b) < 2:
        return 0.0
    pooled = math.sqrt(((len(a) - 1) * a.var(ddof=1)
                        + (len(b) - 1) * b.var(ddof=1))
                       / (len(a) + len(b) - 2))
    return float((a.mean() - b.mean()) / pooled) if pooled > 0 else 0.0


def rank_biserial(u: float, n1: int, n2: int) -> float:
    if n1 == 0 or n2 == 0:
        return 0.0
    return float((2.0 * u) / (n1 * n2) - 1.0)


def cliffs_delta(a, b) -> float:
    """Cliff's delta via its exact relation to the Mann-Whitney statistic.

    Computed from ranks rather than by pairwise comparison, which would be
    O(n*m) and intractable at these corpus sizes.
    """
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0:
        return 0.0
    u = mannwhitneyu(a, b, alternative="two-sided").statistic
    return float((2.0 * u) / (n1 * n2) - 1.0)


def interpret_delta(d: float) -> str:
    d = abs(d)
    return ("negligible" if d < 0.147 else "small" if d < 0.33
            else "medium" if d < 0.474 else "large")


def interpret_d(d: float) -> str:
    d = abs(d)
    return ("negligible" if d < 0.2 else "small" if d < 0.5
            else "medium" if d < 0.8 else "large")


def cramers_v(chi2: float, n: int, rows: int, cols: int) -> float:
    denom = n * (min(rows, cols) - 1)
    return float(math.sqrt(chi2 / denom)) if denom > 0 else 0.0


def stars(p: float) -> str:
    return ("***" if p < 0.001 else "**" if p < 0.01
            else "*" if p < 0.05 else "ns")


# --------------------------------------------------------------------------
# Intervals
# --------------------------------------------------------------------------

def wilson_interval(successes: int, n: int,
                    confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a proportion.

    Preferred over the normal approximation because several construct
    prevalences sit near 0 or 1, where the normal interval leaves the [0, 1]
    range entirely.
    """
    if n == 0:
        return (0.0, 0.0)
    z = norm.ppf(1 - (1 - confidence) / 2)
    phat = successes / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    margin = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def bootstrap_mean_ci(values, iterations: int = 2000,
                      confidence: float = 0.95,
                      seed: int = 42) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    means = values[rng.integers(0, len(values),
                                size=(iterations, len(values)))].mean(axis=1)
    lo = float(np.percentile(means, 100 * (1 - confidence) / 2))
    hi = float(np.percentile(means, 100 * (1 + confidence) / 2))
    return (lo, hi)


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

@dataclass
class TestResult:
    metric: str
    test: str
    ai: float
    human: float
    p: float
    effect: str
    effect_value: float
    n_ai: int
    n_human: int
    ci_ai: tuple[float, float] = (0.0, 0.0)
    ci_human: tuple[float, float] = (0.0, 0.0)
    detail: dict = field(default_factory=dict)
    p_adjusted: float | None = None

    @property
    def significant(self) -> bool:
        p = self.p_adjusted if self.p_adjusted is not None else self.p
        return p < 0.05

    def row(self) -> dict:
        return {
            "Metric": self.metric, "Test": self.test,
            "AI": self.ai, "Human": self.human,
            "AI_CI_low": self.ci_ai[0], "AI_CI_high": self.ci_ai[1],
            "Human_CI_low": self.ci_human[0], "Human_CI_high": self.ci_human[1],
            "AI_median": self.detail.get("median_ai"),
            "Human_median": self.detail.get("median_human"),
            "n_AI": self.n_ai, "n_Human": self.n_human,
            "p": self.p, "p_adj": self.p_adjusted,
            "Sig": stars(self.p_adjusted if self.p_adjusted is not None
                         else self.p),
            "Effect": self.effect, "EffectValue": self.effect_value,
        }


def proportion_test(succ_ai: int, n_ai: int, succ_hu: int,
                    n_hu: int, metric: str) -> TestResult:
    table = np.array([[succ_ai, n_ai - succ_ai], [succ_hu, n_hu - succ_hu]])
    small = min(n_ai, n_hu) < 50 or (table < 5).any()
    if small:
        odds, p = fisher_exact(table)
        test, effect, value = "Fisher exact", "odds ratio", float(odds)
    else:
        chi2, p, _, _ = chi2_contingency(table)
        test = "Chi-square"
        effect, value = "Cramer's V", cramers_v(chi2, table.sum(), 2, 2)
    return TestResult(
        metric=metric, test=test,
        ai=succ_ai / n_ai if n_ai else 0.0,
        human=succ_hu / n_hu if n_hu else 0.0,
        p=float(p), effect=effect, effect_value=value,
        n_ai=n_ai, n_human=n_hu,
        ci_ai=wilson_interval(succ_ai, n_ai),
        ci_human=wilson_interval(succ_hu, n_hu),
        detail={"successes_ai": succ_ai, "successes_human": succ_hu})


def distribution_test(ai, human, metric: str) -> TestResult:
    ai = np.asarray(ai, dtype=float)
    human = np.asarray(human, dtype=float)
    if len(ai) < 3 or len(human) < 3:
        return TestResult(metric=metric, test="insufficient n",
                          ai=float(ai.mean()) if len(ai) else 0.0,
                          human=float(human.mean()) if len(human) else 0.0,
                          p=1.0, effect="Cliff's delta", effect_value=0.0,
                          n_ai=len(ai), n_human=len(human))
    result = mannwhitneyu(ai, human, alternative="two-sided")
    delta = rank_biserial(result.statistic, len(ai), len(human))
    return TestResult(
        metric=metric, test="Mann-Whitney U",
        ai=float(ai.mean()), human=float(human.mean()),
        p=float(result.pvalue), effect="Cliff's delta", effect_value=delta,
        n_ai=len(ai), n_human=len(human),
        ci_ai=bootstrap_mean_ci(ai), ci_human=bootstrap_mean_ci(human),
        detail={"U": float(result.statistic),
                "median_ai": float(np.median(ai)),
                "median_human": float(np.median(human)),
                "cohens_d": cohens_d(ai, human)})


def cluster_test(frame: pd.DataFrame, value_col: str, metric: str,
                 cluster_col: str = "repo_full_name") -> TestResult:
    """Repository-level test: collapse each repository to its mean first.

    PRs from one repository share a codebase, a review culture and often an
    author, so treating them as independent overstates the evidence. Collapsing
    to one observation per repository per group is the crudest defensible fix
    and is reported alongside the pooled test rather than instead of it.
    """
    collapsed = (frame.groupby([cluster_col, "group"])[value_col]
                 .mean().reset_index())
    ai = collapsed.loc[collapsed.group == "AI", value_col].to_numpy()
    human = collapsed.loc[collapsed.group == "Human", value_col].to_numpy()
    result = distribution_test(ai, human, metric)
    result.test = f"{result.test} (repo-clustered)"
    return result


def benjamini_hochberg(results: list[TestResult]) -> list[TestResult]:
    """Control the false discovery rate across a family of tests."""
    if not results:
        return results
    order = sorted(range(len(results)), key=lambda i: results[i].p)
    m = len(results)
    previous = 1.0
    for rank, index in enumerate(reversed(order), start=1):
        position = m - rank + 1
        adjusted = min(previous, results[index].p * m / position)
        results[index].p_adjusted = adjusted
        previous = adjusted
    return results


# --------------------------------------------------------------------------
# Profile tests: does the group use the SAME constructs, not just as many?
# --------------------------------------------------------------------------

def profile_test(frame: pd.DataFrame, columns: list[str], metric: str,
                 denom_col: str = "denom_lines", iterations: int = 10_000,
                 seed: int = 42) -> TestResult:
    """Permutation test on the distance between the two usage profiles.

    A family-level volume test answers "do they use as many". It cannot answer
    "do they use the same ones", because a group could match the total while
    spending it on entirely different constructs. This does answer that.

    The statistic is the L1 distance between the AI vector of mean per-100-line
    rates and the human vector, one entry per construct. Group labels are then
    shuffled and the statistic recomputed, which gives the distribution of the
    distance under the null that group carries no information about the
    profile. Only group means are needed per shuffle, so this stays cheap at
    corpus scale where a full distance matrix would not.

    Reported alongside it is the Spearman rank correlation between the two
    profiles. The two numbers answer different halves of the question: a high
    rho with a small p means the groups agree on which constructs matter and
    differ only in how hard they lean on them, while a low rho means the
    preference ordering itself differs.
    """
    if not columns:
        return TestResult(metric=metric, test="no constructs", ai=0.0,
                          human=0.0, p=1.0, effect="Spearman rho",
                          effect_value=0.0, n_ai=0, n_human=0)

    rates = (100 * frame[columns].to_numpy(dtype=float)
             / frame[denom_col].to_numpy(dtype=float)[:, None])
    is_ai = (frame["group"].to_numpy() == "AI")
    n_ai, n_human = int(is_ai.sum()), int((~is_ai).sum())
    if n_ai < 3 or n_human < 3:
        return TestResult(metric=metric, test="insufficient n", ai=0.0,
                          human=0.0, p=1.0, effect="Spearman rho",
                          effect_value=0.0, n_ai=n_ai, n_human=n_human)

    profile_ai = rates[is_ai].mean(axis=0)
    profile_hu = rates[~is_ai].mean(axis=0)
    observed = float(np.abs(profile_ai - profile_hu).sum())

    rho = 0.0
    if len(columns) > 2:
        rho = float(spearmanr(profile_ai, profile_hu).statistic)
        if not np.isfinite(rho):
            rho = 0.0

    rng = np.random.default_rng(seed)
    labels = is_ai.copy()
    hits = 0
    for _ in range(iterations):
        rng.shuffle(labels)
        d = np.abs(rates[labels].mean(axis=0)
                   - rates[~labels].mean(axis=0)).sum()
        if d >= observed:
            hits += 1
    # Add-one correction: a permutation p is never reported as exactly zero,
    # since the observed arrangement is itself one draw from the null.
    p = (hits + 1) / (iterations + 1)

    return TestResult(
        metric=metric, test=f"profile permutation ({iterations:,}x)",
        ai=float(profile_ai.sum()), human=float(profile_hu.sum()),
        p=p, effect="Spearman rho", effect_value=rho,
        n_ai=n_ai, n_human=n_human,
        detail={"L1_distance": observed, "n_constructs": len(columns),
                "median_ai": float(np.median(rates[is_ai].sum(axis=1))),
                "median_human": float(np.median(rates[~is_ai].sum(axis=1)))})

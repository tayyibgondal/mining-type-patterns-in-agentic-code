"""Run every research question against the rebuilt corpus.

Replaces `data_analysis/statistical_analysis/all_languages_statistical_analysis.py`.
The important structural change is that construct counts are read from columns
the extractor wrote, not recomputed from `patch_text` by a second set of
regexes at report time. The old module recounted, the figure scripts recounted
differently again, and the two disagreed.

Research questions, renumbered to match the paper's intended order:

    RQ1  type patterns   - expressiveness and safety families
    RQ2  escape hatches  - escape family, Tier A and Tier B kept apart,
                           suppression reported on its own unit
    RQ3  acceptance      - merged vs not, now available for all three
                           languages rather than TypeScript alone

Reporting rules carried over from the taxonomy:

  * Tier A and Tier B counts are never summed. Tier A waives a guarantee,
    Tier B relocates it to a runtime check; adding them yields a number that
    means nothing.
  * The headline metric is gross additions. Removals are reported separately
    and net is secondary, because under a net metric a refactor that replaces
    ten `any` annotations with concrete types looks like a no-op.
  * Constructs flagged `reliable=False` in the catalogue are reported with
    their measured precision but excluded from the tests.
  * Every per-construct family of tests is Benjamini-Hochberg corrected.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from analysis.stats import (  # noqa: E402
    TestResult, benjamini_hochberg, cluster_test, distribution_test,
    profile_test, proportion_test, stars, wilson_interval)
from catalogue.constructs import (  # noqa: E402
    HEADLINE_ESCAPE, LANGUAGES, NESTED_KEYS, by_family, constructs_for,
    get_by_key)

DATA_DIR = {
    "TypeScript": REPO / "datasets" / "typescript_data",
    "C#": REPO / "datasets" / "csharp_data",
    "Rust": REPO / "datasets" / "rust_data",
}
OUTDIR = REPO / "analysis" / "results"

NESTED = {child for children in NESTED_KEYS.values() for child in children}


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def load_corpus(language: str, stage: str = "stage2") -> pd.DataFrame:
    """Load the analysed corpus, falling back to Stage 1 when Stage 2 is absent.

    The fallback exists so the analysis can be developed and smoke-tested
    while the LLM batches are still running. Any report produced from Stage 1
    is labelled as such rather than silently passed off as final.
    """
    directory = DATA_DIR[language]
    stage2 = directory / "stage2_corpus.parquet"
    if stage == "stage2" and stage2.exists():
        frame = pd.read_parquet(stage2)
        frame.attrs["stage"] = "stage2"
    else:
        frames = [pd.read_parquet(directory / f"stage1_{g}.parquet")
                  for g in ("agent", "human")
                  if (directory / f"stage1_{g}.parquet").exists()]
        if not frames:
            raise FileNotFoundError(f"no corpus for {language}")
        frame = pd.concat(frames, ignore_index=True)
        frame.attrs["stage"] = "stage1"

    assert len(frame) == frame.pr_key.nunique(), \
        f"{language}: pr_key is not unique in the analysed corpus"

    # Denominator for the per-100-changed-lines normalisation. Uses lines the
    # parser actually counted, not the PR's global additions, so files in other
    # languages do not dilute the rate.
    frame["denom_lines"] = frame["lines_added"].clip(lower=1)
    return frame


def split_groups(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (frame[frame.group == "AI"], frame[frame.group == "Human"])


# --------------------------------------------------------------------------
# Metric construction
# --------------------------------------------------------------------------

def family_frame(frame: pd.DataFrame, language: str,
                 family: str) -> pd.DataFrame:
    """Per-PR totals and diversity for one construct family."""
    members = [c for c in by_family(language, family)
               if c.key not in NESTED and c.scope == "line"]
    add_cols = [c.add_col for c in members if c.add_col in frame.columns]
    out = pd.DataFrame(index=frame.index)
    out["total"] = frame[add_cols].sum(axis=1) if add_cols else 0
    out["unique"] = ((frame[add_cols] > 0).sum(axis=1) if add_cols else 0)
    out["per100"] = 100 * out["total"] / frame["denom_lines"]
    out["group"] = frame["group"]
    out["repo_full_name"] = frame["repo_full_name"]
    return out


def family_add_cols(frame: pd.DataFrame, language: str, family: str,
                    reliable_only: bool = True) -> list[str]:
    """The add columns a family's tests and profile are built from."""
    return [c.add_col for c in constructs_for(language)
            if c.family == family and c.key not in NESTED
            and c.scope == "line" and c.add_col in frame.columns
            and (c.reliable or not reliable_only)]


def construct_tests(frame: pd.DataFrame, language: str, family: str,
                    reliable_only: bool = True) -> list[TestResult]:
    """One test per construct in a family, then BH-corrected together."""
    ai, human = split_groups(frame)
    results: list[TestResult] = []
    for c in constructs_for(language):
        if c.family != family or c.key in NESTED or c.scope != "line":
            continue
        if reliable_only and not c.reliable:
            continue
        if c.add_col not in frame.columns:
            continue
        rate_ai = 100 * ai[c.add_col] / ai["denom_lines"]
        rate_hu = 100 * human[c.add_col] / human["denom_lines"]
        result = distribution_test(rate_ai, rate_hu,
                                   f"{c.display_name} [{c.id}]")
        result.detail["tier"] = c.tier
        result.detail["failure_mode"] = c.failure_mode
        results.append(result)
    return benjamini_hochberg(results)


# --------------------------------------------------------------------------
# Research questions
# --------------------------------------------------------------------------

def rq1_type_patterns(frame: pd.DataFrame, language: str) -> list[TestResult]:
    """How do the two groups use the language's type patterns?"""
    results: list[TestResult] = []
    for family in ("expressiveness", "safety"):
        metrics = family_frame(frame, language, family)
        ai, human = split_groups(metrics)
        for column, label in (("total", "volume per PR"),
                              ("unique", "distinct constructs per PR"),
                              ("per100", "per 100 changed lines")):
            results.append(distribution_test(
                ai[column], human[column], f"{family}: {label}"))
        results.append(cluster_test(metrics, "per100",
                                    f"{family}: per 100 lines"))
        # Omnibus: do the two groups spend their construct budget on the same
        # constructs? The volume tests above cannot answer that.
        results.append(profile_test(
            frame, family_add_cols(frame, language, family),
            f"{family}: usage profile (omnibus)"))
    results.extend(construct_tests(frame, language, "expressiveness"))
    results.extend(construct_tests(frame, language, "safety"))
    return results


def rq2_escape_hatches(frame: pd.DataFrame, language: str) -> list[TestResult]:
    """How do the two groups use escape hatches?"""
    ai, human = split_groups(frame)
    results: list[TestResult] = []

    # Headline: the constructs that share a row in the cross-language mapping.
    for key in HEADLINE_ESCAPE[language]:
        construct = get_by_key(language, key)
        col = construct.add_col
        if col not in frame.columns:
            continue
        label = f"HEADLINE {construct.display_name} [{construct.id}]"
        results.append(proportion_test(
            int((ai[col] > 0).sum()), len(ai),
            int((human[col] > 0).sum()), len(human),
            f"{label}: prevalence"))
        results.append(distribution_test(
            100 * ai[col] / ai["denom_lines"],
            100 * human[col] / human["denom_lines"],
            f"{label}: per 100 changed lines"))
        results.append(cluster_test(
            frame.assign(_r=100 * frame[col] / frame["denom_lines"]),
            "_r", f"{label}: per 100 lines"))
        # Additions against removals: a ratio above one means the group leaves
        # more of the construct behind than it takes out.
        for side, name in ((construct.add_col, "additions"),
                           (construct.rem_col, "removals")):
            if side in frame.columns:
                results.append(distribution_test(
                    ai[side], human[side], f"{label}: {name} per PR"))

    # Tier A and Tier B totals, kept apart on purpose.
    for tier in ("A", "B"):
        cols = [c.add_col for c in constructs_for(language)
                if c.family == "escape" and c.tier == tier
                and c.key not in NESTED and c.add_col in frame.columns]
        if not cols:
            continue
        rate_ai = 100 * ai[cols].sum(axis=1) / ai["denom_lines"]
        rate_hu = 100 * human[cols].sum(axis=1) / human["denom_lines"]
        results.append(distribution_test(
            rate_ai, rate_hu,
            f"Tier {tier} escape hatches: per 100 changed lines"))

    # Suppression has its own unit: PRs containing one, not occurrences per
    # line. One `#nullable disable` waives an unbounded number of checks.
    sup = [c.add_col for c in by_family(language, "suppression")
           if c.add_col in frame.columns]
    if sup:
        results.append(proportion_test(
            int((ai[sup].sum(axis=1) > 0).sum()), len(ai),
            int((human[sup].sum(axis=1) > 0).sum()), len(human),
            "suppression directives: share of PRs containing one"))

    # Omnibus over the escape family, the direct answer to "similarly?".
    results.append(profile_test(
        frame, family_add_cols(frame, language, "escape"),
        "escape hatches: usage profile (omnibus)"))

    results.extend(construct_tests(frame, language, "escape"))
    return results


def rq3_acceptance(frame: pd.DataFrame, language: str) -> list[TestResult]:
    """Are agent PRs accepted at a different rate from human PRs?"""
    merged = frame["merged_at"].astype(str).str.len() > 4
    work = frame.assign(_merged=merged)
    ai, human = split_groups(work)
    results = [proportion_test(
        int(ai._merged.sum()), len(ai),
        int(human._merged.sum()), len(human),
        "acceptance: merged share")]

    # Does carrying a Tier A escape hatch predict acceptance within a group?
    cols = [c.add_col for c in constructs_for(language)
            if c.family == "escape" and c.tier == "A"
            and c.key not in NESTED and c.add_col in frame.columns]
    if cols:
        for label, subset in (("agent", ai), ("human", human)):
            has = subset[cols].sum(axis=1) > 0
            if has.sum() < 5 or (~has).sum() < 5:
                continue
            results.append(proportion_test(
                int(subset.loc[has, "_merged"].sum()), int(has.sum()),
                int(subset.loc[~has, "_merged"].sum()), int((~has).sum()),
                f"acceptance within {label} PRs: "
                f"with vs without a Tier A escape hatch"))

    # Repo-matched acceptance. The comparison that survives the objection that
    # the two arms come from projects with different merge cultures.
    shared = set(ai.repo_full_name) & set(human.repo_full_name)
    if shared:
        sub = work[work.repo_full_name.isin(shared)]
        s_ai, s_hu = split_groups(sub)
        if len(s_ai) >= 5 and len(s_hu) >= 5:
            results.append(proportion_test(
                int(s_ai._merged.sum()), len(s_ai),
                int(s_hu._merged.sum()), len(s_hu),
                f"REPO-MATCHED acceptance: merged share "
                f"({len(shared)} shared repos)"))

    # Per-agent acceptance against the pooled human rate, so the reader can see
    # whether one agent carries the pooled difference.
    hu_succ, hu_n = int(human._merged.sum()), len(human)
    for agent, rows in ai.groupby("agent"):
        if len(rows) < 20:
            continue
        results.append(proportion_test(
            int(rows._merged.sum()), len(rows), hu_succ, hu_n,
            f"acceptance: {agent} vs all humans"))
    return results


def repo_matched(frame: pd.DataFrame, language: str) -> list[TestResult]:
    """Restrict to repositories that appear in both arms.

    The strongest available answer to the objection that the two arms come
    from different sources: within one repository the codebase, the review
    culture and the project norms are held constant.
    """
    ai, human = split_groups(frame)
    shared = set(ai.repo_full_name) & set(human.repo_full_name)
    if not shared:
        return []
    subset = frame[frame.repo_full_name.isin(shared)]
    results = []
    for key in HEADLINE_ESCAPE[language]:
        construct = get_by_key(language, key)
        if construct.add_col not in subset.columns:
            continue
        s_ai, s_hu = split_groups(subset)
        results.append(distribution_test(
            100 * s_ai[construct.add_col] / s_ai["denom_lines"],
            100 * s_hu[construct.add_col] / s_hu["denom_lines"],
            f"REPO-MATCHED {construct.display_name}: per 100 changed lines "
            f"({len(shared)} shared repos)"))
    return results


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def analyse(language: str, stage: str) -> tuple[pd.DataFrame, list[str]]:
    frame = load_corpus(language, stage)
    ai, human = split_groups(frame)
    lines = [f"## {language}",
             "",
             f"Corpus stage: **{frame.attrs['stage']}**. "
             f"{len(ai):,} agent PRs, {len(human):,} human PRs, "
             f"{frame.repo_full_name.nunique():,} repositories.",
             ""]

    rows = []
    for rq, runner in (("RQ1 type patterns", rq1_type_patterns),
                       ("RQ2 escape hatches", rq2_escape_hatches),
                       ("RQ3 acceptance", rq3_acceptance),
                       ("Robustness", repo_matched)):
        results = runner(frame, language)
        if not results:
            continue
        lines += [f"### {rq}", "",
                  "| Metric | Test | AI | Human | p | adj p | Effect |",
                  "|---|---|---|---|---|---|---|"]
        for r in results:
            adj = f"{r.p_adjusted:.3g}" if r.p_adjusted is not None else "-"
            lines.append(
                f"| {r.metric} | {r.test} | {r.ai:.3f} | {r.human:.3f} | "
                f"{r.p:.3g} {stars(r.p)} | {adj} | "
                f"{r.effect} {r.effect_value:.3f} |")
            row = r.row()
            row.update(Language=language, RQ=rq)
            rows.append(row)
        lines.append("")
    return pd.DataFrame(rows), lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--language", choices=list(LANGUAGES), action="append")
    ap.add_argument("--stage", choices=["stage1", "stage2"], default="stage2")
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    all_rows, report = [], ["# Statistical results", ""]
    for language in (args.language or list(LANGUAGES)):
        frame, lines = analyse(language, args.stage)
        all_rows.append(frame)
        report += lines

    combined = pd.concat(all_rows, ignore_index=True)
    combined.to_csv(OUTDIR / "statistical_results.csv", index=False)
    (OUTDIR / "STATISTICAL_REPORT.md").write_text("\n".join(report))
    print(f"wrote {len(combined):,} test results to "
          f"{(OUTDIR / 'statistical_results.csv').relative_to(REPO)}")
    print(f"wrote {(OUTDIR / 'STATISTICAL_REPORT.md').relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

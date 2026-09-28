"""Count catalogue constructs in a PR patch.

One entry point, `count_patch`, used by all three extractors and by the
analysis module. Previously the extractors counted one way, the statistics
module recounted a different way from `patch_text` at figure time, and a figure
script inlined a third set of regexes. All three disagreed.

Counts are per occurrence on added (`+`) and removed (`-`) lines separately.
The reported RQ2 metric is gross additions; removals are reported alongside so
that churn is visible, and net is a secondary derived quantity. Under a net
metric a refactor replacing ten `any` annotations with concrete types is
indistinguishable from a PR that touched nothing.
"""
from __future__ import annotations

from .constructs import Construct, constructs_for
from .preprocess import PreparedDiff, prepare

# Constructs that must read the raw line. Stripping comments would destroy a
# `// @ts-ignore` or a `// SAFETY:` comment, which are the whole signal.
_RAW_TEXT_IDS = frozenset({"TS-E5", "TS-E5b", "TS-E5c", "RS-D5", "TS-C6"})

# Panicking macros are idiomatic in tests; counting them there would say more
# about test style than about how agents handle failure.
_SKIP_IN_TESTS = frozenset({"RS-E6"})


def needs_raw_text(construct: Construct) -> bool:
    # Config files are JSON or XML data, not code: blanking string
    # contents would erase the very keys the flag looks for.
    return construct.id in _RAW_TEXT_IDS or construct.scope == "pr_flag"


def _count_side(construct: Construct, lines) -> int:
    total = 0
    raw = needs_raw_text(construct)
    skip_tests = construct.id in _SKIP_IN_TESTS
    for entry in lines:
        if skip_tests and entry.is_test:
            continue
        total += construct.count_line(entry.raw if raw else entry.clean)
    return total


def count_prepared(prepared: PreparedDiff, language: str) -> dict[str, int]:
    """Count every catalogue construct over an already-parsed diff."""
    counts: dict[str, int] = {}

    for construct in constructs_for(language):
        if construct.scope == "pr_flag":
            # Config-file constructs are a per-PR binary, not an occurrence
            # count: one `"strict": false` waives an unbounded number of
            # checks, so it is not commensurable with a per-line construct.
            hit = any(construct.count_line(line)
                      for line in prepared.config_lines)
            counts[construct.add_col] = int(hit)
            counts[construct.rem_col] = 0
            continue

        counts[construct.add_col] = _count_side(construct, prepared.added)
        counts[construct.rem_col] = _count_side(construct, prepared.removed)

    return counts


def count_patch(patch_text: str | None, language: str) -> dict[str, int]:
    """Count constructs plus the churn denominators for one PR."""
    prepared = prepare(patch_text, language)
    counts = count_prepared(prepared, language)
    counts["files_counted"] = prepared.files_counted
    counts["lines_added"] = prepared.lines_added
    counts["lines_removed"] = prepared.lines_removed
    return counts


def empty_counts(language: str) -> dict[str, int]:
    """Zero-filled row, for PRs with no usable patch."""
    counts = {col: 0 for c in constructs_for(language)
              for col in (c.add_col, c.rem_col)}
    counts.update(files_counted=0, lines_added=0, lines_removed=0)
    return counts


def family_total(counts: dict[str, int], language: str, family: str,
                 side: str = "add") -> int:
    """Sum one family. Never mixes Tier A with Tier B, see totals_by_tier."""
    from .constructs import NESTED_KEYS, by_family
    nested = {k for parent in NESTED_KEYS.values() for k in parent}
    return sum(
        counts.get(c.add_col if side == "add" else c.rem_col, 0)
        for c in by_family(language, family)
        if c.key not in nested          # sub-counters would double-count
    )


def totals_by_tier(counts: dict[str, int], language: str,
                   side: str = "add") -> dict[str, int]:
    """Per-tier totals. Tier A and Tier B are deliberately kept apart.

    Tier A waives a guarantee outright; Tier B relocates it to a runtime check.
    Adding them produces a number that means nothing, which is what the earlier
    aggregate 'escape hatch count' did.
    """
    from .constructs import NESTED_KEYS, constructs_for as _cs
    nested = {k for parent in NESTED_KEYS.values() for k in parent}
    out = {"A": 0, "B": 0, "C": 0, "D": 0}
    for c in _cs(language):
        if c.key in nested:
            continue
        col = c.add_col if side == "add" else c.rem_col
        out[c.tier] += counts.get(col, 0)
    return out

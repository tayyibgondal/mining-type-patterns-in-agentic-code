"""The Stage 1 retention predicate.

Unchanged in form from Section 4.3 of the paper, which is already defensible:

    Retain(p) = File(p) and (Diff(p) or Cue(p)) and not Excl(p)

  File(p)  p modifies at least one hand-written source file of the language
  Diff(p)  the diff matches at least one catalogue construct pattern
  Cue(p)   the title, body or commit messages carry a construct-related cue
  Excl(p)  the PR matches a language-specific exclusion pattern

What changed is that Diff(p) now consults the catalogue instead of a private
list of regexes, so Stage 1 and the construct counts can no longer disagree
about what a construct is.

Stage 1 is deliberately tuned for recall. A false positive here is recoverable,
because Stage 2 rejects PRs that do not involve construct-related work. A false
negative is permanent: no later stage can reintroduce a PR Stage 1 discarded.
Which disjunct fired is recorded so the contribution of each signal can be
audited, and so PRs retained on a cue alone, the weakest signal, can be counted.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .constructs import constructs_for
from .preprocess import PreparedDiff

# Natural-language cues developers use when describing type work.
SHARED_CUES = (
    r"\btype[- ]?safe(?:ty)?\b", r"\btype system\b", r"\btype annotation",
    r"\btype error", r"\btype check", r"\btyping\b", r"\bstrict(?:ly)? typed\b",
    r"\bcompile[- ]?time (?:error|check)", r"\bfix(?:es|ed)? types?\b",
)

LANGUAGE_CUES: dict[str, tuple[str, ...]] = {
    "TypeScript": SHARED_CUES + (
        r"\bany type\b", r"\bts-ignore\b", r"\btsconfig\b", r"\bgenerics?\b",
        r"\bnon-null\b", r"\btype guard\b", r"\bnoImplicitAny\b",
        r"\bstrictNullChecks\b", r"\btype assertion\b", r"\bunknown type\b",
    ),
    "C#": SHARED_CUES + (
        r"\bdynamic\b", r"\bnullable\b", r"\bnull[- ]forgiving\b",
        r"\bgenerics?\b", r"\bnullable reference\b", r"\bunsafe\b",
        r"\bpattern match", r"\brecord type\b", r"\bboxing\b",
    ),
    "Rust": SHARED_CUES + (
        r"\bunsafe\b", r"\blifetime", r"\bborrow(?:ck| checker)?\b",
        r"\btrait bound", r"\bgenerics?\b", r"\bunwrap\b", r"\bpanic\b",
        r"\bimpl Trait\b", r"\bdyn Trait\b", r"\bownership\b",
    ),
}

# Language-specific false-positive traps in the title and body.
EXCLUSIONS: dict[str, tuple[str, ...]] = {
    "TypeScript": (
        r"\bcontent[- ]?type\b", r"\bmime[- ]?type\b", r"\bmedia[- ]?type\b",
        r"\btype=[\"']", r"\bevent type\b", r"\blog (?:type|level)\b",
    ),
    "C#": (
        r"\bcontent[- ]?type\b", r"\bmime[- ]?type\b", r"\bmedia[- ]?type\b",
        r"\btype=[\"']",
    ),
    "Rust": (
        r"\bcontent[- ]?type\b", r"\bmime[- ]?type\b", r"\bmedia[- ]?type\b",
    ),
}


def _compile(patterns) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


_CUE_RX = {lang: _compile(pats) for lang, pats in LANGUAGE_CUES.items()}
_EXCL_RX = {lang: _compile(pats) for lang, pats in EXCLUSIONS.items()}


@dataclass
class RetainDecision:
    retained: bool
    file_ok: bool
    diff_hit: bool
    cue_hit: bool
    excluded: bool
    construct_total: int

    @property
    def method(self) -> str:
        """Which signals fired, for auditing Stage 1's recall."""
        if not self.retained:
            return "rejected"
        parts = [name for name, hit in
                 (("diff", self.diff_hit), ("cue", self.cue_hit)) if hit]
        return "|".join(parts) or "none"


def has_cue(text: str, language: str) -> bool:
    if not text:
        return False
    return any(rx.search(text) for rx in _CUE_RX[language])


def is_excluded(text: str, language: str) -> bool:
    if not text:
        return False
    return any(rx.search(text) for rx in _EXCL_RX[language])


def decide(prepared: PreparedDiff, counts: dict[str, int],
           title: str, body: str, language: str) -> RetainDecision:
    """Apply the retention predicate to one PR."""
    file_ok = prepared.files_counted > 0

    total = sum(counts.get(c.add_col, 0) + counts.get(c.rem_col, 0)
                for c in constructs_for(language))
    diff_hit = total > 0

    text = f"{title or ''}\n{body or ''}"
    cue_hit = has_cue(text, language)
    excluded = is_excluded(text, language)

    retained = file_ok and (diff_hit or cue_hit) and not excluded
    return RetainDecision(retained=retained, file_ok=file_ok,
                          diff_hit=diff_hit, cue_hit=cue_hit,
                          excluded=excluded, construct_total=total)

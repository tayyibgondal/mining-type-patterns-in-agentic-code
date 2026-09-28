"""Stage 1: count catalogue constructs and apply the retention predicate.

Replaces `extract_typescript_type_prs.py`, `extract_csharp_type_prs.py`,
`extract_rust_type_prs.py` and the three `extract_human_*` scripts. Six
near-identical files is how the catalogues drifted apart in the first place.

Both arms flow through one code path:

    agent  AIDev cache  -> catalogue.aidev.build_agent_corpus
    human  new scrape   -> datasets/<lang>_data/human_corpus.parquet

Output: `datasets/<lang>_data/stage1_<group>.parquet`, one row per PR, carrying
every catalogue count column so the counts survive to the analysis. The old
pipeline computed these and then dropped them on export for TypeScript and C#,
which is why every figure recounted from `patch_text` with a different regex.

Two invariants are asserted rather than trusted:
  * `pr_key` is unique in every output frame;
  * retained PRs are a subset of the input.

Usage:
    python3 scripts/stage1_extract.py                  # all languages, both arms
    python3 scripts/stage1_extract.py --language Rust --limit 500
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from catalogue import aidev  # noqa: E402
from catalogue.constructs import LANGUAGES, constructs_for  # noqa: E402
from catalogue.count import count_prepared  # noqa: E402
from catalogue.preprocess import prepare, prepare_files  # noqa: E402
from catalogue.retain import decide  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUTDIR = {
    "TypeScript": REPO / "datasets" / "typescript_data",
    "C#": REPO / "datasets" / "csharp_data",
    "Rust": REPO / "datasets" / "rust_data",
}

PATCH_EXCERPT_CHARS = 6000

META_COLUMNS = [
    "pr_key", "language", "group", "agent", "repo_full_name", "number",
    "html_url", "title", "body", "state", "created_at", "merged_at",
    "additions", "deletions", "changes", "lang_files_changed",
]


def _process(records, language: str, from_files: bool) -> pd.DataFrame:
    rows = []
    for rec in records:
        if from_files:
            prepared = prepare_files(rec.get("_files") or [], language)
        else:
            prepared = prepare(rec.get("patch_text"), language)

        counts = count_prepared(prepared, language)
        decision = decide(prepared, counts, rec.get("title"),
                          rec.get("body"), language)

        row = {k: rec.get(k) for k in META_COLUMNS}
        row.update(counts)
        row.update(
            files_counted=prepared.files_counted,
            lines_added=prepared.lines_added,
            lines_removed=prepared.lines_removed,
            construct_total=decision.construct_total,
            retained=decision.retained,
            detection_method=decision.method,
            file_ok=decision.file_ok,
            diff_hit=decision.diff_hit,
            cue_hit=decision.cue_hit,
            excluded=decision.excluded,
            # An excerpt, not the full diff. Counts are already computed, and
            # Stage 2 shows the model a truncated patch anyway. Storing full
            # diffs for ~100k PRs would cost roughly a gigabyte; the full text
            # remains recoverable from the source corpora via pr_key.
            patch_excerpt=(rec.get("patch_text") or "")[:PATCH_EXCERPT_CHARS],
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _agent_records(language: str, limit: int | None):
    frame = aidev.build_agent_corpus(language)
    if frame.empty:
        return [], 0
    if limit:
        frame = frame.head(limit)
    # Rebuild patch_text from the (filename, patch) pairs so Stage 2 and the
    # validation sheets have something to show a human reviewer.
    records = frame.to_dict("records")
    for rec in records:
        rec["patch_text"] = "\n".join(
            f"=== {fn} ===\n{p}" for fn, p in (rec.get("_files") or []) if p)
    return records, len(frame)


def _human_records(language: str, limit: int | None):
    path = OUTDIR[language] / "human_corpus.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing. Run scripts/normalise_human_corpus.py first.")
    frame = pd.read_parquet(path)
    if limit:
        frame = frame.head(limit)
    return frame.to_dict("records"), len(frame)


def run(language: str, group: str, limit: int | None) -> pd.DataFrame:
    started = time.time()
    if group == "agent":
        records, total = _agent_records(language, limit)
        frame = _process(records, language, from_files=True)
    else:
        records, total = _human_records(language, limit)
        frame = _process(records, language, from_files=False)

    if frame.empty:
        print(f"[{language}/{group}] no records")
        return frame

    assert len(frame) == frame.pr_key.nunique(), \
        f"{language}/{group}: pr_key not unique"

    kept = frame[frame.retained].copy()
    OUTDIR[language].mkdir(parents=True, exist_ok=True)
    dest = OUTDIR[language] / f"stage1_{group}.parquet"
    kept.to_parquet(dest, index=False, compression="zstd")

    pct = 100 * len(kept) / max(total, 1)
    by_method = kept.detection_method.value_counts().to_dict()
    print(f"[{language}/{group}] {total:,} -> {len(kept):,} retained "
          f"({pct:.1f}%)  in {time.time() - started:.0f}s")
    print(f"    no source file : {(~frame.file_ok).sum():,}")
    print(f"    excluded       : {frame.excluded.sum():,}")
    print(f"    signal         : {by_method}")
    print(f"    -> {dest.relative_to(REPO)} "
          f"({dest.stat().st_size / 1e6:.1f} MB)")
    return kept


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--language", choices=list(LANGUAGES), action="append")
    ap.add_argument("--group", choices=["agent", "human"], action="append")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    for language in (args.language or list(LANGUAGES)):
        print(f"\n### {language}  "
              f"({len(constructs_for(language))} constructs)")
        for group in (args.group or ["agent", "human"]):
            run(language, group, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Map the new human PR scrape into the canonical schema.

`more_human_pr_data/` holds 12,690 TypeScript, 15,417 Rust and 15,260 C# human
PRs, against the 235 / 145 / 195 the paper currently uses. Every row carries a
non-empty diff, and unlike the old human sets it carries rejected and pending
PRs as well as merged ones, so acceptance stops being 100% by construction.

The two schemas share almost no column names, so nothing is drop-in:

    diff          -> patch_text        pr_number     -> number
    pr_url        -> html_url          repo          -> repo_full_name
    changed_files -> changes           ts_files      -> lang_files_changed
    state (merged/rejected/pending)    -> state (closed/closed/open) + merged_at

`pr_key` is synthesised here as `<language>:<owner/repo>#<number>` and is the
primary key for every later stage. De-duplication happens on it at write time.
The old pipeline had no such key: a merge dropped metadata from 189 TypeScript
human rows that collapsed to 21 real PRs, and the resulting 269-row file was
reported as 269 PRs in Table 1 and 101 in Table 3. That cannot recur.

Output is parquet with zstd rather than CSV. The three source files total
844 MB; the parquet output is a fraction of that, which matters because the
AIDev cache already competes for disk.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "more_human_pr_data"

csv.field_size_limit(sys.maxsize)

# language -> (source csv, per-language file-count column, output directory)
SOURCES: dict[str, tuple[Path, str, Path]] = {
    "TypeScript": (SRC / "TypeScript" / "human_ts_prs.csv", "ts_files",
                   REPO / "datasets" / "typescript_data"),
    "C#": (SRC / "CSharp" / "human_csharp_prs.csv", "cs_files",
           REPO / "datasets" / "csharp_data"),
    "Rust": (SRC / "Rust" / "human_rust_prs.csv", "rs_files",
             REPO / "datasets" / "rust_data"),
}

CANONICAL = [
    "pr_key", "language", "group", "agent",
    "repo_full_name", "repo_stars", "number", "html_url",
    "title", "body", "author",
    "state", "created_at", "closed_at", "merged_at",
    "additions", "deletions", "changes", "lang_files_changed",
    "patch_text",
]

# The scrape records an outcome, not GitHub's raw state. Map back so the
# acceptance analysis uses one vocabulary across both arms.
STATE_MAP = {"merged": "closed", "rejected": "closed", "pending": "open"}


def _int(value: str | None) -> int:
    try:
        return int(float(value)) if value not in (None, "") else 0
    except (TypeError, ValueError):
        return 0


def normalise(language: str, batch_size: int = 2000,
              limit: int | None = None) -> Path:
    src, files_col, outdir = SOURCES[language]
    if not src.exists():
        raise FileNotFoundError(src)
    outdir.mkdir(parents=True, exist_ok=True)
    dest = outdir / "human_corpus.parquet"

    seen: set[str] = set()
    batches: list[pd.DataFrame] = []
    rows: list[dict] = []
    kept = skipped_dupe = skipped_nodiff = total = 0

    def flush() -> None:
        if rows:
            batches.append(pd.DataFrame(rows, columns=CANONICAL))
            rows.clear()

    with src.open(newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            total += 1
            if limit and total > limit:
                break
            repo = (raw.get("repo") or "").strip()
            number = (raw.get("pr_number") or "").strip()
            if not repo or not number:
                continue
            pr_key = f"{language}:{repo}#{number}"
            if pr_key in seen:
                skipped_dupe += 1
                continue
            diff = raw.get("diff") or ""
            if not diff.strip():
                skipped_nodiff += 1
                continue
            seen.add(pr_key)

            state_word = (raw.get("state") or "").strip().lower()
            merged_at = (raw.get("merged_at") or "").strip()
            if state_word == "merged" and not merged_at:
                # The scrape's own outcome label is authoritative; some merged
                # PRs arrive with an empty timestamp.
                merged_at = (raw.get("closed_at") or "").strip()

            rows.append({
                "pr_key": pr_key,
                "language": language,
                "group": "Human",
                "agent": "Human",
                "repo_full_name": repo,
                "repo_stars": _int(raw.get("repo_stars")),
                "number": _int(number),
                "html_url": raw.get("pr_url") or "",
                "title": raw.get("title") or "",
                "body": raw.get("body") or "",
                "author": raw.get("author") or "",
                "state": STATE_MAP.get(state_word, "open"),
                "created_at": raw.get("created_at") or "",
                "closed_at": raw.get("closed_at") or "",
                "merged_at": merged_at if state_word == "merged" else "",
                "additions": _int(raw.get("additions")),
                "deletions": _int(raw.get("deletions")),
                "changes": _int(raw.get("changed_files")),
                "lang_files_changed": _int(raw.get(files_col)),
                "patch_text": diff,
            })
            kept += 1
            if len(rows) >= batch_size:
                flush()

    flush()
    frame = pd.concat(batches, ignore_index=True) if batches \
        else pd.DataFrame(columns=CANONICAL)

    assert len(frame) == frame.pr_key.nunique(), "pr_key is not unique"
    frame.to_parquet(dest, index=False, compression="zstd")

    merged = (frame.merged_at.astype(str).str.len() > 0).sum()
    closed = ((frame.state == "closed") & (frame.merged_at == "")).sum()
    print(f"[{language}]")
    print(f"  read      {total:,} rows from {src.name}")
    print(f"  kept      {kept:,}   duplicates {skipped_dupe:,}   "
          f"empty diff {skipped_nodiff:,}")
    print(f"  merged    {merged:,}   rejected {closed:,}   "
          f"open {(frame.state == 'open').sum():,}")
    print(f"  repos     {frame.repo_full_name.nunique():,}")
    print(f"  dates     {frame.created_at.min()[:10]} .. "
          f"{frame.created_at.max()[:10]}")
    print(f"  -> {dest.relative_to(REPO)}  "
          f"({dest.stat().st_size / 1e6:.1f} MB)")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--language", choices=list(SOURCES), action="append",
                    help="restrict to one language (repeatable)")
    ap.add_argument("--limit", type=int, default=None,
                    help="stop after N source rows, for smoke tests")
    args = ap.parse_args()
    for language in (args.language or list(SOURCES)):
        normalise(language, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Cache the AIDev tables locally, filtered to the three studied languages.

Two problems this solves.

First, each extractor previously streamed all four tables from HuggingFace on
every run. `pr_commit_details.parquet` alone is 1.3 GB, so one three-language
re-run moved roughly 4 GB before doing any work.

Second, 94% of that 1.3 GB is the `patch` column, and 74% of the rows are files
in languages this study does not examine. Caching the raw table fills a laptop
disk for no benefit. This script keeps only rows whose filename has a
TypeScript, C# or Rust extension and only the columns the pipeline reads, then
stores them with zstd instead of snappy. The result is 160 MB rather than
1.3 GB, with no loss of information the pipeline can use.

Run once:  python3 scripts/cache_aidev.py
Re-run:    add --force to refresh a table.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "datasets" / "aidev_cache"
BASE = "hf://datasets/hao-li/AIDev"

SMALL_TABLES = ("repository", "pull_request", "pr_commits")

# pr_commit_details is the only table large enough to need special handling.
DETAIL_COLUMNS = ["pr_id", "filename", "patch", "additions", "deletions",
                  "changes"]
SOURCE_EXTENSIONS = (".ts", ".tsx", ".mts", ".cts", ".cs", ".rs")


def cache_small(name: str, force: bool) -> None:
    dest = CACHE / f"{name}.parquet"
    if dest.exists() and not force:
        print(f"[skip] {name:<20} already cached "
              f"({dest.stat().st_size / 1e6:.1f} MB)", flush=True)
        return
    print(f"[get ] {name} ...", flush=True)
    df = pd.read_parquet(f"{BASE}/{name}.parquet")
    df.to_parquet(dest, index=False, compression="zstd")
    print(f"[done] {name:<20} rows={len(df):,}  "
          f"{dest.stat().st_size / 1e6:.1f} MB", flush=True)


def cache_details(force: bool) -> None:
    """Stream, filter to the studied languages, and recompress."""
    dest = CACHE / "pr_commit_details.parquet"
    if dest.exists() and not force:
        print(f"[skip] pr_commit_details already cached "
              f"({dest.stat().st_size / 1e6:.1f} MB)", flush=True)
        return

    tmp = CACHE / "pr_commit_details.partial.parquet"
    print("[get ] pr_commit_details (streaming, filtered) ...", flush=True)
    src = pq.ParquetFile(f"{BASE}/pr_commit_details.parquet")

    writer = None
    seen = kept = 0
    started = time.time()
    try:
        for batch in src.iter_batches(batch_size=20_000,
                                      columns=DETAIL_COLUMNS):
            seen += batch.num_rows
            names = pc.utf8_lower(pc.fill_null(batch.column("filename"), ""))
            mask = None
            for ext in SOURCE_EXTENSIONS:
                hit = pc.ends_with(names, pattern=ext)
                mask = hit if mask is None else pc.or_(mask, hit)
            table = pa.Table.from_batches([batch]).filter(mask)
            if table.num_rows == 0:
                continue
            if writer is None:
                writer = pq.ParquetWriter(tmp, table.schema,
                                          compression="zstd",
                                          compression_level=9)
            writer.write_table(table)
            kept += table.num_rows
    finally:
        if writer is not None:
            writer.close()

    tmp.replace(dest)
    print(f"[done] pr_commit_details    scanned={seen:,} kept={kept:,} "
          f"({100 * kept / max(seen, 1):.1f}%)  "
          f"{dest.stat().st_size / 1e6:.1f} MB  "
          f"in {time.time() - started:.0f}s", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="refresh tables that are already cached")
    args = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    for name in SMALL_TABLES:
        cache_small(name, args.force)
    cache_details(args.force)
    total = sum(p.stat().st_size for p in CACHE.glob("*.parquet"))
    print(f"[ok  ] cache ready at {CACHE}  ({total / 1e6:.1f} MB total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

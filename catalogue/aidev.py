"""Load the cached AIDev tables and build the agent-side corpus.

Reads `datasets/aidev_cache/` written by `scripts/cache_aidev.py`, falling back
to HuggingFace when a table is missing. The cache exists because the raw
`pr_commit_details` table is 1.3 GB and every extractor used to re-download it.

The agent arm is emitted in the same canonical schema as the human arm, so both
flow through one Stage 1 and one Stage 2. `pr_key` is `<language>:<owner/repo>#
<number>`, matching `scripts/normalise_human_corpus.py`.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "datasets" / "aidev_cache"
HF_BASE = "hf://datasets/hao-li/AIDev"

# The five agents the paper studies.
AI_AGENTS = ("OpenAI_Codex", "Devin", "Copilot", "Cursor", "Claude_Code")

# How each language appears in AIDev's repository.language column.
LANGUAGE_TAG = {"TypeScript": "TypeScript", "C#": "C#", "Rust": "Rust"}

LANG_FILE_SUFFIX = {
    "TypeScript": (".ts", ".tsx", ".mts", ".cts"),
    "C#": (".cs",),
    "Rust": (".rs",),
}


def load_table(name: str) -> pd.DataFrame:
    local = CACHE / f"{name}.parquet"
    if local.exists():
        return pd.read_parquet(local)
    print(f"[warn] {name}.parquet not cached, streaming from HuggingFace. "
          f"Run scripts/cache_aidev.py to avoid this.")
    return pd.read_parquet(f"{HF_BASE}/{name}.parquet")


def repos_for(language: str) -> pd.DataFrame:
    repos = load_table("repository")
    tag = LANGUAGE_TAG[language]
    mask = repos["language"].fillna("").str.fullmatch(tag, case=False)
    return repos.loc[mask].copy()


def build_agent_corpus(language: str) -> pd.DataFrame:
    """One row per agent PR, in the canonical schema, with its patch text."""
    repos = repos_for(language)
    repo_name = dict(zip(repos["id"], repos.get(
        "full_name", repos.get("name", repos["id"]))))

    prs = load_table("pull_request")
    prs = prs[prs["repo_id"].isin(set(repos["id"]))].copy()
    prs = prs[prs["agent"].isin(AI_AGENTS)].copy()

    # Push the pr_id filter into the parquet read. Loading all 465k detail
    # rows with their patch column costs several GB of memory; only this
    # language's PRs are ever needed.
    pr_ids = prs["id"].tolist()
    local = CACHE / "pr_commit_details.parquet"
    if local.exists():
        details = pd.read_parquet(
            local, filters=[("pr_id", "in", pr_ids)])
    else:
        details = load_table("pr_commit_details")
        details = details[details["pr_id"].isin(set(pr_ids))].copy()

    suffixes = LANG_FILE_SUFFIX[language]
    keep = details["filename"].fillna("").str.lower().str.endswith(suffixes)
    details = details.loc[keep]

    # (filename, patch) pairs per PR: the counters take these directly rather
    # than re-parsing a concatenated blob, so no banner format can be missed.
    grouped = {
        pr_id: list(zip(g["filename"].tolist(), g["patch"].tolist()))
        for pr_id, g in details.groupby("pr_id", sort=False)
    }

    rows = []
    for rec in prs.to_dict("records"):
        repo = repo_name.get(rec["repo_id"], str(rec["repo_id"]))
        number = rec.get("number")
        files = grouped.get(rec["id"], [])
        rows.append({
            "pr_key": f"{language}:{repo}#{int(number)}"
                      if pd.notna(number) else f"{language}:{repo}#na",
            "language": language,
            "group": "AI",
            "agent": rec.get("agent"),
            "repo_full_name": repo,
            "repo_stars": 0,
            "number": int(number) if pd.notna(number) else 0,
            "html_url": rec.get("html_url") or "",
            "title": rec.get("title") or "",
            "body": rec.get("body") or "",
            "author": rec.get("agent") or "",
            "state": rec.get("state") or "",
            "created_at": str(rec.get("created_at") or ""),
            "closed_at": str(rec.get("closed_at") or ""),
            "merged_at": str(rec.get("merged_at") or ""),
            "additions": int(rec.get("additions") or 0),
            "deletions": int(rec.get("deletions") or 0),
            "changes": int(rec.get("changed_files") or 0),
            "lang_files_changed": len(files),
            "_files": files,
        })

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    before = len(frame)
    frame = frame.drop_duplicates(subset="pr_key", keep="first")
    if before != len(frame):
        print(f"[info] {language}: dropped {before - len(frame):,} duplicate "
              f"pr_key rows from the agent arm")
    return frame.reset_index(drop=True)

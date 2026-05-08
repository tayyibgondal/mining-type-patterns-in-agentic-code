"""
Probe AIDev-pop for Rust language coverage.

Reports:
- Total Rust repositories in AIDev-pop
- Total PRs in those Rust repositories
- Breakdown of those PRs by AI agent vs Human authorship
- Number of PRs that have associated commit/patch detail rows

We always work with AIDev-pop (`pull_request.parquet`); the full AIDev dataset
lacks PR patch details and is therefore unsuitable for this study.
"""

import pandas as pd

AI_AGENTS = ['OpenAI_Codex', 'Devin', 'Copilot', 'Cursor', 'Claude_Code']


def main():
    print("=" * 80)
    print("Rust coverage probe in AIDev-pop")
    print("=" * 80)

    print("\nLoading AIDev-pop tables from HuggingFace...")
    pr_df = pd.read_parquet('hf://datasets/hao-li/AIDev/pull_request.parquet')
    repo_df = pd.read_parquet('hf://datasets/hao-li/AIDev/repository.parquet')
    pr_commit_details_df = pd.read_parquet(
        'hf://datasets/hao-li/AIDev/pr_commit_details.parquet'
    )
    print(f"  Loaded: {len(pr_df):,} PRs | {len(repo_df):,} repos | "
          f"{len(pr_commit_details_df):,} commit detail rows")

    print("\nLanguage distribution (top 20 repo languages in AIDev-pop):")
    lang_counts = repo_df['language'].fillna('Unknown').value_counts().head(20)
    print(lang_counts.to_string())

    print("\n" + "=" * 80)
    print("Rust repositories")
    print("=" * 80)
    rust_repos = repo_df[
        repo_df['language'].fillna('').str.contains('Rust', case=False, regex=False)
    ]
    print(f"  Rust repos in AIDev-pop:        {len(rust_repos):,}")

    rust_repo_ids = set(rust_repos['id'].tolist())
    rust_prs = pr_df[pr_df['repo_id'].isin(rust_repo_ids)].copy()
    print(f"  Total PRs in Rust repos:        {len(rust_prs):,}")

    rust_prs['group'] = rust_prs['agent'].apply(
        lambda a: 'AI' if a in AI_AGENTS else 'Human'
    )
    print(f"\n  PRs by group:")
    print(rust_prs['group'].value_counts().to_string())

    print(f"\n  PRs by agent:")
    print(rust_prs['agent'].fillna('Unknown').value_counts().to_string())

    rust_pr_ids = set(rust_prs['id'].tolist())
    detail_rust = pr_commit_details_df[pr_commit_details_df['pr_id'].isin(rust_pr_ids)]
    prs_with_details = detail_rust['pr_id'].nunique()
    print(f"\n  Rust PRs with commit detail rows: {prs_with_details:,} "
          f"({100 * prs_with_details / max(1, len(rust_prs)):.1f}% of Rust PRs)")

    rs_files = detail_rust[
        detail_rust['filename'].fillna('').str.endswith('.rs')
    ]
    print(f"  PRs touching at least one .rs file: {rs_files['pr_id'].nunique():,}")

    print("\n" + "=" * 80)
    print("Probe complete. Proceed to extract_rust_type_prs.py.")
    print("=" * 80)


if __name__ == '__main__':
    main()

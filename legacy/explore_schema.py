import pandas as pd

print("Loading datasets...")

# Load key datasets
pr_df = pd.read_parquet('hf://datasets/hao-li/AIDev/pull_request.parquet')
repo_df = pd.read_parquet('hf://datasets/hao-li/AIDev/repository.parquet')
pr_commits_df = pd.read_parquet('hf://datasets/hao-li/AIDev/pr_commits.parquet')
pr_commit_details_df = pd.read_parquet('hf://datasets/hao-li/AIDev/pr_commit_details.parquet')

print("\n" + "="*80)
print("PR DataFrame Schema")
print("="*80)
print(f"Shape: {pr_df.shape}")
print(f"Columns: {pr_df.columns.tolist()}")
print("\nSample data:")
print(pr_df.head(2))

print("\n" + "="*80)
print("Repository DataFrame Schema")
print("="*80)
print(f"Shape: {repo_df.shape}")
print(f"Columns: {repo_df.columns.tolist()}")
print("\nSample data:")
print(repo_df.head(2))

print("\n" + "="*80)
print("PR Commits DataFrame Schema")
print("="*80)
print(f"Shape: {pr_commits_df.shape}")
print(f"Columns: {pr_commits_df.columns.tolist()}")
print("\nSample data:")
print(pr_commits_df.head(2))

print("\n" + "="*80)
print("PR Commit Details DataFrame Schema")
print("="*80)
print(f"Shape: {pr_commit_details_df.shape}")
print(f"Columns: {pr_commit_details_df.columns.tolist()}")
print("\nSample data:")
print(pr_commit_details_df.head(2))

print("\n" + "="*80)
print("Agent Distribution in PR DataFrame")
print("="*80)
print(pr_df['agent'].value_counts())

print("\n" + "="*80)
print("TypeScript Repositories (by language)")
print("="*80)
ts_repos = repo_df[repo_df['language'].str.contains('TypeScript', case=False, na=False)]
print(f"Number of TypeScript repos: {len(ts_repos)}")


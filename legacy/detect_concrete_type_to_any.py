"""
Extract TypeScript type-related PRs with any replacement detection.
"""

import pandas as pd
import re
from typing import List, Set, Dict, Any
import json
from datetime import datetime
import os
from pathlib import Path

class TypeScriptTypePRExtractorV3:
    """Extractor with any replacement detection"""
    
    TS_EXTENSIONS = {'.ts', '.tsx'}
    TYPE_KEYWORDS_SCORED = [
        (r'\btype\s+\w+\s*=', 12),
        (r'\binterface\s+\w+', 12),
        (r':\s*[A-Z][a-zA-Z]*\s*[;\)\}]', 10),
        (r'as\s+[A-Z][a-zA-Z]*', 8),
        (r'<[A-Z][a-zA-Z]*>', 7),
        (r'\btype\s+fix\b', 8),
        (r'\bfix.*type error\b', 9),
        (r'\bnoImplicitAny\b', 11),
        (r'\bstrictNullChecks\b', 11),
        (r'\badd.*\btype\b', 6),
        (r'\bimprove.*\btyping\b', 7),
        (r'\brefactor.*\btype\b', 6),
    ]
    
    PATCH_ADDITION_PATTERNS = [
        (r'^\+\s*.*:\s*[a-zA-Z_][\w]*\s*[;\)\}]', 15),
        (r'^\+\s*.*:\s*[A-Z][a-zA-Z]*\s*[;\)\}]', 18),
        (r'^\+\s*(interface|type)\s+\w+', 25),
        (r'^\+\s*.*\s+as\s+[A-Z][a-zA-Z]*', 12),
        (r'^\+\s*.*<[^<>]*[A-Z][a-zA-Z][^<>]*>', 10),
        (r'^\+\s*.*:\s*any\b', 18),
        (r'^\-\s*.*:\s*any\b', 20),
    ]
    
    FP_EXCLUDE_PATTERNS = [
        r'type\s*=\s*["\']',
        r'typeof\s+\w+',
        r'@type\s+{',
        r'console\.log.*type',
        r'button.*type',
        r'input.*type',
        r'\.d\.ts\b',
    ]
    
    ANY_REPLACEMENT_PATTERN = re.compile(
        r'^\-\s*.*:\s*([a-zA-Z_][\w\[\]<>]*)\s*[;\)\}]?\s*$\n'
        r'^\+\s*.*:\s*any\b',
        re.MULTILINE
    )
    
    MIN_TITLE_SCORE = 10
    MIN_PATCH_SCORE = 18
    MIN_TOTAL_SCORE = 28

    def __init__(self):
        self.pr_df = None
        self.repo_df = None
        self.pr_commits_df = None
        self.pr_commit_details_df = None
        self.typescript_type_prs = None
        
    def load_datasets(self):
        print("Loading datasets from HuggingFace...")
        self.pr_df = pd.read_parquet('hf://datasets/hao-li/AIDev/pull_request.parquet')
        self.repo_df = pd.read_parquet('hf://datasets/hao-li/AIDev/repository.parquet')
        self.pr_commits_df = pd.read_parquet('hf://datasets/hao-li/AIDev/pr_commits.parquet')
        self.pr_commit_details_df = pd.read_parquet('hf://datasets/hao-li/AIDev/pr_commit_details.parquet')
        print(f"Loaded: {len(self.pr_df):,} PRs, {len(self.repo_df):,} repos")

    def filter_typescript_repos(self) -> Set[int]:
        print("\nFiltering TypeScript repositories...")
        ts_repos = self.repo_df[
            self.repo_df['language'].str.contains('TypeScript', case=False, na=False)
        ]
        repo_ids = set(ts_repos['id'].tolist())
        print(f"   Found {len(repo_ids):,} TypeScript repos")
        return repo_ids

    def filter_ai_agent_prs(self, ts_repo_ids: Set[int]) -> pd.DataFrame:
        print("\nFiltering AI agent PRs in TypeScript repos...")
        ai_agents = ['OpenAI_Codex', 'Devin', 'Copilot', 'Cursor', 'Claude_Code']
        agent_prs = self.pr_df[
            (self.pr_df['agent'].isin(ai_agents)) &
            (self.pr_df['repo_id'].isin(ts_repo_ids))
        ].copy()
        print(f"   Found {len(agent_prs):,} AI PRs")
        return agent_prs

    def _has_fp(self, text: str) -> bool:
        if pd.isna(text): return False
        return any(re.search(p, text, re.IGNORECASE) for p in self.FP_EXCLUDE_PATTERNS)

    def _score_text(self, text: str) -> int:
        if pd.isna(text): return 0
        text_lower = text.lower()
        score = 0
        for pattern, weight in self.TYPE_KEYWORDS_SCORED:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += weight
        return score

    def _score_patch(self, patch: str) -> int:
        if pd.isna(patch): return 0
        score = 0
        for line in patch.splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                for pattern, weight in self.PATCH_ADDITION_PATTERNS:
                    if re.search(pattern, line):
                        score += weight
                        break
        return score

    def _is_valid_ts_file(self, filename: str) -> bool:
        if pd.isna(filename):
            return False
        path = Path(filename)
        return path.suffix.lower() in self.TS_EXTENSIONS and not path.name.endswith('.d.ts')

    def identify_type_related_prs(self, agent_prs: pd.DataFrame) -> pd.DataFrame:
        print("\nIdentifying type-related PRs with any detection...")
        print("   Applying FP filters...")
        agent_prs['has_fp'] = (
            agent_prs['title'].apply(self._has_fp) |
            agent_prs['body'].apply(self._has_fp)
        )
        fp_count = agent_prs['has_fp'].sum()
        agent_prs = agent_prs[~agent_prs['has_fp']].copy()
        print(f"   Removed {fp_count:,} FPs")
        print("   Scoring title & body...")
        agent_prs['title_score'] = agent_prs['title'].apply(self._score_text)
        agent_prs['body_score'] = agent_prs['body'].apply(self._score_text)
        agent_prs['text_score'] = agent_prs['title_score'] + agent_prs['body_score']
        print("   Scoring commit messages...")
        commit_scores = self.pr_commits_df.groupby('pr_id').apply(
            lambda g: max(self._score_text(msg) for msg in g['message']),
            include_groups=False
        ).to_dict()
        agent_prs['commit_score'] = agent_prs['id'].map(commit_scores).fillna(0).astype(int)
        print("   Analyzing patches + detecting any replacements...")
        ts_details = self.pr_commit_details_df[
            self.pr_commit_details_df['filename'].apply(self._is_valid_ts_file)
        ]

        def analyze_patch_group(group):
            max_score = 0
            any_add = 0
            any_rem = 0
            any_replacements = 0

            for patch in group['patch']:
                if pd.isna(patch):
                    continue
                patch_score = self._score_patch(patch)
                max_score = max(max_score, patch_score)
                any_add += len(re.findall(r'^\+\s*.*:\s*any\b', patch, re.MULTILINE))
                any_rem += len(re.findall(r'^\-\s*.*:\s*any\b', patch, re.MULTILINE))
                any_replacements += len(self.ANY_REPLACEMENT_PATTERN.findall(patch))

            return pd.Series({
                'patch_score': max_score,
                'any_additions': any_add,
                'any_removals': any_rem,
                'any_replacements': any_replacements
            })

        patch_stats = ts_details.groupby('pr_id').apply(analyze_patch_group, include_groups=False)
        agent_prs['patch_score'] = agent_prs['id'].map(patch_stats['patch_score'].to_dict()).fillna(0).astype(int)
        agent_prs['any_additions'] = agent_prs['id'].map(patch_stats['any_additions'].to_dict()).fillna(0).astype(int)
        agent_prs['any_removals'] = agent_prs['id'].map(patch_stats['any_removals'].to_dict()).fillna(0).astype(int)
        agent_prs['any_replacements'] = agent_prs['id'].map(patch_stats['any_replacements'].to_dict()).fillna(0).astype(int)
        
        ts_file_count = ts_details.groupby('pr_id').size().to_dict()
        agent_prs['ts_file_count'] = agent_prs['id'].map(ts_file_count).fillna(0).astype(int)
        agent_prs['has_ts_files'] = agent_prs['ts_file_count'] > 0
        
        agent_prs['total_score'] = (
            agent_prs['text_score'] +
            agent_prs['commit_score'] +
            agent_prs['patch_score'] +
            (agent_prs['ts_file_count'] * 2)
        )
        
        type_prs = agent_prs[
            agent_prs['has_ts_files'] &
            (
                (agent_prs['text_score'] >= self.MIN_TITLE_SCORE) |
                (agent_prs['patch_score'] >= self.MIN_PATCH_SCORE)
            ) &
            (agent_prs['total_score'] >= self.MIN_TOTAL_SCORE)
        ].copy()
        
        type_prs['detection_method'] = ''
        type_prs.loc[type_prs['text_score'] >= self.MIN_TITLE_SCORE, 'detection_method'] += 'text|'
        type_prs.loc[type_prs['patch_score'] >= self.MIN_PATCH_SCORE, 'detection_method'] += 'patch|'
        type_prs['detection_method'] = type_prs['detection_method'].str.rstrip('|')

        print(f"\n   Found {len(type_prs):,} type-related PRs")
        print(f"   any_additions: {type_prs['any_additions'].sum():,}")
        print(f"   any_removals: {type_prs['any_removals'].sum():,}")
        print(f"   any_replacements: {type_prs['any_replacements'].sum():,}")

        return type_prs

    def enrich_with_commit_stats(self, type_prs: pd.DataFrame) -> pd.DataFrame:
        print("\nEnriching with commit stats...")
        ts_details = self.pr_commit_details_df[
            self.pr_commit_details_df['filename'].apply(self._is_valid_ts_file)
        ]

        stats = ts_details.groupby('pr_id').agg(
            additions=('additions', 'sum'),
            deletions=('deletions', 'sum'),
            changes=('changes', 'sum'),
            ts_files_changed=('filename', 'nunique')
        )

        def collect_patches(group):
            patches = []
            for _, row in group.iterrows():
                if pd.notna(row['patch']) and row['patch'].strip():
                    header = f"=== {row['filename']} (+{row['additions']}/-{row['deletions']}) ==="
                    patches.append(f"{header}\n{row['patch']}")
            return "\n\n".join(patches) if patches else ""

        patch_text = ts_details.groupby('pr_id').apply(collect_patches, include_groups=False).rename('patch_text')

        enriched = type_prs.merge(stats, left_on='id', right_index=True, how='left') \
                          .merge(patch_text, left_on='id', right_index=True, how='left')

        for col in ['additions', 'deletions', 'changes', 'ts_files_changed']:
            enriched[col] = enriched[col].fillna(0).astype(int)
        enriched['patch_text'] = enriched['patch_text'].fillna('')

        return enriched

    def export_results(self, enriched_prs: pd.DataFrame, output_file: str):
        print(f"\nExporting to {output_file}...")
        export_cols = [
            'id', 'number', 'title', 'body', 'agent', 'state', 'created_at', 'merged_at',
            'repo_id', 'html_url', 'additions', 'deletions', 'changes', 'ts_files_changed',
            'any_additions', 'any_removals', 'any_replacements',
            'text_score', 'patch_score', 'total_score', 'detection_method', 'patch_text'
        ]
        enriched_prs[export_cols].to_csv(output_file, index=False)
        print(f"   Exported {len(enriched_prs):,} PRs")

        summary = {
            'extraction_date': datetime.now().isoformat(),
            'total_type_prs': len(enriched_prs),
            'by_agent': enriched_prs['agent'].value_counts().to_dict(),
            'any_additions_total': int(enriched_prs['any_additions'].sum()),
            'any_removals_total': int(enriched_prs['any_removals'].sum()),
            'any_replacements_total': int(enriched_prs['any_replacements'].sum()),
            'prs_with_any_change': int(((enriched_prs['any_additions'] + enriched_prs['any_removals']) > 0).sum()),
            'prs_with_any_replacement': int((enriched_prs['any_replacements'] > 0).sum()),
            'avg_score': float(enriched_prs['total_score'].mean()),
            'detection_methods': enriched_prs['detection_method'].value_counts().to_dict()
        }
        with open(output_file.replace('.csv', '_summary.json'), 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"   Summary saved to {output_file.replace('.csv', '_summary.json')}")

    def run_pipeline(self, output_file: str = 'ts_type_prs_with_any_replacement.csv'):
        print("="*80)
        print("TypeScript Type-Related PR Extraction (with any replacement detection)")
        print("="*80)

        self.load_datasets()
        ts_repo_ids = self.filter_typescript_repos()
        agent_prs = self.filter_ai_agent_prs(ts_repo_ids)
        type_prs = self.identify_type_related_prs(agent_prs)
        enriched = self.enrich_with_commit_stats(type_prs)
        self.export_results(enriched, output_file)
        self.typescript_type_prs = enriched

        print("\n" + "="*80)
        print("Pipeline completed!")
        print("="*80)
        return enriched


def main():
    extractor = TypeScriptTypePRExtractorV3()
    results = extractor.run_pipeline()
    print(f"\nFinal: {len(results):,} type-related PRs extracted.")
    return results


if __name__ == '__main__':
    main()
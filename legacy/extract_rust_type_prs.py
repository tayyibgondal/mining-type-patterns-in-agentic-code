"""
Rust Type Feature PR Extractor

Extracts and analyzes Rust type-related PRs from AIDev-pop, counting type
escape mechanisms (unsafe, .unwrap()/.expect(), `as` casts) and advanced type
features per PR. Mirrors the TypeScript and C# extractors but specialized for
Rust's type system.

Type escape hatches tracked for RQ1:
  - `unsafe` (primary)  — direct equivalent of TS `any` and C# `dynamic`
  - `.unwrap()` / `.expect()` — bypasses Result/Option type-safe error handling
  - `as` casts — silent numeric coercion, bypasses checked conversions
"""

import pandas as pd
import re
import json
from datetime import datetime
from pathlib import Path


class RustTypePRExtractor:
    """
    Extractor for detecting and counting Rust type features in PR patch
    additions, comparing AI vs. Human problem-solving styles.
    """

    # AI Agents filter (same set as TS / C# scripts)
    AI_AGENTS = ['OpenAI_Codex', 'Devin', 'Copilot', 'Cursor', 'Claude_Code']

    # File extensions
    RS_EXTENSIONS = {'.rs'}

    # Rust Type Feature Patterns (advanced features for RQ2)
    TYPE_FEATURE_PATTERNS = [
        # 1. Generics: <T>, <T, U>, Vec<T>, Option<T>, Result<T, E>, etc.
        (r'<[^<>]+>', 'generics_count'),

        # 2. Lifetime annotations: 'a, 'static, &'a, <'a>
        (r"'[a-zA-Z_]\w*\b", 'lifetime_count'),

        # 3. Trait bounds in generics: T: Trait, T: Trait + Send
        (r'<[^<>]*\b\w+\s*:\s*[A-Z]\w*[^<>]*>', 'trait_bound_count'),

        # 4. where clauses: where T: Trait
        (r'\bwhere\s+\w+\s*:', 'where_clause_count'),

        # 5. impl Trait (return position / arg position)
        (r'\bimpl\s+[A-Z]\w*', 'impl_trait_count'),

        # 6. dyn Trait (dynamic dispatch / trait objects)
        (r'\bdyn\s+[A-Z]\w*', 'dyn_trait_count'),

        # 7. Box<dyn Trait>
        (r'\bBox\s*<\s*dyn\s+', 'box_dyn_count'),

        # 8. Type aliases: type Foo = Bar<T>
        (r'\btype\s+[A-Z]\w*\s*(<[^>]*>)?\s*=', 'type_alias_count'),

        # 9. Associated types: type Item = ...; or Self::Item
        (r'\btype\s+[A-Z]\w*\s*=', 'associated_type_count'),

        # 10. PhantomData markers
        (r'\bPhantomData\s*<', 'phantom_data_count'),

        # 11. #[derive(...)] attributes
        (r'#\[derive\([^\)]+\)\]', 'derive_count'),

        # 12. match expressions
        (r'\bmatch\s+\w', 'match_count'),

        # 13. if let / while let
        (r'\b(?:if|while)\s+let\b', 'if_let_count'),

        # 14. Enum definitions: enum Foo { ... }
        (r'\benum\s+[A-Z]\w*', 'enum_count'),

        # 15. Struct definitions: struct Foo
        (r'\bstruct\s+[A-Z]\w*', 'struct_count'),

        # 16. trait definitions: trait Foo
        (r'\btrait\s+[A-Z]\w*', 'trait_count'),

        # 17. impl blocks
        (r'\bimpl(?:\s*<[^>]+>)?\s+[A-Z]\w*', 'impl_block_count'),

        # 18. Send / Sync trait bounds
        (r'\b(?:Send|Sync)\b', 'send_sync_count'),

        # 19. Arc / Mutex / RwLock smart-pointer wrappers
        (r'\b(?:Arc|Rc|Mutex|RwLock|RefCell|Cell)\s*<', 'smart_pointer_count'),

        # 20. Option<T> / Result<T, E>
        (r'\b(?:Option|Result)\s*<', 'option_result_count'),

        # 21. unsafe impl
        (r'\bunsafe\s+impl\b', 'unsafe_impl_count'),

        # 22. mem::transmute (extremely dangerous escape hatch)
        (r'\bmem::transmute\b|\btransmute\s*::\s*<', 'transmute_count'),

        # 23. std::any::Any usage
        (r'\b(?:std::)?any::Any\b|\bdyn\s+Any\b', 'any_trait_count'),
    ]

    # Type-related keyword patterns (used for FILTER ONLY, no scoring)
    TYPE_KEYWORDS_PATTERNS = [
        r'\btrait\s+\w+',
        r'\bstruct\s+\w+',
        r'\benum\s+\w+',
        r'\btype\s+\w+\s*=',
        r'\bimpl\s+',
        r'\bunsafe\b',
        r'\bdyn\s+\w+',
        r'\bBox\s*<',
        r'<[^<>]+>',
        r"'[a-zA-Z_]\w*\b",
        r'\bwhere\s+',
        r'\bderive\s*\(',
        r'\bOption\s*<',
        r'\bResult\s*<',
        r'\bArc\s*<',
        r'\bMutex\s*<',
        r'\bPhantomData\b',
        r'\bSend\b|\bSync\b',
        r'\bborrow checker\b',
        r'\blifetime\b',
        r'\btype\s+annotation\b',
        r'\btype\s+safety\b',
        r'\btype\s+system\b',
        r'\bfix.*type error\b',
    ]

    PATCH_ADDITION_PATTERNS = [
        r'.*:\s*[a-zA-Z_][\w:]*(?:<[^<>]*>)?',
        r'.*\bfn\s+\w+',
        r'.*\bstruct\s+\w+',
        r'.*\benum\s+\w+',
        r'.*\btrait\s+\w+',
        r'.*\bimpl\s+',
        r'.*\bunsafe\b',
        r'.*\bdyn\s+',
        r'.*\bBox\s*<',
        r'.*<[^<>]+>',
        r".*'[a-z_]\w*",
    ]

    FP_EXCLUDE_PATTERNS = [
        # SAFETY documentation comments are not unsafe code being added
        r'^\s*//\s*SAFETY\s*:',
        # Doc-comment "type" mentions
        r'^\s*//[!/].*\btype\b',
        # MIME / content-type mentions
        r'content[_-]?type',
        r'mime[_-]?type',
    ]

    # Patterns for the unsafe escape-hatch metric (the headline RQ1 metric).
    # Match `unsafe { ... }`, `unsafe fn`, `unsafe impl`, `unsafe trait`.
    UNSAFE_TOKEN_PATTERN = r'\bunsafe\b'

    # Secondary escape-hatch metrics
    UNWRAP_TOKEN_PATTERN = r'\.\s*(?:unwrap|expect)\s*\('
    AS_CAST_TOKEN_PATTERN = r'\bas\s+(?:[iu](?:8|16|32|64|128|size)|f32|f64|bool|char|usize|isize|\*(?:const|mut)|&)'

    def __init__(self):
        self.pr_df = None
        self.repo_df = None
        self.pr_commits_df = None
        self.pr_commit_details_df = None
        self.rust_type_prs = None

        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all regular expressions."""
        self.compiled_type_keywords = [
            re.compile(p, re.IGNORECASE) for p in self.TYPE_KEYWORDS_PATTERNS
        ]
        self.compiled_patch_add_patterns = [
            re.compile(p) for p in self.PATCH_ADDITION_PATTERNS
        ]
        self.compiled_fp_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in self.FP_EXCLUDE_PATTERNS
        ]

        self.compiled_type_feature_patterns = [
            (re.compile(pattern), col_name)
            for pattern, col_name in self.TYPE_FEATURE_PATTERNS
        ]
        self.TYPE_FEATURE_COLS = [col for _, col in self.TYPE_FEATURE_PATTERNS]

        # Escape-hatch counters: count additions on `+` lines and removals on `-` lines.
        self.compiled_unsafe = re.compile(self.UNSAFE_TOKEN_PATTERN)
        self.compiled_unwrap = re.compile(self.UNWRAP_TOKEN_PATTERN)
        self.compiled_as_cast = re.compile(self.AS_CAST_TOKEN_PATTERN)

    def load_datasets(self):
        """Load AIDev-pop tables from HuggingFace."""
        print("Loading datasets from HuggingFace (AIDev-pop)...")
        self.pr_df = pd.read_parquet('hf://datasets/hao-li/AIDev/pull_request.parquet')
        self.repo_df = pd.read_parquet('hf://datasets/hao-li/AIDev/repository.parquet')
        self.pr_commits_df = pd.read_parquet('hf://datasets/hao-li/AIDev/pr_commits.parquet')
        self.pr_commit_details_df = pd.read_parquet(
            'hf://datasets/hao-li/AIDev/pr_commit_details.parquet'
        )
        print(f"Loaded: {len(self.pr_df):,} PRs, {len(self.repo_df):,} repos")

    def filter_prs_by_agent_status(self) -> pd.DataFrame:
        """Filter all PRs in Rust repos and tag each as 'AI' or 'Human'."""
        if self.pr_df.empty or self.repo_df.empty:
            return pd.DataFrame()

        print("\nFiltering Rust PRs and classifying by agent status...")

        rs_repos = self.repo_df[
            self.repo_df['language'].fillna('').str.contains('Rust', case=False, regex=False)
        ]
        rs_repo_ids = set(rs_repos['id'].tolist())

        all_rs_prs = self.pr_df[self.pr_df['repo_id'].isin(rs_repo_ids)].copy()
        all_rs_prs['group'] = all_rs_prs['agent'].apply(
            lambda x: 'AI' if x in self.AI_AGENTS else 'Human'
        )

        ai_n = (all_rs_prs['group'] == 'AI').sum()
        hu_n = (all_rs_prs['group'] == 'Human').sum()
        print(f"   Found {len(all_rs_prs):,} total PRs in Rust repos "
              f"({ai_n:,} AI, {hu_n:,} Human)")
        return all_rs_prs

    def _has_fp(self, text: str) -> bool:
        if pd.isna(text):
            return False
        return any(p.search(text) for p in self.compiled_fp_patterns)

    def _has_type_keywords(self, text: str) -> bool:
        if pd.isna(text):
            return False
        return any(p.search(text) for p in self.compiled_type_keywords)

    def _has_patch_type_patterns(self, patch: str) -> bool:
        if pd.isna(patch):
            return False
        for line in patch.splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                line_content = line[1:].strip()
                for pattern in self.compiled_patch_add_patterns:
                    if pattern.search(line_content):
                        return True
        return False

    def _is_valid_rs_file(self, filename: str) -> bool:
        if pd.isna(filename):
            return False
        path = Path(filename)
        if path.suffix.lower() not in self.RS_EXTENSIONS:
            return False
        # Exclude generated / build files
        if path.name.endswith('.pb.rs') or path.name == 'build.rs':
            return False
        return True

    def identify_type_related_prs(self, all_rs_prs: pd.DataFrame) -> pd.DataFrame:
        """Identify type-related PRs and count features."""
        if all_rs_prs.empty:
            print("No PRs to analyze.")
            return pd.DataFrame()

        print("\nIdentifying type-related Rust PRs with feature detection...")

        # 1. False Positive removal on title/body
        print("   Applying FP filters...")
        all_rs_prs['has_fp'] = (
            all_rs_prs['title'].apply(self._has_fp) |
            all_rs_prs['body'].apply(self._has_fp)
        )
        filtered_prs = all_rs_prs[~all_rs_prs['has_fp']].copy()

        # 2. Type-keyword presence in title/body
        print("   Checking for type-related keywords...")
        filtered_prs['has_type_keywords'] = (
            filtered_prs['title'].apply(self._has_type_keywords) |
            filtered_prs['body'].apply(self._has_type_keywords)
        )

        # 3. Patch analysis
        print("   Analyzing patches + counting all features...")
        rs_details = self.pr_commit_details_df[
            self.pr_commit_details_df['filename'].apply(self._is_valid_rs_file)
        ].copy()

        def analyze_patch_group(group):
            feature_counts = {col: 0 for col in self.TYPE_FEATURE_COLS}
            unsafe_add = unsafe_rem = 0
            unwrap_add = unwrap_rem = 0
            as_cast_add = as_cast_rem = 0

            full_patch_text = "\n".join(group['patch'].dropna().tolist())
            if not full_patch_text:
                return pd.Series({
                    **feature_counts,
                    'unsafe_additions': 0, 'unsafe_removals': 0,
                    'unwrap_additions': 0, 'unwrap_removals': 0,
                    'as_cast_additions': 0, 'as_cast_removals': 0,
                })

            added_lines = []
            removed_lines = []
            for line in full_patch_text.splitlines():
                if line.startswith('+') and not line.startswith('+++'):
                    added_lines.append(line[1:])
                elif line.startswith('-') and not line.startswith('---'):
                    removed_lines.append(line[1:])

            added_text = "\n".join(added_lines)
            removed_text = "\n".join(removed_lines)

            if added_text.strip():
                for pattern, col_name in self.compiled_type_feature_patterns:
                    feature_counts[col_name] = len(pattern.findall(added_text))
                unsafe_add = len(self.compiled_unsafe.findall(added_text))
                unwrap_add = len(self.compiled_unwrap.findall(added_text))
                as_cast_add = len(self.compiled_as_cast.findall(added_text))

            if removed_text.strip():
                unsafe_rem = len(self.compiled_unsafe.findall(removed_text))
                unwrap_rem = len(self.compiled_unwrap.findall(removed_text))
                as_cast_rem = len(self.compiled_as_cast.findall(removed_text))

            return pd.Series({
                **feature_counts,
                'unsafe_additions': unsafe_add,
                'unsafe_removals': unsafe_rem,
                'unwrap_additions': unwrap_add,
                'unwrap_removals': unwrap_rem,
                'as_cast_additions': as_cast_add,
                'as_cast_removals': as_cast_rem,
            })

        print(f"   Processing {rs_details['pr_id'].nunique():,} PRs with patches...")
        patch_stats = rs_details.groupby('pr_id').apply(
            analyze_patch_group, include_groups=False
        )

        filtered_prs = filtered_prs.merge(
            patch_stats, left_on='id', right_index=True, how='left'
        )

        all_count_cols = self.TYPE_FEATURE_COLS + [
            'unsafe_additions', 'unsafe_removals',
            'unwrap_additions', 'unwrap_removals',
            'as_cast_additions', 'as_cast_removals',
        ]
        for col in all_count_cols:
            if col in filtered_prs.columns:
                filtered_prs[col] = filtered_prs[col].fillna(0).astype(int)
            else:
                filtered_prs[col] = 0

        # 4. Rust file count per PR
        rs_file_count = rs_details.groupby('pr_id').size().to_dict()
        filtered_prs['rs_file_count'] = filtered_prs['id'].map(rs_file_count).fillna(0).astype(int)
        filtered_prs['has_rs_files'] = filtered_prs['rs_file_count'] > 0

        filtered_prs['total_feature_count'] = filtered_prs[self.TYPE_FEATURE_COLS].sum(axis=1)

        # Patch-type-pattern flag
        print("   Checking for type patterns in patches...")
        patch_type_flags = rs_details.groupby('pr_id').apply(
            lambda g: any(self._has_patch_type_patterns(p) for p in g['patch'] if pd.notna(p)),
            include_groups=False
        ).to_dict()
        filtered_prs['has_patch_type_patterns'] = (
            filtered_prs['id'].map(patch_type_flags).fillna(False)
        )

        # 5. Final filter: must touch a .rs file AND show some type-related signal
        type_prs = filtered_prs[
            filtered_prs['has_rs_files'] &
            ~filtered_prs['has_fp'] &
            (
                (filtered_prs['total_feature_count'] > 0) |
                (filtered_prs['unsafe_additions'] > 0) |
                (filtered_prs['unsafe_removals'] > 0) |
                filtered_prs['has_type_keywords'] |
                filtered_prs['has_patch_type_patterns']
            )
        ].copy()

        type_prs['detection_method'] = ''
        type_prs.loc[type_prs['total_feature_count'] > 0, 'detection_method'] += 'features|'
        type_prs.loc[
            (type_prs['unsafe_additions'] > 0) | (type_prs['unsafe_removals'] > 0),
            'detection_method'
        ] += 'unsafe|'
        type_prs.loc[type_prs['has_type_keywords'], 'detection_method'] += 'type_keywords|'
        type_prs.loc[type_prs['has_patch_type_patterns'], 'detection_method'] += 'patch_patterns|'
        type_prs['detection_method'] = type_prs['detection_method'].str.rstrip('|')

        print(f"\n   Found {len(type_prs):,} high-confidence Rust type-related PRs.")
        return type_prs

    def enrich_with_commit_stats(self, type_prs: pd.DataFrame) -> pd.DataFrame:
        if type_prs.empty:
            return pd.DataFrame()

        print("\nEnriching with commit stats and collecting full patches...")
        rs_details = self.pr_commit_details_df[
            self.pr_commit_details_df['pr_id'].isin(type_prs['id']) &
            self.pr_commit_details_df['filename'].apply(self._is_valid_rs_file)
        ]

        stats = rs_details.groupby('pr_id').agg(
            additions=('additions', 'sum'),
            deletions=('deletions', 'sum'),
            changes=('changes', 'sum'),
            rs_files_changed=('filename', 'nunique')
        )

        def collect_patches(group):
            patches = []
            for _, row in group.iterrows():
                if pd.notna(row['patch']) and row['patch'].strip():
                    header = (
                        f"=== {row['filename']} "
                        f"(+{row['additions']}/-{row['deletions']}) ==="
                    )
                    patches.append(f"{header}\n{row['patch']}")
            return "\n\n".join(patches) if patches else ""

        patch_text = (
            rs_details.groupby('pr_id')
            .apply(collect_patches, include_groups=False)
            .rename('patch_text')
        )

        enriched = (
            type_prs
            .merge(stats, left_on='id', right_index=True, how='left')
            .merge(patch_text, left_on='id', right_index=True, how='left')
        )

        for col in ['additions', 'deletions', 'changes', 'rs_files_changed']:
            enriched[col] = enriched[col].fillna(0).astype(int)
        enriched['patch_text'] = enriched['patch_text'].fillna('')

        return enriched

    def export_results(self, enriched_prs: pd.DataFrame, output_file: str):
        if enriched_prs.empty:
            print("No results to export.")
            return

        print(f"\nExporting to {output_file}...")
        export_cols = [
            'id', 'number', 'title', 'body', 'agent', 'group', 'state',
            'created_at', 'merged_at', 'repo_id', 'html_url',
            'additions', 'deletions', 'changes', 'rs_files_changed',
            'unsafe_additions', 'unsafe_removals',
            'unwrap_additions', 'unwrap_removals',
            'as_cast_additions', 'as_cast_removals',
        ] + self.TYPE_FEATURE_COLS + [
            'total_feature_count', 'detection_method', 'patch_text'
        ]

        export_cols = [c for c in export_cols if c in enriched_prs.columns]
        enriched_prs[export_cols].to_csv(output_file, index=False)
        print(f"   Exported {len(enriched_prs):,} PRs")

        # Per-agent breakdown
        agent_feature_stats = {}
        for agent in enriched_prs['agent'].dropna().unique():
            agent_data = enriched_prs[enriched_prs['agent'] == agent]
            agent_feature_stats[str(agent)] = {
                'pr_count': len(agent_data),
                'total_features': int(agent_data['total_feature_count'].sum()),
                'avg_features_per_pr': round(
                    float(agent_data['total_feature_count'].mean()), 4
                ),
                'unsafe_additions': int(agent_data['unsafe_additions'].sum()),
                'unsafe_removals': int(agent_data['unsafe_removals'].sum()),
                'unwrap_additions': int(agent_data['unwrap_additions'].sum()),
                'unwrap_removals': int(agent_data['unwrap_removals'].sum()),
                'as_cast_additions': int(agent_data['as_cast_additions'].sum()),
                'as_cast_removals': int(agent_data['as_cast_removals'].sum()),
                'feature_counts': {
                    col: int(agent_data[col].sum()) for col in self.TYPE_FEATURE_COLS
                }
            }

        group_feature_stats = {}
        for group in enriched_prs['group'].dropna().unique():
            group_data = enriched_prs[enriched_prs['group'] == group]
            group_feature_stats[str(group)] = {
                'pr_count': len(group_data),
                'total_features': int(group_data['total_feature_count'].sum()),
                'avg_features_per_pr': round(
                    float(group_data['total_feature_count'].mean()), 4
                ),
                'unsafe_additions': int(group_data['unsafe_additions'].sum()),
                'unsafe_removals': int(group_data['unsafe_removals'].sum()),
                'unwrap_additions': int(group_data['unwrap_additions'].sum()),
                'unwrap_removals': int(group_data['unwrap_removals'].sum()),
                'as_cast_additions': int(group_data['as_cast_additions'].sum()),
                'as_cast_removals': int(group_data['as_cast_removals'].sum()),
                'feature_counts': {
                    col: int(group_data[col].sum()) for col in self.TYPE_FEATURE_COLS
                }
            }

        summary = {
            'extraction_date': datetime.now().isoformat(),
            'total_type_prs': len(enriched_prs),
            'by_group': enriched_prs['group'].value_counts().to_dict(),
            'by_agent': enriched_prs['agent'].value_counts().to_dict(),
            'unsafe_additions_total': int(enriched_prs['unsafe_additions'].sum()),
            'unsafe_removals_total': int(enriched_prs['unsafe_removals'].sum()),
            'unwrap_additions_total': int(enriched_prs['unwrap_additions'].sum()),
            'unwrap_removals_total': int(enriched_prs['unwrap_removals'].sum()),
            'as_cast_additions_total': int(enriched_prs['as_cast_additions'].sum()),
            'as_cast_removals_total': int(enriched_prs['as_cast_removals'].sum()),
            'total_features': int(enriched_prs['total_feature_count'].sum()),
            'feature_totals': {
                col: int(enriched_prs[col].sum()) for col in self.TYPE_FEATURE_COLS
            },
            'agent_feature_stats': agent_feature_stats,
            'group_feature_stats': group_feature_stats,
        }

        summary_file = output_file.replace('.csv', '_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"   Summary saved to {summary_file}")

    def run_pipeline(self, output_file: str = 'rust_type_prs_all_groups.csv'):
        print("=" * 80)
        print("Rust Type-Related PR Extraction (AIDev-pop)")
        print("=" * 80)

        self.load_datasets()
        all_rs_prs = self.filter_prs_by_agent_status()
        type_prs = self.identify_type_related_prs(all_rs_prs)
        enriched = self.enrich_with_commit_stats(type_prs)
        self.export_results(enriched, output_file)
        self.rust_type_prs = enriched

        print("\n" + "=" * 80)
        print("Pipeline completed!")
        print("=" * 80)
        return enriched


def main():
    extractor = RustTypePRExtractor()
    return extractor.run_pipeline(output_file='datasets/rust_data/rust_type_prs_all_groups.csv')


if __name__ == '__main__':
    main()

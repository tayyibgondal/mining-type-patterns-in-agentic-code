import pandas as pd
import re
from typing import List, Set, Dict, Any
import json
from datetime import datetime
from pathlib import Path

class TypeScriptTypePRExtractorV4:
    """
    V4: Extractor focused on detecting and counting advanced TypeScript type features
    and type safety patterns (generics, conditional types, satisfies, etc.)
    in PR patch additions, comparing AI vs. Human problem-solving styles.
    """
    
    # AI Agents filter
    AI_AGENTS = ['OpenAI_Codex', 'Devin', 'Copilot', 'Cursor', 'Claude_Code']
    
    # File extensions
    TS_EXTENSIONS = {'.ts', '.tsx'}
    
    # --- V4 NEW PATTERNS for Advanced Type Feature Counting (Refined for Rigor) ---
    ADVANCED_TYPE_PATTERNS_REFINED = [
        # 1. Generics: Type parameters in declarations (avoid JSX false positives)
        # Target: class A<T> { ... } | type B<T> = ... | const func: <T>(a: T) => void
        (r'(interface|type|class|function|declare\s+function|const\s+\w+\s*:\s*)\s*\w+\s*<[^<>]+>', 'generics_count'),

        # 2. Conditional Types: T extends U ? X : Y
        # Target: T extends string ? A : B
        (r'\bextends\b\s*[^?]*\?\s*[^:]*:\s*', 'conditional_type_count'),

        # 3. Infer keyword inside conditional types
        # Target: infer T
        (r'\binfer\s+\w+\b', 'infer_count'),

        # 4. Mapped Types: {[K in keyof T]: ...}
        # Target: [K in keyof T]: ... | [readonly K in keyof T]
        (r'\[\s*(readonly\s+)?([A-Za-z_]\w*)\s+in\s+keyof\s+\w+\s*(\s*\?)?\s*\]', 'mapped_type_count'),

        # 5. Key Remapping in mapped types (as ...)
        # Target: [K in keyof T as \`\${K}Changed\`]: ...
        (r'\[[^\]]+in[^\]]+\bas\s+[A-Za-z_]\w+[^\]]*\]', 'key_remap_count'),

        # 6. Template Literal Types: `${string}` / `${infer T}`
        # Target: `prefix${T}suffix`
        (r'`[^`]*\$\{[^}]+}[^`]*`', 'template_literal_type_count'),

        # 7. Satisfies operator (TS 4.9+)
        # Target: obj satisfies Type
        (r'\s+satisfies\s+', 'satisfies_count'),

        # 8. As const: literal narrowing
        # Target: as const
        (r'\bas\s+const\b', 'as_const_count'),

        # 9. Non-null Assertion Operator: foo!.bar, foo![0], foo!(), etc.
        # Target: !. | ![ | !(
        (r'!\s*([\.\[(])', 'non_null_assertion_count'),

        # 10. Type Guard ('is'): return type predicate
        # Target: is string
        (r':\s*\(?\s*\w+\s+is\s+\w+', 'type_guard_is_count'),

        # 11. Type-Level Operators (keyof, typeof, in)
        (r'\bkeyof\b', 'keyof_count'),
        (r'\btypeof\b', 'typeof_count'),
        # 'in' operator distinguished by being inside square brackets for types
        (r'\[[^\]]*\bin\b[^\]]*\]', 'in_operator_count'),

        # 12. Intersection & Union Types (type-level operators)
        # Ensures it's surrounded by type-like characters (not just logic)
        (r'[A-Za-z0-9)\]]\s*&\s*[A-Za-z0-9(\[]', 'intersection_type_count'),
        (r'[A-Za-z0-9)\]]\s*\|\s*[A-Za-z0-9(\[]', 'union_type_count'),

        # 13. Indexed Access Types: T[K] using keyof for specific indexing
        # Target: T[keyof K]
        (r'\w+\s*\[\s*keyof\s*\w+\s*\]', 'indexed_access_count'),

        # 14. Utility Types: Pick, Record, ReturnType, etc. (expanded list)
        (r'\b(Partial|Required|Readonly|Pick|Omit|Record|ReturnType|InstanceType|Parameters|ConstructorParameters|Awaited|ThisType|Exclude|Extract|NonNullable)\s*<', 'utility_type_usage_count'),

        # 15. Recursive / Self-referential type alias (Highly unreliable heuristic)
        # Target: type A = A | B
        # Note: This is a simplified pattern - full recursive detection is complex
        (r'type\s+(\w+)\s*=\s*.*\b\1\b', 'recursive_type_count'),

        # 16. Const Assertions in Objects or Arrays (via suffix)
        # Target: {a: 1} as const
        (r'(as\s+const)|(\{[^}]+\}\s+as\s+const)', 'const_assertion_count'),

        # 17. Discriminated Union Hints (literal field value for 'kind', 'type', or 'tag')
        # Target: kind: 'literal'
        (r'\b(kind|type|tag)\s*:\s*(\'[A-Za-z_0-9]+\'|"[A-Za-z_0-9]+")', 'discriminated_union_count'),

        # 18. Unique symbol declarations
        # Target: unique symbol
        (r'\bunique\s+symbol\b', 'unique_symbol_count'),

        # 19. Readonly modifier inside object properties or tuple types
        # Target: readonly prop: string | readonly [string, number]
        (r'\b(readonly\s+([A-Za-z_]\w+|\[))|(\{[^}]*readonly\s+\w+:[^}]*\})', 'readonly_modifier_count'),

        # 20. Optional modifiers on properties
        # Target: prop?: string
        (r'\w+\s*\?:', 'optional_property_count'),
    ]
    
    # Type-related patterns (for filtering only, no scoring)
    TYPE_KEYWORDS_PATTERNS = [
        r'\btype\s+\w+\s*=',
        r'\binterface\s+\w+',
        r':\s*[A-Z][a-zA-Z]*\s*[;\)\}]',
        r'as\s+[A-Z][a-zA-Z]*',
        r'<[A-Z][a-zA-Z]*>',
        r'\btype\s+fix\b',
        r'\bfix.*type error\b',
        r'\bnoImplicitAny\b',
        r'\bstrictNullChecks\b',
        r'\badd.*\btype\b',
        r'\bimprove.*\btyping\b',
        r'\brefactor.*\btype\b',
    ]
    PATCH_ADDITION_PATTERNS = [
        r'.*:\s*[a-zA-Z_][\w]*\s*[;\)\}]',
        r'.*:\s*[A-Z][a-zA-Z]*\s*[;\)\}]',
        r'(interface|type)\s+\w+',
        r'.*\s+as\s+[A-Z][a-zA-Z]*',
        r'.*<[^<>]*[A-Z][a-zA-Z][^<>]*>',
        r'.*:\s*any\b',
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

    ANY_REPLACEMENT_RAW_PATTERN = r'^\-\s*.*:\s*([a-zA-Z_][\w\[\]<>]*)\s*[;\)\}]?\s*$\n^\+\s*.*:\s*any\b'

    def __init__(self):
        self.pr_df = None
        self.human_pr_df = None
        self.repo_df = None
        self.pr_commits_df = None
        self.pr_commit_details_df = None
        self.typescript_type_prs = None
        
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all regular expressions."""
        self.compiled_type_keywords = [
            re.compile(p, re.IGNORECASE) for p in self.TYPE_KEYWORDS_PATTERNS
        ]
        self.compiled_patch_add_patterns = [
            re.compile(p) for p in self.PATCH_ADDITION_PATTERNS
        ]
        self.compiled_fp_patterns = [re.compile(p, re.IGNORECASE) for p in self.FP_EXCLUDE_PATTERNS]
        
        # Specific patterns for 'any' counting (findall)
        self.compiled_any_add = re.compile(r'^\+\s*.*:\s*any\b', re.MULTILINE)
        self.compiled_any_rem = re.compile(r'^\-\s*.*:\s*any\b', re.MULTILINE)
        self.compiled_any_replacement = re.compile(self.ANY_REPLACEMENT_RAW_PATTERN, re.MULTILINE)

        # V4 NEW: Compiled Advanced Type Patterns
        self.compiled_advanced_patterns = [
            (re.compile(p), col_name) for p, col_name in self.ADVANCED_TYPE_PATTERNS_REFINED
        ]
        self.ADVANCED_COUNT_COLS = [col_name for _, col_name in self.ADVANCED_TYPE_PATTERNS_REFINED]

    def load_datasets(self):
        print("Loading datasets from HuggingFace...")
        try:
             self.pr_df = pd.read_parquet('hf://datasets/hao-li/AIDev/pull_request.parquet')
             self.repo_df = pd.read_parquet('hf://datasets/hao-li/AIDev/repository.parquet')
             self.pr_commits_df = pd.read_parquet('hf://datasets/hao-li/AIDev/pr_commits.parquet')
             self.pr_commit_details_df = pd.read_parquet('hf://datasets/hao-li/AIDev/pr_commit_details.parquet')
             
             print(f"Loaded: {len(self.pr_df):,} PRs, {len(self.repo_df):,} repos")
        except Exception as e:
             print(f"Error loading data from HuggingFace/Parquet: {e}")
             raise

    def filter_prs_by_agent_status(self) -> pd.DataFrame:
        """Filters all PRs in TS repos and marks them as 'AI' or 'Human'."""
        if self.pr_df.empty or self.repo_df.empty:
            return pd.DataFrame()
            
        print("\nFiltering TypeScript PRs and classifying by agent status...")
        
        ts_repos = self.repo_df[
            self.repo_df['language'].str.contains('TypeScript', case=False, na=False)
        ]
        ts_repo_ids = set(ts_repos['id'].tolist())

        # Filter all PRs in TS repos
        all_ts_prs = self.pr_df[
            self.pr_df['repo_id'].isin(ts_repo_ids)
        ].copy()
        
        # Classify PRs
        all_ts_prs['group'] = all_ts_prs['agent'].apply(
            lambda x: 'AI' if x in self.AI_AGENTS else 'Human'
        )

        print(f"   Found {len(all_ts_prs):,} total PRs in TS repos ({len(all_ts_prs[all_ts_prs['group'] == 'AI']):,} AI, {len(all_ts_prs[all_ts_prs['group'] == 'Human']):,} Human)")
        return all_ts_prs

    def _has_fp(self, text: str) -> bool:
        if pd.isna(text): return False
        return any(p.search(text) for p in self.compiled_fp_patterns)

    def _has_type_keywords(self, text: str) -> bool:
        """Check if text contains type-related keywords (no scoring)."""
        if pd.isna(text): return False
        return any(p.search(text) for p in self.compiled_type_keywords)

    def _has_patch_type_patterns(self, patch: str) -> bool:
        """Check if patch contains type-related additions (no scoring)."""
        if pd.isna(patch): return False
        for line in patch.splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                line_content = line[1:].strip()
                for pattern in self.compiled_patch_add_patterns:
                    if pattern.search(line_content):
                        return True
        return False

    def _is_valid_ts_file(self, filename: str) -> bool:
        if pd.isna(filename): return False
        path = Path(filename)
        # Exclude declaration files (.d.ts) as they often only contain type definitions
        return path.suffix.lower() in self.TS_EXTENSIONS and not path.name.endswith('.d.ts')

    def identify_type_related_prs(self, all_ts_prs: pd.DataFrame) -> pd.DataFrame:
        if all_ts_prs.empty:
            print("No PRs to analyze.")
            return pd.DataFrame()

        print("\nIdentifying type-related PRs with advanced feature detection...")

        # 1. False Positive removal
        print("   Applying FP filters...")
        all_ts_prs['has_fp'] = (
            all_ts_prs['title'].apply(self._has_fp) |
            all_ts_prs['body'].apply(self._has_fp)
        )
        filtered_prs = all_ts_prs[~all_ts_prs['has_fp']].copy()

        # 2. Check for type-related keywords (no scoring)
        print("   Checking for type-related keywords...")
        filtered_prs['has_type_keywords'] = (
            filtered_prs['title'].apply(self._has_type_keywords) |
            filtered_prs['body'].apply(self._has_type_keywords)
        )
        
        # Add dummy scores for compatibility (we don't use them for filtering)
        filtered_prs['text_score'] = 0
        filtered_prs['commit_score'] = 0

        # 3. Patch analysis with type feature counting
        print("   Analyzing patches + counting all features...")
        ts_details = self.pr_commit_details_df[
            self.pr_commit_details_df['filename'].apply(self._is_valid_ts_file)
        ].copy()

        def analyze_patch_group(group):
            any_add = 0
            any_rem = 0
            any_replacements = 0
            
            advanced_counts = {col: 0 for col in self.ADVANCED_COUNT_COLS}

            # Concatenate all valid TS patches for this PR
            full_patch_text = "\n".join(group['patch'].dropna().tolist())
            
            if full_patch_text:
                # any counts (on the combined text)
                any_add = len(self.compiled_any_add.findall(full_patch_text))
                any_rem = len(self.compiled_any_rem.findall(full_patch_text))
                any_replacements = len(self.compiled_any_replacement.findall(full_patch_text))

                # Count advanced features on ADDED lines only
                added_lines = "\n".join([line for line in full_patch_text.splitlines() if line.startswith('+') and not line.startswith('+++')])
                for pattern, col_name in self.compiled_advanced_patterns:
                    advanced_counts[col_name] += len(pattern.findall(added_lines))
            
            results = {
                'patch_score': 0,  # Dummy value, not used
                'any_additions': any_add,
                'any_removals': any_rem,
                'any_replacements': any_replacements,
                **advanced_counts
            }
            return pd.Series(results)

        patch_stats = ts_details.groupby('pr_id').apply(analyze_patch_group, include_groups=False)
        
        # Merge all patch stats back into the PR dataframe
        filtered_prs = filtered_prs.merge(patch_stats, left_on='id', right_index=True, how='left')

        # Fill NaNs for all count columns
        count_cols = ['patch_score', 'any_additions', 'any_removals', 'any_replacements'] + self.ADVANCED_COUNT_COLS
        for col in count_cols:
            filtered_prs[col] = filtered_prs[col].fillna(0).astype(int)

        # 4. TS file count and Total score
        ts_file_count = ts_details.groupby('pr_id').size().to_dict()
        filtered_prs['ts_file_count'] = filtered_prs['id'].map(ts_file_count).fillna(0).astype(int)
        filtered_prs['has_ts_files'] = filtered_prs['ts_file_count'] > 0

        # Set dummy total_score (not used for filtering)
        filtered_prs['total_score'] = 0

        # Check if patches contain type patterns
        print("   Checking for type patterns in patches...")
        patch_type_flags = ts_details.groupby('pr_id').apply(
            lambda group: any(self._has_patch_type_patterns(patch) for patch in group['patch'] if pd.notna(patch)),
            include_groups=False
        ).to_dict()
        filtered_prs['has_patch_type_patterns'] = filtered_prs['id'].map(patch_type_flags).fillna(False)
        
        # 5. Final filtering: require TS files AND (any-related changes OR type keywords/patterns) AND NOT has_fp
        type_prs = filtered_prs[
            filtered_prs['has_ts_files'] &
            ~filtered_prs['has_fp'] &
            (
                (filtered_prs['any_additions'] > 0) |
                (filtered_prs['any_removals'] > 0) |
                (filtered_prs['any_replacements'] > 0) 
            ) &
            (filtered_prs['has_type_keywords'] | filtered_prs['has_patch_type_patterns'])
        ].copy()

        # Add detection method based on what triggered inclusion
        type_prs['detection_method'] = ''
        type_prs.loc[type_prs['any_additions'] > 0, 'detection_method'] += 'any_add|'
        type_prs.loc[type_prs['any_removals'] > 0, 'detection_method'] += 'any_rem|'
        type_prs.loc[type_prs['any_replacements'] > 0, 'detection_method'] += 'any_rep|'
        type_prs.loc[type_prs['has_type_keywords'], 'detection_method'] += 'type_keywords|'
        type_prs.loc[type_prs['has_patch_type_patterns'], 'detection_method'] += 'patch_patterns|'
        type_prs['detection_method'] = type_prs['detection_method'].str.rstrip('|')

        print(f"\n   Found {len(type_prs):,} high-confidence type-related PRs.")
        return type_prs

    def enrich_with_commit_stats(self, type_prs: pd.DataFrame) -> pd.DataFrame:
        if type_prs.empty:
            return pd.DataFrame()
        
        print("\nEnriching with commit stats and collecting full patches...")
        ts_details = self.pr_commit_details_df[
            self.pr_commit_details_df['pr_id'].isin(type_prs['id']) &
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
        if enriched_prs.empty:
            print("No results to export.")
            return

        print(f"\nExporting to {output_file}...")
        export_cols = [
            'id', 'number', 'title', 'body', 'agent', 'group', 'state', 'created_at', 'merged_at',
            'repo_id', 'html_url', 'additions', 'deletions', 'changes', 'ts_files_changed',
            'any_additions', 'any_removals', 'any_replacements',
        ] + self.ADVANCED_COUNT_COLS + [
            'text_score', 'patch_score', 'total_score', 'detection_method', 'patch_text'
        ]
        
        export_cols = [col for col in export_cols if col in enriched_prs.columns]
            
        enriched_prs[export_cols].to_csv(output_file, index=False)
        print(f"   Exported {len(enriched_prs):,} PRs")

        # Calculate agent-specific feature density (per PR average)
        agent_feature_density = {}
        for agent in enriched_prs['agent'].unique():
            agent_data = enriched_prs[enriched_prs['agent'] == agent]
            agent_feature_density[agent] = {}
            for col in self.ADVANCED_COUNT_COLS:
                total = float(agent_data[col].sum())
                count = len(agent_data)
                agent_feature_density[agent][col] = round(total / count if count > 0 else 0, 4)
        
        # Calculate group-specific feature density
        group_feature_density = {}
        for group in enriched_prs['group'].unique():
            group_data = enriched_prs[enriched_prs['group'] == group]
            group_feature_density[group] = {}
            for col in self.ADVANCED_COUNT_COLS:
                total = float(group_data[col].sum())
                count = len(group_data)
                group_feature_density[group][col] = round(total / count if count > 0 else 0, 4)
        
        # Calculate agent-specific any statistics
        agent_any_stats = {}
        for agent in enriched_prs['agent'].unique():
            agent_data = enriched_prs[enriched_prs['agent'] == agent]
            agent_any_stats[agent] = {
                'any_additions': int(agent_data['any_additions'].sum()),
                'any_removals': int(agent_data['any_removals'].sum()),
                'any_replacements': int(agent_data['any_replacements'].sum()),
            }
        
        # Calculate group-specific any statistics
        group_any_stats = {}
        for group in enriched_prs['group'].unique():
            group_data = enriched_prs[enriched_prs['group'] == group]
            group_any_stats[group] = {
                'any_additions': int(group_data['any_additions'].sum()),
                'any_removals': int(group_data['any_removals'].sum()),
                'any_replacements': int(group_data['any_replacements'].sum()),
            }
        
        summary = {
            'extraction_date': datetime.now().isoformat(),
            'total_type_prs': len(enriched_prs),
            'by_group': enriched_prs['group'].value_counts().to_dict(),
            'by_agent': enriched_prs['agent'].value_counts().to_dict(),
            'any_additions_total': int(enriched_prs['any_additions'].sum()),
            'any_removals_total': int(enriched_prs['any_removals'].sum()),
            'any_replacements_total': int(enriched_prs['any_replacements'].sum()),
            'any_replacements_pr': int((enriched_prs['any_replacements'] > 0).sum()),
            'agent_any_stats': agent_any_stats,
            'group_any_stats': group_any_stats,
            'advanced_feature_totals': {col: int(enriched_prs[col].sum()) for col in self.ADVANCED_COUNT_COLS},
            'agent_feature_density': agent_feature_density,
            'group_feature_density': group_feature_density,
        }
        with open(output_file.replace('.csv', '_summary.json'), 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"   Summary saved to {output_file.replace('.csv', '_summary.json')}")

    def run_pipeline(self, output_file: str = 'ts_type_prs_all_groups_final.csv'):
        print("="*80)
        print("TypeScript Type-Related PR Extraction (V4 - Advanced Feature Analysis)")
        print("="*80)

        self.load_datasets()
        all_ts_prs = self.filter_prs_by_agent_status() 
        type_prs = self.identify_type_related_prs(all_ts_prs)
        enriched = self.enrich_with_commit_stats(type_prs)
        self.export_results(enriched, output_file)
        self.typescript_type_prs = enriched

        print("\n" + "="*80)
        print("Pipeline completed!")
        print("="*80)
        return enriched


def main():
    extractor = TypeScriptTypePRExtractorV4()
    results = extractor.run_pipeline()
    return results


if __name__ == '__main__':
    main()

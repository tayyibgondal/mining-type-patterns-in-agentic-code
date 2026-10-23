import pandas as pd
import re
from typing import List, Set, Dict, Any
import json
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

class HumanTypePRExtractor:
    """Extracts type-related PRs from human PR dataset."""
    
    TS_EXTENSIONS = {'.ts', '.tsx'}
    
    ADVANCED_TYPE_PATTERNS = [
        (r'(interface|type|class|function)\s+\w*\s*<[^<>]+>', 'generics_count'),
        (r'\bextends\b[^?]+\?.+:.+', 'conditional_type_count'),
        (r'\s+satisfies\s+', 'satisfies_count'),
        (r'\bas\s+const\b', 'as_const_count'),
        (r'!\s*([\.\[(])', 'non_null_assertion_count'),
        (r':\s*\(?\s*\w+\s+is\s+\w+', 'type_guard_is_count'),
        (r'\bkeyof\s+typeof\b', 'keyof_typeof_count'),
    ]
    
    TYPE_KEYWORDS_SCORED = [
        (r'\btype\s+\w+\s*=', 12), (r'\binterface\s+\w+', 12),
        (r':\s*[A-Z][a-zA-Z]*\s*[;\)\}]', 10), (r'as\s+[A-Z][a-zA-Z]*', 8),
        (r'<[A-Z][a-zA-Z]*>', 7), (r'\btype\s+fix\b', 8), (r'\bfix.*type error\b', 9),
        (r'\bnoImplicitAny\b', 11), (r'\bstrictNullChecks\b', 11),
        (r'\badd.*\btype\b', 6), (r'\bimprove.*\btyping\b', 7), (r'\brefactor.*\btype\b', 6),
    ]
    
    PATCH_ADDITION_PATTERNS = [
        (r'.*:\s*[a-zA-Z_][\w]*\s*[;\)\}]', 15), (r'.*:\s*[A-Z][a-zA-Z]*\s*[;\)\}]', 18),
        (r'(interface|type)\s+\w+', 25), (r'.*\s+as\s+[A-Z][a-zA-Z]*', 12),
        (r'.*<[^<>]*[A-Z][a-zA-Z][^<>]*>', 10), (r'.*:\s*any\b', 18),
    ]
    
    FP_EXCLUDE_PATTERNS = [
        r'type\s*=\s*["\']', r'typeof\s+\w+', r'@type\s+{', r'console\.log.*type',
        r'button.*type', r'input.*type', r'\.d\.ts\b',
    ]
    
    ANY_REPLACEMENT_RAW_PATTERN = r'^\-\s*.*:\s*([a-zA-Z_][\w\[\]<>]*)\s*[;\)\}]?\s*$\n^\+\s*.*:\s*any\b'
    
    MIN_TITLE_SCORE, MIN_PATCH_SCORE, MIN_TOTAL_SCORE = 10, 18, 28

    def __init__(self):
        self.human_prs = None
        self._compile_patterns()

    def _compile_patterns(self):
        self.compiled_type_keywords = [
            (re.compile(p, re.IGNORECASE), w) for p, w in self.TYPE_KEYWORDS_SCORED
        ]
        self.compiled_patch_add_patterns = [
            (re.compile(p), w) for p, w in self.PATCH_ADDITION_PATTERNS
        ]
        self.compiled_fp_patterns = [re.compile(p, re.IGNORECASE) for p in self.FP_EXCLUDE_PATTERNS]
        
        self.compiled_any_add = re.compile(r'^\+\s*.*:\s*any\b', re.MULTILINE)
        self.compiled_any_rem = re.compile(r'^\-\s*.*:\s*any\b', re.MULTILINE)
        self.compiled_any_replacement = re.compile(self.ANY_REPLACEMENT_RAW_PATTERN, re.MULTILINE)
        
        self.compiled_advanced_patterns = [
            (re.compile(p), col_name) for p, col_name in self.ADVANCED_TYPE_PATTERNS
        ]
        self.ADVANCED_COUNT_COLS = [col_name for _, col_name in self.ADVANCED_TYPE_PATTERNS]

    def load_human_prs(self, input_file: str):
        """Load human PR data from CSV."""
        print(f"Loading human PR data from {input_file}...")
        try:
            print("   Counting rows...")
            with open(input_file, 'r') as f:
                total_rows = sum(1 for _ in f) - 1
            
            print(f"   Reading {total_rows:,} rows...")
            chunksize = 50000
            chunks = []
            
            with tqdm(total=total_rows, desc="Loading CSV", unit=" rows") as pbar:
                for chunk in pd.read_csv(input_file, chunksize=chunksize, low_memory=False):
                    chunks.append(chunk)
                    pbar.update(len(chunk))
            
            self.human_prs = pd.concat(chunks, ignore_index=True)
            print(f"✓ Loaded {len(self.human_prs):,} human PRs")
            print(f"Available columns: {list(self.human_prs.columns)}")
            
            return self.human_prs
        except Exception as e:
            print(f"Error loading data: {e}")
            raise

    def _has_fp(self, text: str) -> bool:
        if pd.isna(text):
            return False
        return any(p.search(text) for p in self.compiled_fp_patterns)

    def _score_text(self, text: str) -> int:
        if pd.isna(text):
            return 0
        score = 0
        for pattern, weight in self.compiled_type_keywords:
            if pattern.search(text):
                score += weight
        return score

    def _score_patch(self, patch: str) -> int:
        if pd.isna(patch):
            return 0
        score = 0
        for line in patch.splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                line_content = line[1:].strip()
                for pattern, weight in self.compiled_patch_add_patterns:
                    if pattern.search(line_content):
                        score += weight
                        break
        return score

    def _is_valid_ts_file(self, patch_text: str) -> bool:
        if pd.isna(patch_text) or not patch_text.strip():
            return False
        
        for line in patch_text.split('\n'):
            if line.startswith('===') and line.endswith('==='):
                filename = line.split('===')[1].strip().split('(')[0].strip()
                path = Path(filename)
                if path.suffix.lower() in self.TS_EXTENSIONS and not path.name.endswith('.d.ts'):
                    return True
        
        for line in patch_text.split('\n')[:50]:
            if line.startswith('diff --git') or line.startswith('---') or line.startswith('+++'):
                if any(ext in line for ext in ['.ts', '.tsx']):
                    if '.d.ts' not in line:
                        return True
        
        return False

    def _extract_ts_file_count(self, patch_text: str) -> int:
        if pd.isna(patch_text) or not patch_text.strip():
            return 0
        
        ts_files = set()
        for line in patch_text.split('\n'):
            if line.startswith('===') and line.endswith('==='):
                filename = line.split('===')[1].strip().split('(')[0].strip()
                path = Path(filename)
                if path.suffix.lower() in self.TS_EXTENSIONS and not path.name.endswith('.d.ts'):
                    ts_files.add(filename)
        
        return len(ts_files)

    def _analyze_patch(self, patch_text: str) -> Dict[str, int]:
        empty_result = {
            'patch_score': 0,
            'any_additions': 0,
            'any_removals': 0,
            'any_replacements': 0,
            **{col: 0 for col in self.ADVANCED_COUNT_COLS}
        }
        
        if pd.isna(patch_text) or not patch_text.strip():
            return empty_result
        
        patch_score = self._score_patch(patch_text)
        any_add = len(self.compiled_any_add.findall(patch_text))
        any_rem = len(self.compiled_any_rem.findall(patch_text))
        any_replacements = len(self.compiled_any_replacement.findall(patch_text))
        
        added_lines = "\n".join([
            line for line in patch_text.splitlines() 
            if line.startswith('+') and not line.startswith('+++')
        ])
        
        advanced_counts = {}
        for pattern, col_name in self.compiled_advanced_patterns:
            advanced_counts[col_name] = len(pattern.findall(added_lines))
        
        return {
            'patch_score': patch_score,
            'any_additions': any_add,
            'any_removals': any_rem,
            'any_replacements': any_replacements,
            **advanced_counts
        }

    def _extract_additions_deletions(self, patch_text: str) -> Dict[str, int]:
        if pd.isna(patch_text) or not patch_text.strip():
            return {'additions': 0, 'deletions': 0, 'changes': 0}
        
        additions = 0
        deletions = 0
        
        for line in patch_text.split('\n'):
            if line.startswith('===') and line.endswith('==='):
                import re
                match = re.search(r'\(\+(\d+)/-(\d+)\)', line)
                if match:
                    additions += int(match.group(1))
                    deletions += int(match.group(2))
        
        if additions == 0 and deletions == 0:
            for line in patch_text.split('\n'):
                if line.startswith('+') and not line.startswith('+++'):
                    additions += 1
                elif line.startswith('-') and not line.startswith('---'):
                    deletions += 1
        
        changes = additions + deletions
        return {'additions': additions, 'deletions': deletions, 'changes': changes}

    def identify_type_related_prs(self, prs_df: pd.DataFrame) -> pd.DataFrame:
        if prs_df.empty:
            print("No PRs to analyze.")
            return pd.DataFrame()

        print("\nIdentifying type-related PRs with advanced feature detection...")
        
        col_mapping = {}
        if 'pr_title' in prs_df.columns:
            col_mapping['title'] = 'pr_title'
        if 'pr_description' in prs_df.columns:
            col_mapping['body'] = 'pr_description'
        if 'pr_state' in prs_df.columns:
            col_mapping['state'] = 'pr_state'
        if 'pr_created_at' in prs_df.columns:
            col_mapping['created_at'] = 'pr_created_at'
        if 'pr_merged_at' in prs_df.columns:
            col_mapping['merged_at'] = 'pr_merged_at'
        
        working_df = prs_df.copy()
        for std_name, original_name in col_mapping.items():
            if original_name in working_df.columns and std_name not in working_df.columns:
                working_df[std_name] = working_df[original_name]
        
        for col in ['title', 'body']:
            if col not in working_df.columns:
                working_df[col] = ''
        
        print("   Step 1: Filtering for TypeScript PRs (fast pre-filter)...")
        tqdm.pandas(desc="Detecting TS files")
        working_df['has_ts_files'] = working_df['patch_text'].progress_apply(self._is_valid_ts_file)
        tqdm.pandas(desc="Counting TS files")
        working_df['ts_files_changed'] = working_df['patch_text'].progress_apply(self._extract_ts_file_count)
        
        ts_prs = working_df[working_df['has_ts_files']].copy()
        print(f"   ✓ Found {len(ts_prs):,} PRs with TypeScript files (filtered from {len(working_df):,})")
        
        if ts_prs.empty:
            print("   No TypeScript PRs found.")
            return pd.DataFrame()
        
        print("   Step 2: Applying FP filters on TS PRs...")
        tqdm.pandas(desc="FP Filter (Title)")
        has_fp_title = ts_prs['title'].progress_apply(self._has_fp)
        tqdm.pandas(desc="FP Filter (Body)")
        has_fp_body = ts_prs['body'].progress_apply(self._has_fp)
        ts_prs['has_fp'] = has_fp_title | has_fp_body
        
        filtered_prs = ts_prs[~ts_prs['has_fp']].copy()
        print(f"   ✓ After FP filtering: {len(filtered_prs):,} PRs")
        
        print("   Step 3: Scoring PR titles and bodies...")
        tqdm.pandas(desc="Scoring Titles")
        title_scores = filtered_prs['title'].progress_apply(self._score_text)
        tqdm.pandas(desc="Scoring Bodies")
        body_scores = filtered_prs['body'].progress_apply(self._score_text)
        filtered_prs['text_score'] = title_scores + body_scores
        print(f"   ✓ Text scoring completed")
        
        print("   Step 4: Analyzing patches for type features...")
        tqdm.pandas(desc="Analyzing patches")
        patch_analysis = filtered_prs['patch_text'].progress_apply(self._analyze_patch)
        patch_df = pd.DataFrame(patch_analysis.tolist(), index=filtered_prs.index)
        
        for col in patch_df.columns:
            filtered_prs[col] = patch_df[col]
        
        tqdm.pandas(desc="Extracting add/del")
        add_del = filtered_prs['patch_text'].progress_apply(self._extract_additions_deletions)
        add_del_df = pd.DataFrame(add_del.tolist(), index=filtered_prs.index)
        for col in add_del_df.columns:
            filtered_prs[col] = add_del_df[col]
        
        filtered_prs['total_score'] = (
            filtered_prs['text_score'] +
            filtered_prs['patch_score'] +
            (filtered_prs['ts_files_changed'] * 2)
        )
        
        print(f"   ✓ Scores calculated for {len(filtered_prs):,} PRs")
        print("   Step 5: Applying final score thresholds...")
        
        type_prs = filtered_prs[
            (
                (filtered_prs['text_score'] >= self.MIN_TITLE_SCORE) |
                (filtered_prs['patch_score'] >= self.MIN_PATCH_SCORE)
            ) &
            (filtered_prs['total_score'] >= self.MIN_TOTAL_SCORE)
        ].copy()
        
        print("   Step 6: Adding metadata...")
        type_prs['detection_method'] = ''
        type_prs.loc[type_prs['text_score'] >= self.MIN_TITLE_SCORE, 'detection_method'] += 'text|'
        type_prs.loc[type_prs['patch_score'] >= self.MIN_PATCH_SCORE, 'detection_method'] += 'patch|'
        type_prs['detection_method'] = type_prs['detection_method'].str.rstrip('|')
        
        type_prs['group'] = 'Human'
        
        if 'agent' not in type_prs.columns:
            type_prs['agent'] = 'Human'

        print(f"\n{'='*60}")
        print(f"FILTERING SUMMARY:")
        print(f"{'='*60}")
        print(f"  Total PRs loaded:              {len(prs_df):,}")
        print(f"  ↓ With TypeScript files:       {len(ts_prs):,}")
        print(f"  ↓ After FP filtering:          {len(filtered_prs):,}")
        print(f"  ↓ Meeting score thresholds:    {len(type_prs):,}")
        print(f"{'='*60}")
        print(f"✓ Final result: {len(type_prs):,} high-confidence type-related PRs")
        print(f"{'='*60}\n")
        return type_prs

    def export_results(self, type_prs: pd.DataFrame, output_file: str):
        if type_prs.empty:
            print("No results to export.")
            return

        print(f"\n{'='*60}")
        print(f"Exporting results to {output_file}...")
        print(f"{'='*60}")
        
        export_cols = [
            'id', 'number', 'title', 'body', 'agent', 'group', 'state', 
            'created_at', 'merged_at', 'repo_id', 'html_url', 
            'additions', 'deletions', 'changes', 'ts_files_changed',
            'any_additions', 'any_removals', 'any_replacements',
        ] + self.ADVANCED_COUNT_COLS + [
            'text_score', 'patch_score', 'total_score', 'detection_method', 'patch_text'
        ]
        
        for col in export_cols:
            if col not in type_prs.columns:
                if col == 'repo_id':
                    if 'repo_url' in type_prs.columns:
                        type_prs['repo_id'] = type_prs['repo_url'].apply(
                            lambda x: x.split('/')[-1] if pd.notna(x) else ''
                        )
                    else:
                        type_prs[col] = ''
                elif col in ['agent', 'group']:
                    type_prs[col] = 'Human'
                else:
                    type_prs[col] = 0 if col.endswith('_count') or col in ['additions', 'deletions', 'changes'] else ''
        
        export_cols = [col for col in export_cols if col in type_prs.columns]
        
        print(f"Writing {len(type_prs):,} PRs to CSV...")
        type_prs[export_cols].to_csv(output_file, index=False)
        print(f"   ✓ CSV export complete: {output_file}")
        print("Generating summary statistics...")
        summary = {
            'extraction_date': datetime.now().isoformat(),
            'total_type_prs': len(type_prs),
            'by_group': type_prs['group'].value_counts().to_dict(),
            'by_agent': type_prs['agent'].value_counts().to_dict() if 'agent' in type_prs.columns else {},
            'any_additions_total': int(type_prs['any_additions'].sum()),
            'any_removals_total': int(type_prs['any_removals'].sum()),
            'any_replacements_total': int(type_prs['any_replacements'].sum()),
            'any_replacements_pr': int((type_prs['any_replacements'] > 0).sum()),
            'advanced_feature_totals': {col: int(type_prs[col].sum()) for col in self.ADVANCED_COUNT_COLS},
            'group_feature_density': {
                'Human': {
                    col: round(float(type_prs[col].sum()) / len(type_prs), 4) if len(type_prs) > 0 else 0
                    for col in self.ADVANCED_COUNT_COLS
                }
            }
        }
        
        summary_file = output_file.replace('.csv', '_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"   ✓ Summary saved to {summary_file}")
        
        print(f"\n{'='*60}")
        print(f"Export completed successfully!")
        print(f"{'='*60}")

    def run_pipeline(self, input_file: str, output_file: str = 'human_type_prs_baseline.csv'):
        print("="*80)
        print("Human TypeScript Type-Related PR Extraction (Baseline)")
        print("="*80)
        
        self.load_human_prs(input_file)
        type_prs = self.identify_type_related_prs(self.human_prs)
        self.export_results(type_prs, output_file)

        print("\n" + "="*80)
        print("Pipeline completed!")
        print("="*80)
        return type_prs


def main():
    extractor = HumanTypePRExtractor()
    results = extractor.run_pipeline(
        input_file='human_pr_detailed_info.csv',
        output_file='human_type_prs_baseline.csv'
    )
    return results


if __name__ == '__main__':
    main()


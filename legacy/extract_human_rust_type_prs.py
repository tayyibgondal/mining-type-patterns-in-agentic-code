"""
Human Rust PR feature extractor.

Reads the CSV produced by `scrape_rust_prs_from_github.py` (or any CSV in the
same shape: each row has `patch_text`, `title`, `body`, etc.), keeps PRs that
touch at least one `.rs` file, and annotates each row with type-feature counts
and Rust-specific escape-hatch counts so the downstream LLM classifier can
finalize the type-related label.

Mirrors `extract_human_csharp_type_prs.py` in structure.
"""

import pandas as pd
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict
from tqdm import tqdm


class HumanRustTypePRExtractor:
    """Extract ALL Rust PRs from the human PR dataset (LLM filters later)."""

    RS_EXTENSIONS = {'.rs'}

    # Same advanced-feature pattern set as `extract_rust_type_prs.py` so AI vs
    # Human counts are directly comparable downstream.
    ADVANCED_TYPE_PATTERNS = [
        (r'<[^<>]+>', 'generics_count'),
        (r"'[a-zA-Z_]\w*\b", 'lifetime_count'),
        (r'<[^<>]*\b\w+\s*:\s*[A-Z]\w*[^<>]*>', 'trait_bound_count'),
        (r'\bwhere\s+\w+\s*:', 'where_clause_count'),
        (r'\bimpl\s+[A-Z]\w*', 'impl_trait_count'),
        (r'\bdyn\s+[A-Z]\w*', 'dyn_trait_count'),
        (r'\bBox\s*<\s*dyn\s+', 'box_dyn_count'),
        (r'\btype\s+[A-Z]\w*\s*(<[^>]*>)?\s*=', 'type_alias_count'),
        (r'\btype\s+[A-Z]\w*\s*=', 'associated_type_count'),
        (r'\bPhantomData\s*<', 'phantom_data_count'),
        (r'#\[derive\([^\)]+\)\]', 'derive_count'),
        (r'\bmatch\s+\w', 'match_count'),
        (r'\b(?:if|while)\s+let\b', 'if_let_count'),
        (r'\benum\s+[A-Z]\w*', 'enum_count'),
        (r'\bstruct\s+[A-Z]\w*', 'struct_count'),
        (r'\btrait\s+[A-Z]\w*', 'trait_count'),
        (r'\bimpl(?:\s*<[^>]+>)?\s+[A-Z]\w*', 'impl_block_count'),
        (r'\b(?:Send|Sync)\b', 'send_sync_count'),
        (r'\b(?:Arc|Rc|Mutex|RwLock|RefCell|Cell)\s*<', 'smart_pointer_count'),
        (r'\b(?:Option|Result)\s*<', 'option_result_count'),
        (r'\bunsafe\s+impl\b', 'unsafe_impl_count'),
        (r'\bmem::transmute\b|\btransmute\s*::\s*<', 'transmute_count'),
        (r'\b(?:std::)?any::Any\b|\bdyn\s+Any\b', 'any_trait_count'),
    ]

    UNSAFE_TOKEN_PATTERN = r'\bunsafe\b'
    UNWRAP_TOKEN_PATTERN = r'\.\s*(?:unwrap|expect)\s*\('
    AS_CAST_TOKEN_PATTERN = (
        r'\bas\s+(?:[iu](?:8|16|32|64|128|size)|f32|f64|bool|char|usize|isize|'
        r'\*(?:const|mut)|&)'
    )

    def __init__(self):
        self.human_prs = None
        self._compile_patterns()

    def _compile_patterns(self):
        self.compiled_advanced_patterns = [
            (re.compile(p), col_name) for p, col_name in self.ADVANCED_TYPE_PATTERNS
        ]
        self.ADVANCED_COUNT_COLS = [col for _, col in self.ADVANCED_TYPE_PATTERNS]
        self.compiled_unsafe = re.compile(self.UNSAFE_TOKEN_PATTERN)
        self.compiled_unwrap = re.compile(self.UNWRAP_TOKEN_PATTERN)
        self.compiled_as_cast = re.compile(self.AS_CAST_TOKEN_PATTERN)

    def load_human_prs(self, input_file: str):
        print(f"Loading human PR data from {input_file}...")
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
        print(f"Loaded {len(self.human_prs):,} human PRs")
        print(f"Available columns: {list(self.human_prs.columns)}")
        return self.human_prs

    def _is_valid_rs_file(self, patch_text: str) -> bool:
        if pd.isna(patch_text) or not patch_text.strip():
            return False

        # Custom collected-patch header format used elsewhere in this repo
        for line in patch_text.split('\n'):
            if line.startswith('===') and line.endswith('==='):
                filename = line.split('===')[1].strip().split('(')[0].strip()
                path = Path(filename)
                if path.suffix.lower() in self.RS_EXTENSIONS:
                    if path.name.endswith('.pb.rs') or path.name == 'build.rs':
                        continue
                    return True

        # Standard git diff format (from GitHub `.patch` URL)
        for line in patch_text.split('\n')[:200]:
            if line.startswith('diff --git') or line.startswith('---') or line.startswith('+++'):
                if '.rs' in line and '.pb.rs' not in line and 'build.rs' not in line:
                    return True

        return False

    def _extract_rs_file_count(self, patch_text: str) -> int:
        if pd.isna(patch_text) or not patch_text.strip():
            return 0

        rs_files = set()

        for line in patch_text.split('\n'):
            if line.startswith('===') and line.endswith('==='):
                filename = line.split('===')[1].strip().split('(')[0].strip()
                path = Path(filename)
                if path.suffix.lower() in self.RS_EXTENSIONS:
                    if not (path.name.endswith('.pb.rs') or path.name == 'build.rs'):
                        rs_files.add(filename)

        if not rs_files:
            # Fallback: parse diff --git lines
            for line in patch_text.split('\n'):
                if line.startswith('diff --git'):
                    parts = line.split()
                    if len(parts) >= 4:
                        filename = parts[3].lstrip('b/')
                        if filename.endswith('.rs') and not filename.endswith('.pb.rs') \
                                and Path(filename).name != 'build.rs':
                            rs_files.add(filename)

        return len(rs_files)

    def _analyze_patch(self, patch_text: str) -> Dict[str, int]:
        empty = {col: 0 for col in self.ADVANCED_COUNT_COLS}
        empty.update({
            'unsafe_additions': 0, 'unsafe_removals': 0,
            'unwrap_additions': 0, 'unwrap_removals': 0,
            'as_cast_additions': 0, 'as_cast_removals': 0,
        })
        if pd.isna(patch_text) or not patch_text.strip():
            return empty

        added_lines = []
        removed_lines = []
        for line in patch_text.splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:])
            elif line.startswith('-') and not line.startswith('---'):
                removed_lines.append(line[1:])

        added_text = "\n".join(added_lines)
        removed_text = "\n".join(removed_lines)

        counts: Dict[str, int] = {}
        for pattern, col_name in self.compiled_advanced_patterns:
            counts[col_name] = len(pattern.findall(added_text)) if added_text else 0

        counts['unsafe_additions'] = len(self.compiled_unsafe.findall(added_text)) if added_text else 0
        counts['unsafe_removals'] = len(self.compiled_unsafe.findall(removed_text)) if removed_text else 0
        counts['unwrap_additions'] = len(self.compiled_unwrap.findall(added_text)) if added_text else 0
        counts['unwrap_removals'] = len(self.compiled_unwrap.findall(removed_text)) if removed_text else 0
        counts['as_cast_additions'] = len(self.compiled_as_cast.findall(added_text)) if added_text else 0
        counts['as_cast_removals'] = len(self.compiled_as_cast.findall(removed_text)) if removed_text else 0

        return counts

    def _extract_additions_deletions(self, patch_text: str) -> Dict[str, int]:
        if pd.isna(patch_text) or not patch_text.strip():
            return {'additions': 0, 'deletions': 0, 'changes': 0}

        additions = 0
        deletions = 0

        for line in patch_text.split('\n'):
            if line.startswith('===') and line.endswith('==='):
                m = re.search(r'\(\+(\d+)/-(\d+)\)', line)
                if m:
                    additions += int(m.group(1))
                    deletions += int(m.group(2))

        if additions == 0 and deletions == 0:
            for line in patch_text.split('\n'):
                if line.startswith('+') and not line.startswith('+++'):
                    additions += 1
                elif line.startswith('-') and not line.startswith('---'):
                    deletions += 1

        return {'additions': additions, 'deletions': deletions, 'changes': additions + deletions}

    def identify_type_related_prs(self, prs_df: pd.DataFrame) -> pd.DataFrame:
        if prs_df.empty:
            print("No PRs to analyze.")
            return pd.DataFrame()

        print("\nExtracting Rust PRs (no filtering - LLM will classify type-related)...")

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

        print("   Step 1: Filtering for Rust PRs...")
        tqdm.pandas(desc="Detecting .rs files")
        working_df['has_rs_files'] = working_df['patch_text'].progress_apply(self._is_valid_rs_file)
        tqdm.pandas(desc="Counting .rs files")
        working_df['rs_files_changed'] = working_df['patch_text'].progress_apply(self._extract_rs_file_count)

        rs_prs = working_df[working_df['has_rs_files']].copy()
        print(f"   Found {len(rs_prs):,} PRs with Rust files (from {len(working_df):,} total)")

        if rs_prs.empty:
            print("   No Rust PRs found.")
            return pd.DataFrame()

        print("   Step 2: Analyzing patches for type features (statistics only)...")
        tqdm.pandas(desc="Analyzing patches")
        patch_analysis = rs_prs['patch_text'].progress_apply(self._analyze_patch)
        patch_df = pd.DataFrame(patch_analysis.tolist(), index=rs_prs.index)
        for col in patch_df.columns:
            rs_prs[col] = patch_df[col]

        tqdm.pandas(desc="Extracting add/del")
        add_del = rs_prs['patch_text'].progress_apply(self._extract_additions_deletions)
        add_del_df = pd.DataFrame(add_del.tolist(), index=rs_prs.index)
        for col in add_del_df.columns:
            rs_prs[col] = add_del_df[col]

        rs_prs['total_feature_count'] = rs_prs[self.ADVANCED_COUNT_COLS].sum(axis=1)

        print("   Step 3: Adding metadata...")
        rs_prs['group'] = 'Human'
        if 'agent' not in rs_prs.columns:
            rs_prs['agent'] = 'Human'
        rs_prs['detection_method'] = 'rust_file_detected'

        print(f"\n{'='*60}")
        print(f"EXTRACTION SUMMARY:")
        print(f"  Total PRs loaded:       {len(prs_df):,}")
        print(f"  Rust PRs extracted:     {len(rs_prs):,}")
        print(f"{'='*60}")
        return rs_prs

    def export_results(self, type_prs: pd.DataFrame, output_file: str):
        if type_prs.empty:
            print("No results to export.")
            return

        print(f"\nExporting results to {output_file}...")

        export_cols = [
            'id', 'number', 'title', 'body', 'agent', 'group', 'state',
            'created_at', 'merged_at', 'repo_id', 'html_url',
            'additions', 'deletions', 'changes', 'rs_files_changed',
            'unsafe_additions', 'unsafe_removals',
            'unwrap_additions', 'unwrap_removals',
            'as_cast_additions', 'as_cast_removals',
        ] + self.ADVANCED_COUNT_COLS + [
            'total_feature_count', 'detection_method', 'patch_text'
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
                elif col in ('agent', 'group'):
                    type_prs[col] = 'Human'
                elif col.endswith('_count') or col in (
                    'additions', 'deletions', 'changes',
                    'unsafe_additions', 'unsafe_removals',
                    'unwrap_additions', 'unwrap_removals',
                    'as_cast_additions', 'as_cast_removals',
                ):
                    type_prs[col] = 0
                else:
                    type_prs[col] = ''

        export_cols = [c for c in export_cols if c in type_prs.columns]
        type_prs[export_cols].to_csv(output_file, index=False)
        print(f"   CSV export complete: {output_file}")

        summary = {
            'extraction_date': datetime.now().isoformat(),
            'total_type_prs': len(type_prs),
            'by_group': type_prs['group'].value_counts().to_dict(),
            'by_agent': type_prs['agent'].value_counts().to_dict()
                if 'agent' in type_prs.columns else {},
            'unsafe_additions_total': int(type_prs['unsafe_additions'].sum()),
            'unsafe_removals_total': int(type_prs['unsafe_removals'].sum()),
            'unwrap_additions_total': int(type_prs['unwrap_additions'].sum()),
            'unwrap_removals_total': int(type_prs['unwrap_removals'].sum()),
            'as_cast_additions_total': int(type_prs['as_cast_additions'].sum()),
            'as_cast_removals_total': int(type_prs['as_cast_removals'].sum()),
            'advanced_feature_totals': {
                col: int(type_prs[col].sum()) for col in self.ADVANCED_COUNT_COLS
            },
            'group_feature_density': {
                'Human': {
                    col: round(float(type_prs[col].sum()) / len(type_prs), 4)
                    if len(type_prs) > 0 else 0
                    for col in self.ADVANCED_COUNT_COLS
                }
            }
        }

        summary_file = output_file.replace('.csv', '_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"   Summary saved to {summary_file}")

    def run_pipeline(self, input_file: str, output_file: str = 'human_rust_prs_for_llm.csv'):
        print("=" * 80)
        print("Human Rust PR Extraction (All Rust PRs - No Filtering)")
        print("=" * 80)

        self.load_human_prs(input_file)
        type_prs = self.identify_type_related_prs(self.human_prs)
        self.export_results(type_prs, output_file)

        print("\n" + "=" * 80)
        print("Pipeline completed!")
        print("=" * 80)
        return type_prs


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Extract Rust PRs for LLM classification')
    parser.add_argument('--input', default='datasets/rust_data/scraped_rust_prs.csv',
                        help='Input CSV file (scraped human Rust PRs)')
    parser.add_argument('--output', default='datasets/rust_data/human_rust_prs_for_llm.csv',
                        help='Output CSV file')

    args = parser.parse_args()

    import os
    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    extractor = HumanRustTypePRExtractor()
    return extractor.run_pipeline(input_file=args.input, output_file=args.output)


if __name__ == '__main__':
    main()

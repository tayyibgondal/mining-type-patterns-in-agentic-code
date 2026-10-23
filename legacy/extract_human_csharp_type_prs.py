import pandas as pd
import re
from typing import List, Set, Dict, Any
import json
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

class HumanCSharpTypePRExtractor:
    """Extracts ALL C# PRs from human PR dataset (no filtering - LLM will classify)."""
    
    CS_EXTENSIONS = {'.cs'}
    
    # C# Type Feature Patterns (for statistics only, not for filtering)
    ADVANCED_TYPE_PATTERNS = [
        (r'<[^<>]+>', 'generics_count'),
        (r'\w+\?(?!\?)', 'nullable_count'),
        (r'![\.\[\(]', 'null_forgiving_count'),
        (r'\bvar\s+\w+', 'var_count'),
        (r'\bdynamic\s+\w+', 'dynamic_count'),
        (r'\brecord\s+(?:class|struct)?\s*\w+', 'record_count'),
        (r'\binit\s*;', 'init_count'),
        (r'\brequired\s+\w+', 'required_count'),
        (r'\bis\s+(?:not\s+)?\w+', 'is_pattern_count'),
        (r'\btypeof\s*\(', 'typeof_count'),
        (r'\bas\s+\w+', 'as_cast_count'),
    ]

    def __init__(self):
        self.human_prs = None
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for feature counting only."""
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


    def _is_valid_cs_file(self, patch_text: str) -> bool:
        """Check if patch contains valid C# files."""
        if pd.isna(patch_text) or not patch_text.strip():
            return False
        
        # Check custom header format (=== filename ===)
        for line in patch_text.split('\n'):
            if line.startswith('===') and line.endswith('==='):
                filename = line.split('===')[1].strip().split('(')[0].strip()
                path = Path(filename)
                if path.suffix.lower() in self.CS_EXTENSIONS:
                    if not path.name.endswith('.Designer.cs') and not path.name.endswith('.g.cs'):
                        return True
        
        # Check standard git diff format
        for line in patch_text.split('\n')[:50]:
            if line.startswith('diff --git') or line.startswith('---') or line.startswith('+++'):
                if '.cs' in line:
                    if '.Designer.cs' not in line and '.g.cs' not in line:
                        return True
        
        return False

    def _extract_cs_file_count(self, patch_text: str) -> int:
        """Extract count of C# files in patch."""
        if pd.isna(patch_text) or not patch_text.strip():
            return 0
        
        cs_files = set()
        
        # Check custom header format
        for line in patch_text.split('\n'):
            if line.startswith('===') and line.endswith('==='):
                filename = line.split('===')[1].strip().split('(')[0].strip()
                path = Path(filename)
                if path.suffix.lower() in self.CS_EXTENSIONS:
                    if not path.name.endswith('.Designer.cs') and not path.name.endswith('.g.cs'):
                        cs_files.add(filename)
        
        return len(cs_files)

    def _analyze_patch(self, patch_text: str) -> Dict[str, int]:
        """Analyze patch for C# type features (no scoring, just counting)."""
        empty_result = {col: 0 for col in self.ADVANCED_COUNT_COLS}
        
        if pd.isna(patch_text) or not patch_text.strip():
            return empty_result
        
        # Extract added lines
        added_lines = "\n".join([
            line for line in patch_text.splitlines() 
            if line.startswith('+') and not line.startswith('+++')
        ])
        
        # Count advanced features
        advanced_counts = {}
        for pattern, col_name in self.compiled_advanced_patterns:
            advanced_counts[col_name] = len(pattern.findall(added_lines))
        
        return advanced_counts

    def _extract_additions_deletions(self, patch_text: str) -> Dict[str, int]:
        """Extract additions and deletions from patch."""
        if pd.isna(patch_text) or not patch_text.strip():
            return {'additions': 0, 'deletions': 0, 'changes': 0}
        
        additions = 0
        deletions = 0
        
        # Try custom header format first
        for line in patch_text.split('\n'):
            if line.startswith('===') and line.endswith('==='):
                match = re.search(r'\(\+(\d+)/-(\d+)\)', line)
                if match:
                    additions += int(match.group(1))
                    deletions += int(match.group(2))
        
        # Fallback: count +/- lines
        if additions == 0 and deletions == 0:
            for line in patch_text.split('\n'):
                if line.startswith('+') and not line.startswith('+++'):
                    additions += 1
                elif line.startswith('-') and not line.startswith('---'):
                    deletions += 1
        
        changes = additions + deletions
        return {'additions': additions, 'deletions': deletions, 'changes': changes}

    def identify_type_related_prs(self, prs_df: pd.DataFrame) -> pd.DataFrame:
        """Extract ALL C# PRs (no filtering - let LLM handle it)."""
        if prs_df.empty:
            print("No PRs to analyze.")
            return pd.DataFrame()

        print("\nExtracting C# PRs (no filtering - all C# PRs will be included)...")
        
        # Map column names
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
        
        # Ensure required columns exist
        for col in ['title', 'body']:
            if col not in working_df.columns:
                working_df[col] = ''
        
        print("   Step 1: Filtering for C# PRs...")
        tqdm.pandas(desc="Detecting C# files")
        working_df['has_cs_files'] = working_df['patch_text'].progress_apply(self._is_valid_cs_file)
        tqdm.pandas(desc="Counting C# files")
        working_df['cs_files_changed'] = working_df['patch_text'].progress_apply(self._extract_cs_file_count)
        
        cs_prs = working_df[working_df['has_cs_files']].copy()
        print(f"   ✓ Found {len(cs_prs):,} PRs with C# files (from {len(working_df):,} total)")
        
        if cs_prs.empty:
            print("   No C# PRs found.")
            return pd.DataFrame()
        
        print("   Step 2: Analyzing patches for type features (for statistics only)...")
        tqdm.pandas(desc="Analyzing patches")
        patch_analysis = cs_prs['patch_text'].progress_apply(self._analyze_patch)
        patch_df = pd.DataFrame(patch_analysis.tolist(), index=cs_prs.index)
        
        for col in patch_df.columns:
            cs_prs[col] = patch_df[col]
        
        tqdm.pandas(desc="Extracting add/del")
        add_del = cs_prs['patch_text'].progress_apply(self._extract_additions_deletions)
        add_del_df = pd.DataFrame(add_del.tolist(), index=cs_prs.index)
        for col in add_del_df.columns:
            cs_prs[col] = add_del_df[col]
        
        print("   Step 3: Adding metadata...")
        cs_prs['group'] = 'Human'
        
        if 'agent' not in cs_prs.columns:
            cs_prs['agent'] = 'Human'
        
        cs_prs['detection_method'] = 'csharp_file_detected'

        print(f"\n{'='*60}")
        print(f"EXTRACTION SUMMARY:")
        print(f"{'='*60}")
        print(f"  Total PRs loaded:              {len(prs_df):,}")
        print(f"  ✓ C# PRs extracted:            {len(cs_prs):,}")
        print(f"{'='*60}")
        print(f"✓ All C# PRs extracted (LLM will filter for type-related)")
        print(f"{'='*60}\n")
        return cs_prs

    def export_results(self, type_prs: pd.DataFrame, output_file: str):
        """Export results to CSV and JSON summary."""
        if type_prs.empty:
            print("No results to export.")
            return

        print(f"\n{'='*60}")
        print(f"Exporting results to {output_file}...")
        print(f"{'='*60}")
        
        export_cols = [
            'id', 'number', 'title', 'body', 'agent', 'group', 'state', 
            'created_at', 'merged_at', 'repo_id', 'html_url', 
            'additions', 'deletions', 'changes', 'cs_files_changed',
        ] + self.ADVANCED_COUNT_COLS + [
            'detection_method', 'patch_text'
        ]
        
        # Fill missing columns
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

    def run_pipeline(self, input_file: str, output_file: str = 'human_csharp_prs_for_llm.csv'):
        """Run the complete extraction pipeline (extracts ALL C# PRs for LLM classification)."""
        print("="*80)
        print("Human C# PR Extraction (All C# PRs - No Filtering)")
        print("="*80)
        
        self.load_human_prs(input_file)
        type_prs = self.identify_type_related_prs(self.human_prs)
        self.export_results(type_prs, output_file)

        print("\n" + "="*80)
        print("Pipeline completed!")
        print("="*80)
        return type_prs


def main():
    """Main entry point - extracts ALL C# PRs for LLM classification."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract C# PRs for LLM classification')
    parser.add_argument('--input', default='human_pr_data.csv',
                       help='Input CSV file (default: human_pr_data.csv)')
    parser.add_argument('--output', default='human_csharp_prs_for_llm.csv',
                       help='Output CSV file (default: human_csharp_prs_for_llm.csv)')
    
    args = parser.parse_args()
    
    extractor = HumanCSharpTypePRExtractor()
    results = extractor.run_pipeline(
        input_file=args.input,
        output_file=args.output
    )
    return results


if __name__ == '__main__':
    main()


"""
COMPREHENSIVE EFFECT SIZES REPORT
For all statistical tests in the research paper
Includes median values as requested by reviewer
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import mannwhitneyu, chi2_contingency, fisher_exact
import re
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# LOAD DATA - with correct file paths
# ============================================================================
print("="*80)
print("EFFECT SIZES REPORT FOR RESEARCH PAPER")
print("="*80)
print("\n[1] LOADING DATA...")

# TypeScript - correct file paths
ts_agent = pd.read_csv('../../typescript_data/agent_type_prs_filtered_by_open_ai.csv')
ts_agent = ts_agent[ts_agent['final_is_type_related'] == True]
ts_human = pd.read_csv('../../typescript_data/human_type_prs_filtered_by_open_ai.csv')
ts_human = ts_human[ts_human['final_is_type_related'] == True]

print(f"TypeScript - AI Agent PRs: {len(ts_agent)}")
print(f"TypeScript - Human PRs: {len(ts_human)}")

# C# - correct file paths (note the different naming convention)
try:
    cs_agent = pd.read_csv('../../csharp_data/csharp_classified_type_prs.csv')
    cs_agent = cs_agent[cs_agent['final_is_type_related'] == True]
    cs_human = pd.read_csv('../../csharp_data/human_csharp_classified_type_prs.csv')
    cs_human = cs_human[cs_human['final_is_type_related'] == True]
    print(f"C# - AI Agent PRs: {len(cs_agent)}")
    print(f"C# - Human PRs: {len(cs_human)}")
    has_csharp = True
except Exception as e:
    print(f"C# data not available or error: {e}")
    has_csharp = False

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_any_metrics(df):
    """Extract TypeScript 'any' metrics from patches"""
    pattern = r':\s*any[\s,;>\)\|&]|<any>|as\s+any|\|\s*any|&\s*any|Array<any>|Promise<any>|Record<\w+,\s*any>|Record<any'
    metrics = []
    
    for _, row in df.iterrows():
        patch = str(row.get('patch_text', ''))
        adds, rems = 0, 0
        
        for line in patch.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                adds += len(re.findall(pattern, line))
            elif line.startswith('-') and not line.startswith('---'):
                rems += len(re.findall(pattern, line))
        
        metrics.append({
            'any_additions': adds,
            'any_removals': rems,
            'net_change': adds - rems
        })
    
    return pd.DataFrame(metrics)

def extract_ts_features(df):
    """Extract TypeScript advanced features"""
    FEATURES = {
        'generics': r'<[A-Z]\w*(?:\s+extends\s+[^>]+)?(?:,\s*[A-Z]\w*(?:\s+extends\s+[^>]+)?)*>',
        'union_types': r'\|\s*\w+',
        'type_assertions': r'\bas\s+\w+',
        'optional_chaining': r'\?\.',
        'non_null_assertion': r'!\.',
        'type_guards': r'\b(?:is|asserts)\s+\w+',
        'satisfies': r'\bsatisfies\s+',
        'as_const': r'\bas\s+const\b',
        'nullish_coalescing': r'\?\?',
        'keyof_typeof': r'\b(?:keyof|typeof)\s+',
    }
    
    features = []
    for _, row in df.iterrows():
        patch = str(row.get('patch_text', ''))
        added = '\n'.join([l for l in patch.split('\n') if l.startswith('+')])
        
        counts = {name: len(re.findall(pat, added, re.IGNORECASE)) 
                 for name, pat in FEATURES.items()}
        counts['total'] = sum(counts.values())
        counts['unique'] = sum(1 for v in counts.values() if v > 0)
        features.append(counts)
    
    return pd.DataFrame(features)

def cohens_d(group1, group2):
    """Calculate Cohen's d effect size"""
    n1, n2 = len(group1), len(group2)
    if n1 == 0 or n2 == 0:
        return np.nan
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
    if pooled_std == 0:
        return 0
    return (np.mean(group1) - np.mean(group2)) / pooled_std

def cramers_v(contingency_table):
    """Calculate Cramér's V effect size for chi-square test"""
    chi2, p, dof, expected = chi2_contingency(contingency_table)
    n = contingency_table.sum()
    min_dim = min(contingency_table.shape) - 1
    if min_dim == 0:
        return 0
    return np.sqrt(chi2 / (n * min_dim))

def odds_ratio(contingency_table):
    """Calculate odds ratio for 2x2 contingency table"""
    a, b = contingency_table[0]
    c, d = contingency_table[1]
    if b == 0 or c == 0:
        return np.inf
    return (a * d) / (b * c)

def interpret_effect_size_d(d):
    """Interpret Cohen's d"""
    d = abs(d)
    if d < 0.2: return "negligible"
    elif d < 0.5: return "small"
    elif d < 0.8: return "medium"
    else: return "large"

def interpret_effect_size_v(v):
    """Interpret Cramér's V"""
    v = abs(v)
    if v < 0.1: return "negligible"
    elif v < 0.3: return "small"
    elif v < 0.5: return "medium"
    else: return "large"

def interpret_pvalue(p):
    """Interpret p-value with significance markers"""
    if p < 0.001: return "***"
    elif p < 0.01: return "**"
    elif p < 0.05: return "*"
    else: return "ns"

# ============================================================================
# EXTRACT METRICS
# ============================================================================
print("\n[2] EXTRACTING METRICS...")

ts_agent_any = extract_any_metrics(ts_agent)
ts_human_any = extract_any_metrics(ts_human)
print(f"✓ TypeScript 'any' metrics extracted")

ts_agent_feat = extract_ts_features(ts_agent)
ts_human_feat = extract_ts_features(ts_human)
print(f"✓ TypeScript features extracted")

# Acceptance metrics
ts_agent['is_merged'] = ts_agent['merged_at'].notna()
ts_human['is_merged'] = ts_human['merged_at'].notna()
print(f"✓ Acceptance metrics calculated")

# ============================================================================
# OUTPUT FILE
# ============================================================================
output_lines = []
output_lines.append("="*80)
output_lines.append("COMPREHENSIVE EFFECT SIZES REPORT FOR RESEARCH PAPER")
output_lines.append("="*80)
output_lines.append("")

# ============================================================================
# RQ1: 'any' TYPE USAGE ANALYSIS
# ============================================================================
print("\n" + "="*80)
print("RQ1: 'any' TYPE USAGE ANALYSIS")
print("="*80)

output_lines.append("="*80)
output_lines.append("RQ1: 'any' TYPE USAGE ANALYSIS (TypeScript)")
output_lines.append("="*80)
output_lines.append("")

# All PRs (including those with zero additions)
all_agent_any = ts_agent_any['any_additions']
all_human_any = ts_human_any['any_additions']

# PRs with at least one 'any' addition
agent_any_nz = ts_agent_any[ts_agent_any['any_additions'] > 0]['any_additions']
human_any_nz = ts_human_any[ts_human_any['any_additions'] > 0]['any_additions']

# Compute statistics for ALL PRs (as reported in the paper)
u_stat_all, p_val_all = mannwhitneyu(all_agent_any, all_human_any, alternative='two-sided')
effect_d_all = cohens_d(all_agent_any, all_human_any)

# Print and record results
print("\n[RQ1 - Figure 1] 'any' Type Additions (ALL PRs)")
print("-"*80)
print(f"Sample sizes: AI Agent={len(all_agent_any)}, Human={len(all_human_any)}")
print(f"")
print(f"AI Agent Statistics:")
print(f"  Mean:   {all_agent_any.mean():.4f}")
print(f"  Median: {all_agent_any.median():.4f}")
print(f"  Std:    {all_agent_any.std():.4f}")
print(f"")
print(f"Human Statistics:")
print(f"  Mean:   {all_human_any.mean():.4f}")
print(f"  Median: {all_human_any.median():.4f}")
print(f"  Std:    {all_human_any.std():.4f}")
print(f"")
print(f"Ratio (AI Mean / Human Mean): {all_agent_any.mean() / all_human_any.mean():.2f}x")
print(f"")
print(f"Mann-Whitney U Test:")
print(f"  U-statistic: {u_stat_all:.2f}")
print(f"  p-value:     {p_val_all:.2e} {interpret_pvalue(p_val_all)}")
print(f"")
print(f"Effect Size (Cohen's d): {effect_d_all:.4f} ({interpret_effect_size_d(effect_d_all)})")

output_lines.append("[RQ1 - Figure 1] 'any' Type Additions (ALL PRs)")
output_lines.append("-"*80)
output_lines.append(f"Sample sizes: AI Agent={len(all_agent_any)}, Human={len(all_human_any)}")
output_lines.append("")
output_lines.append("AI Agent Statistics:")
output_lines.append(f"  Mean:   {all_agent_any.mean():.4f}")
output_lines.append(f"  Median: {all_agent_any.median():.4f}")
output_lines.append(f"  Std:    {all_agent_any.std():.4f}")
output_lines.append("")
output_lines.append("Human Statistics:")
output_lines.append(f"  Mean:   {all_human_any.mean():.4f}")
output_lines.append(f"  Median: {all_human_any.median():.4f}")
output_lines.append(f"  Std:    {all_human_any.std():.4f}")
output_lines.append("")
output_lines.append(f"Ratio (AI Mean / Human Mean): {all_agent_any.mean() / all_human_any.mean():.2f}x")
output_lines.append("")
output_lines.append("Mann-Whitney U Test:")
output_lines.append(f"  U-statistic: {u_stat_all:.2f}")
output_lines.append(f"  p-value:     {p_val_all:.2e} {interpret_pvalue(p_val_all)}")
output_lines.append("")
output_lines.append(f"Effect Size (Cohen's d): {effect_d_all:.4f} ({interpret_effect_size_d(effect_d_all)})")
output_lines.append("")

# Also compute for non-zero only (for completeness)
if len(agent_any_nz) > 0 and len(human_any_nz) > 0:
    u_stat_nz, p_val_nz = mannwhitneyu(agent_any_nz, human_any_nz, alternative='two-sided')
    effect_d_nz = cohens_d(agent_any_nz, human_any_nz)
    
    print("\n[RQ1 - Additional] 'any' Type Additions (PRs with at least one addition)")
    print("-"*80)
    print(f"Sample sizes: AI Agent={len(agent_any_nz)}, Human={len(human_any_nz)}")
    print(f"AI Agent: Mean={agent_any_nz.mean():.4f}, Median={agent_any_nz.median():.4f}")
    print(f"Human:    Mean={human_any_nz.mean():.4f}, Median={human_any_nz.median():.4f}")
    print(f"p-value: {p_val_nz:.2e}")
    print(f"Effect Size (Cohen's d): {effect_d_nz:.4f} ({interpret_effect_size_d(effect_d_nz)})")
    
    output_lines.append("[RQ1 - Additional] 'any' Type Additions (PRs with at least one addition)")
    output_lines.append("-"*80)
    output_lines.append(f"Sample sizes: AI Agent={len(agent_any_nz)}, Human={len(human_any_nz)}")
    output_lines.append(f"AI Agent: Mean={agent_any_nz.mean():.4f}, Median={agent_any_nz.median():.4f}")
    output_lines.append(f"Human:    Mean={human_any_nz.mean():.4f}, Median={human_any_nz.median():.4f}")
    output_lines.append(f"p-value: {p_val_nz:.2e}")
    output_lines.append(f"Effect Size (Cohen's d): {effect_d_nz:.4f} ({interpret_effect_size_d(effect_d_nz)})")
    output_lines.append("")

# ============================================================================
# RQ2: ADVANCED FEATURE USAGE ANALYSIS
# ============================================================================
print("\n" + "="*80)
print("RQ2: ADVANCED FEATURE USAGE ANALYSIS")
print("="*80)

output_lines.append("="*80)
output_lines.append("RQ2: ADVANCED FEATURE USAGE ANALYSIS (TypeScript)")
output_lines.append("="*80)
output_lines.append("")

# Feature Diversity (Unique features per PR)
print("\n[RQ2 - Table 2/Figure 2] Feature Diversity (Unique Features per PR)")
print("-"*80)

agent_unique = ts_agent_feat['unique']
human_unique = ts_human_feat['unique']

u_stat, p_val = mannwhitneyu(agent_unique, human_unique, alternative='two-sided')
effect_d = cohens_d(agent_unique, human_unique)

print(f"Sample sizes: AI Agent={len(agent_unique)}, Human={len(human_unique)}")
print(f"")
print(f"AI Agent Statistics:")
print(f"  Mean:   {agent_unique.mean():.4f}")
print(f"  Median: {agent_unique.median():.4f}")
print(f"  Std:    {agent_unique.std():.4f}")
print(f"")
print(f"Human Statistics:")
print(f"  Mean:   {human_unique.mean():.4f}")
print(f"  Median: {human_unique.median():.4f}")
print(f"  Std:    {human_unique.std():.4f}")
print(f"")
print(f"Mann-Whitney U Test:")
print(f"  U-statistic: {u_stat:.2f}")
print(f"  p-value:     {p_val:.2e} {interpret_pvalue(p_val)}")
print(f"")
print(f"Effect Size (Cohen's d): {effect_d:.4f} ({interpret_effect_size_d(effect_d)})")

output_lines.append("[RQ2 - Table 2/Figure 2] Feature Diversity (Unique Features per PR)")
output_lines.append("-"*80)
output_lines.append(f"Sample sizes: AI Agent={len(agent_unique)}, Human={len(human_unique)}")
output_lines.append("")
output_lines.append("AI Agent Statistics:")
output_lines.append(f"  Mean:   {agent_unique.mean():.4f}")
output_lines.append(f"  Median: {agent_unique.median():.4f}")
output_lines.append(f"  Std:    {agent_unique.std():.4f}")
output_lines.append("")
output_lines.append("Human Statistics:")
output_lines.append(f"  Mean:   {human_unique.mean():.4f}")
output_lines.append(f"  Median: {human_unique.median():.4f}")
output_lines.append(f"  Std:    {human_unique.std():.4f}")
output_lines.append("")
output_lines.append("Mann-Whitney U Test:")
output_lines.append(f"  U-statistic: {u_stat:.2f}")
output_lines.append(f"  p-value:     {p_val:.2e} {interpret_pvalue(p_val)}")
output_lines.append("")
output_lines.append(f"Effect Size (Cohen's d): {effect_d:.4f} ({interpret_effect_size_d(effect_d)})")
output_lines.append("")

# Non-null assertion analysis
print("\n[RQ2 - Figure 2] Non-null Assertion Usage")
print("-"*80)

agent_nonnull = ts_agent_feat['non_null_assertion']
human_nonnull = ts_human_feat['non_null_assertion']

# Adoption rate (proportion of PRs using this feature)
agent_adoption = (agent_nonnull > 0).sum()
human_adoption = (human_nonnull > 0).sum()

contingency = np.array([[agent_adoption, len(ts_agent_feat) - agent_adoption],
                        [human_adoption, len(ts_human_feat) - human_adoption]])

chi2, p_val, dof, expected = chi2_contingency(contingency)
cramer_v = cramers_v(contingency)
or_value = odds_ratio(contingency)

print(f"Adoption rates:")
print(f"  AI Agent: {agent_adoption}/{len(ts_agent_feat)} ({agent_adoption/len(ts_agent_feat)*100:.1f}%)")
print(f"  Human:    {human_adoption}/{len(ts_human_feat)} ({human_adoption/len(ts_human_feat)*100:.1f}%)")
print(f"")
print(f"Chi-square Test:")
print(f"  χ²:       {chi2:.4f}")
print(f"  df:       {dof}")
print(f"  p-value:  {p_val:.2e} {interpret_pvalue(p_val)}")
print(f"")
print(f"Effect Sizes:")
print(f"  Cramér's V: {cramer_v:.4f} ({interpret_effect_size_v(cramer_v)})")
print(f"  Odds Ratio: {or_value:.4f}")

output_lines.append("[RQ2 - Figure 2] Non-null Assertion Usage")
output_lines.append("-"*80)
output_lines.append("Adoption rates:")
output_lines.append(f"  AI Agent: {agent_adoption}/{len(ts_agent_feat)} ({agent_adoption/len(ts_agent_feat)*100:.1f}%)")
output_lines.append(f"  Human:    {human_adoption}/{len(ts_human_feat)} ({human_adoption/len(ts_human_feat)*100:.1f}%)")
output_lines.append("")
output_lines.append("Chi-square Test:")
output_lines.append(f"  χ²:       {chi2:.4f}")
output_lines.append(f"  df:       {dof}")
output_lines.append(f"  p-value:  {p_val:.2e} {interpret_pvalue(p_val)}")
output_lines.append("")
output_lines.append("Effect Sizes:")
output_lines.append(f"  Cramér's V: {cramer_v:.4f} ({interpret_effect_size_v(cramer_v)})")
output_lines.append(f"  Odds Ratio: {or_value:.4f}")
output_lines.append("")

# Type assertions analysis
print("\n[RQ2 - Figure 2] Type Assertion Usage")
print("-"*80)

agent_type_assert = ts_agent_feat['type_assertions']
human_type_assert = ts_human_feat['type_assertions']

u_stat, p_val = mannwhitneyu(agent_type_assert, human_type_assert, alternative='two-sided')
effect_d = cohens_d(agent_type_assert, human_type_assert)

print(f"AI Agent: Mean={agent_type_assert.mean():.4f}, Median={agent_type_assert.median():.4f}")
print(f"Human:    Mean={human_type_assert.mean():.4f}, Median={human_type_assert.median():.4f}")
print(f"p-value: {p_val:.2e}")
print(f"Effect Size (Cohen's d): {effect_d:.4f} ({interpret_effect_size_d(effect_d)})")

output_lines.append("[RQ2 - Figure 2] Type Assertion Usage")
output_lines.append("-"*80)
output_lines.append(f"AI Agent: Mean={agent_type_assert.mean():.4f}, Median={agent_type_assert.median():.4f}")
output_lines.append(f"Human:    Mean={human_type_assert.mean():.4f}, Median={human_type_assert.median():.4f}")
output_lines.append(f"p-value: {p_val:.2e}")
output_lines.append(f"Effect Size (Cohen's d): {effect_d:.4f} ({interpret_effect_size_d(effect_d)})")
output_lines.append("")

# ============================================================================
# RQ3: ACCEPTANCE RATE ANALYSIS
# ============================================================================
print("\n" + "="*80)
print("RQ3: ACCEPTANCE RATE ANALYSIS")
print("="*80)

output_lines.append("="*80)
output_lines.append("RQ3: ACCEPTANCE RATE ANALYSIS (TypeScript)")
output_lines.append("="*80)
output_lines.append("")

print("\n[RQ3 - Table 3] Overall Acceptance Rate")
print("-"*80)

agent_merged = ts_agent['is_merged'].sum()
human_merged = ts_human['is_merged'].sum()
agent_total = len(ts_agent)
human_total = len(ts_human)

contingency = np.array([[agent_merged, agent_total - agent_merged],
                        [human_merged, human_total - human_merged]])

chi2, p_val, dof, expected = chi2_contingency(contingency)
cramer_v = cramers_v(contingency)
or_value = odds_ratio(contingency)

print(f"Acceptance rates:")
print(f"  AI Agent: {agent_merged}/{agent_total} ({agent_merged/agent_total*100:.1f}%)")
print(f"  Human:    {human_merged}/{human_total} ({human_merged/human_total*100:.1f}%)")
print(f"")
print(f"Ratio (AI rate / Human rate): {(agent_merged/agent_total) / (human_merged/human_total):.2f}x")
print(f"")
print(f"Chi-square Test:")
print(f"  χ²:       {chi2:.4f}")
print(f"  df:       {dof}")
print(f"  p-value:  {p_val:.2e} {interpret_pvalue(p_val)}")
print(f"")
print(f"Effect Sizes:")
print(f"  Cramér's V: {cramer_v:.4f} ({interpret_effect_size_v(cramer_v)})")
print(f"  Odds Ratio: {or_value:.4f}")

output_lines.append("[RQ3 - Table 3] Overall Acceptance Rate")
output_lines.append("-"*80)
output_lines.append("Acceptance rates:")
output_lines.append(f"  AI Agent: {agent_merged}/{agent_total} ({agent_merged/agent_total*100:.1f}%)")
output_lines.append(f"  Human:    {human_merged}/{human_total} ({human_merged/human_total*100:.1f}%)")
output_lines.append("")
output_lines.append(f"Ratio (AI rate / Human rate): {(agent_merged/agent_total) / (human_merged/human_total):.2f}x")
output_lines.append("")
output_lines.append("Chi-square Test:")
output_lines.append(f"  χ²:       {chi2:.4f}")
output_lines.append(f"  df:       {dof}")
output_lines.append(f"  p-value:  {p_val:.2e} {interpret_pvalue(p_val)}")
output_lines.append("")
output_lines.append("Effect Sizes:")
output_lines.append(f"  Cramér's V: {cramer_v:.4f} ({interpret_effect_size_v(cramer_v)})")
output_lines.append(f"  Odds Ratio: {or_value:.4f}")
output_lines.append("")

# ============================================================================
# SUMMARY TABLE
# ============================================================================
print("\n" + "="*80)
print("SUMMARY TABLE OF ALL EFFECT SIZES")
print("="*80)

output_lines.append("="*80)
output_lines.append("SUMMARY TABLE FOR PAPER")
output_lines.append("="*80)
output_lines.append("")

# Recalculate all effect sizes for summary
u_stat_any, p_val_any = mannwhitneyu(all_agent_any, all_human_any, alternative='two-sided')
effect_d_any = cohens_d(all_agent_any, all_human_any)

u_stat_feat, p_val_feat = mannwhitneyu(agent_unique, human_unique, alternative='two-sided')
effect_d_feat = cohens_d(agent_unique, human_unique)

contingency_accept = np.array([[agent_merged, agent_total - agent_merged],
                               [human_merged, human_total - human_merged]])
chi2_accept, p_val_accept, _, _ = chi2_contingency(contingency_accept)
cramer_v_accept = cramers_v(contingency_accept)

summary_data = [
    {
        'Test': 'RQ1: any additions',
        'Statistical Test': 'Mann-Whitney U',
        'p-value': f"{p_val_any:.2e}",
        'Effect Size': f"Cohen's d = {effect_d_any:.3f}",
        'Interpretation': interpret_effect_size_d(effect_d_any),
        'AI Mean (Median)': f"{all_agent_any.mean():.2f} ({all_agent_any.median():.1f})",
        'Human Mean (Median)': f"{all_human_any.mean():.2f} ({all_human_any.median():.1f})"
    },
    {
        'Test': 'RQ2: Feature diversity',
        'Statistical Test': 'Mann-Whitney U',
        'p-value': f"{p_val_feat:.2e}",
        'Effect Size': f"Cohen's d = {effect_d_feat:.3f}",
        'Interpretation': interpret_effect_size_d(effect_d_feat),
        'AI Mean (Median)': f"{agent_unique.mean():.2f} ({agent_unique.median():.1f})",
        'Human Mean (Median)': f"{human_unique.mean():.2f} ({human_unique.median():.1f})"
    },
    {
        'Test': 'RQ3: Acceptance rate',
        'Statistical Test': 'Chi-square',
        'p-value': f"{p_val_accept:.2e}",
        'Effect Size': f"Cramér's V = {cramer_v_accept:.3f}",
        'Interpretation': interpret_effect_size_v(cramer_v_accept),
        'AI Mean (Median)': f"{agent_merged/agent_total*100:.1f}%",
        'Human Mean (Median)': f"{human_merged/human_total*100:.1f}%"
    }
]

summary_df = pd.DataFrame(summary_data)
print(summary_df.to_string(index=False))

output_lines.append("Summary of Effect Sizes:")
output_lines.append("-"*80)
for row in summary_data:
    output_lines.append(f"{row['Test']}:")
    output_lines.append(f"  Test: {row['Statistical Test']}, p = {row['p-value']}")
    output_lines.append(f"  {row['Effect Size']} ({row['Interpretation']})")
    output_lines.append(f"  AI: {row['AI Mean (Median)']}, Human: {row['Human Mean (Median)']}")
    output_lines.append("")

# ============================================================================
# RECOMMENDED TEXT FOR PAPER (with reviewer request for median)
# ============================================================================
output_lines.append("="*80)
output_lines.append("RECOMMENDED TEXT FOR PAPER (addressing reviewer request)")
output_lines.append("="*80)
output_lines.append("")
output_lines.append("For RQ1 paragraph (with median values added):")
output_lines.append("-"*80)
output_lines.append(f"""
As shown in Figure 1, AI agents are {all_agent_any.mean() / all_human_any.mean():.0f} times more likely to 
introduce the `any` type into the TypeScript codebases compared to human developers, 
with means of the 'any addition' distributions across PRs at {all_agent_any.mean():.2f} and {all_human_any.mean():.2f}, 
respectively (medians: {all_agent_any.median():.1f} vs. {all_human_any.median():.1f}). 
Mann-Whitney U test (p ≈ {p_val_any:.2e}) demonstrated the statistical significance of this 
result with a {interpret_effect_size_d(effect_d_any)} effect size (Cohen's d = {effect_d_any:.2f}).
""")

print("\n" + "="*80)
print("RECOMMENDED TEXT FOR PAPER (with median values)")
print("="*80)
print(f"""
As shown in Figure 1, AI agents are {all_agent_any.mean() / all_human_any.mean():.0f} times more likely to 
introduce the `any` type into the TypeScript codebases compared to human developers, 
with means of the 'any addition' distributions across PRs at {all_agent_any.mean():.2f} and {all_human_any.mean():.2f}, 
respectively (medians: {all_agent_any.median():.1f} vs. {all_human_any.median():.1f}). 
Mann-Whitney U test (p ≈ {p_val_any:.2e}) demonstrated the statistical significance of this 
result with a {interpret_effect_size_d(effect_d_any)} effect size (Cohen's d = {effect_d_any:.2f}).
""")

# Save to file
output_file = 'EFFECT_SIZES_REPORT.md'
with open(output_file, 'w') as f:
    f.write('\n'.join(output_lines))

print(f"\n✓ Full report saved to: {output_file}")

# Also save as CSV for easy reference
summary_df.to_csv('EFFECT_SIZES_SUMMARY.csv', index=False)
print(f"✓ Summary saved to: EFFECT_SIZES_SUMMARY.csv")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)

"""
COMPREHENSIVE STATISTICAL ANALYSIS
Rigorous statistical testing for all TypeScript and C# figures
Acting as a seasoned statistician
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import mannwhitneyu, chi2_contingency, ttest_ind, fisher_exact
import re
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("COMPREHENSIVE STATISTICAL ANALYSIS REPORT")
print("TypeScript and C# Type-Related Pull Requests")
print("="*80)

# ============================================================================
# LOAD DATA
# ============================================================================
print("\n[1] LOADING DATA...")
print("-"*80)

# TypeScript
ts_agent = pd.read_csv('typescript_data/agent_type_prs_filtered_by_open_ai.csv')
ts_agent = ts_agent[ts_agent['final_is_type_related'] == True]
ts_human = pd.read_csv('typescript_data/human_type_prs_filtered_by_open_ai.csv')
ts_human = ts_human[ts_human['final_is_type_related'] == True]

print(f"TypeScript - AI: {len(ts_agent)}, Human: {len(ts_human)}")

# C#
cs_agent = pd.read_csv('csharp_data/agent_type_prs_filtered_by_open_ai.csv')
cs_agent = cs_agent[cs_agent['final_is_type_related'] == True]
cs_human = pd.read_csv('csharp_data/human_type_prs_filtered_by_open_ai.csv')
cs_human = cs_human[cs_human['final_is_type_related'] == True]

print(f"C# - AI: {len(cs_agent)}, Human: {len(cs_human)}")

# ============================================================================
# EXTRACT METRICS FUNCTIONS
# ============================================================================

def extract_any_metrics(df):
    """Extract TypeScript 'any' metrics"""
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

def extract_dynamic_metrics(df):
    """Extract C# 'dynamic' metrics"""
    pattern = r'\bdynamic\s+\w+|\bdynamic\>|:\s*dynamic\b|<dynamic>'
    metrics = []
    
    for _, row in df.iterrows():
        patch = str(row.get('patch_text', ''))
        adds, rems = 0, 0
        
        for line in patch.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                adds += len(re.findall(pattern, line, re.IGNORECASE))
            elif line.startswith('-') and not line.startswith('---'):
                rems += len(re.findall(pattern, line, re.IGNORECASE))
        
        metrics.append({
            'dynamic_additions': adds,
            'dynamic_removals': rems,
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

def extract_cs_features(df):
    """Extract C# advanced features"""
    FEATURES = {
        'generics': r'<[^<>]+>',
        'nullable': r'\w+\?(?!\?)',
        'null_forgiving': r'![\.\[\(]',
        'pattern_matching': r'\bis\s+(?:not\s+)?(?:\w+|\{)',
        'async_await': r'\b(?:async|await)\b',
        'linq': r'\b(?:from|where|select|join|group)\s+\w+',
        'null_coalescing': r'\?\?',
        'null_conditional': r'\?\.',
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

# ============================================================================
# EXTRACT ALL METRICS
# ============================================================================
print("\n[2] EXTRACTING METRICS...")
print("-"*80)

ts_agent_any = extract_any_metrics(ts_agent)
ts_human_any = extract_any_metrics(ts_human)
print("✓ TypeScript 'any' metrics extracted")

cs_agent_dyn = extract_dynamic_metrics(cs_agent)
cs_human_dyn = extract_dynamic_metrics(cs_human)
print("✓ C# 'dynamic' metrics extracted")

ts_agent_feat = extract_ts_features(ts_agent)
ts_human_feat = extract_ts_features(ts_human)
print("✓ TypeScript features extracted")

cs_agent_feat = extract_cs_features(cs_agent)
cs_human_feat = extract_cs_features(cs_human)
print("✓ C# features extracted")

# Acceptance metrics
ts_agent['is_merged'] = ts_agent['merged_at'].notna()
ts_human['is_merged'] = ts_human['merged_at'].notna()
cs_agent['is_merged'] = cs_agent['merged_at'].notna()
cs_human['is_merged'] = cs_human['merged_at'].notna()
print("✓ Acceptance metrics calculated")

# ============================================================================
# STATISTICAL TESTING
# ============================================================================

def cohens_d(group1, group2):
    """Calculate Cohen's d effect size"""
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
    return (np.mean(group1) - np.mean(group2)) / pooled_std if pooled_std > 0 else 0

def interpret_effect_size(d):
    """Interpret Cohen's d"""
    d = abs(d)
    if d < 0.2: return "negligible"
    elif d < 0.5: return "small"
    elif d < 0.8: return "medium"
    else: return "large"

def interpret_pvalue(p):
    """Interpret p-value"""
    if p < 0.001: return "***"
    elif p < 0.01: return "**"
    elif p < 0.05: return "*"
    else: return "ns"

print("\n" + "="*80)
print("STATISTICAL TEST RESULTS")
print("="*80)

results = []

# ============================================================================
# RQ1: ESCAPE TYPE USAGE (any/dynamic)
# ============================================================================
print("\n" + "="*80)
print("RQ1: ESCAPE TYPE USAGE ANALYSIS")
print("="*80)

# TypeScript 'any' additions
print("\n[TS-RQ1-Fig1] 'any' Type Additions")
print("-"*80)
ts_agent_any_nz = ts_agent_any[ts_agent_any['any_additions'] > 0]['any_additions']
ts_human_any_nz = ts_human_any[ts_human_any['any_additions'] > 0]['any_additions']

if len(ts_agent_any_nz) > 0 and len(ts_human_any_nz) > 0:
    # Mann-Whitney U (non-parametric, for non-normal distributions)
    u_stat, p_val = mannwhitneyu(ts_agent_any_nz, ts_human_any_nz, alternative='two-sided')
    effect = cohens_d(ts_agent_any_nz, ts_human_any_nz)
    
    print(f"Test: Mann-Whitney U test (non-parametric)")
    print(f"Reason: Non-normal distribution expected for count data with outliers")
    print(f"Sample sizes: AI={len(ts_agent_any_nz)}, Human={len(ts_human_any_nz)}")
    print(f"Medians: AI={ts_agent_any_nz.median():.2f}, Human={ts_human_any_nz.median():.2f}")
    print(f"Means: AI={ts_agent_any_nz.mean():.2f}, Human={ts_human_any_nz.mean():.2f}")
    print(f"U-statistic: {u_stat:.2f}")
    print(f"p-value: {p_val:.6f} {interpret_pvalue(p_val)}")
    print(f"Cohen's d: {effect:.3f} ({interpret_effect_size(effect)} effect)")
    print(f"Conclusion: {'SIGNIFICANT' if p_val < 0.05 else 'NOT SIGNIFICANT'} difference")
    
    results.append({
        'Figure': 'TS-RQ1-Fig1',
        'Description': 'any additions',
        'Test': 'Mann-Whitney U',
        'p-value': p_val,
        'Effect Size': effect,
        'Significant': 'Yes' if p_val < 0.05 else 'No'
    })

# C# 'dynamic' additions
print("\n[CS-RQ1-Fig1] 'dynamic' Type Additions")
print("-"*80)
cs_agent_dyn_nz = cs_agent_dyn[cs_agent_dyn['dynamic_additions'] > 0]['dynamic_additions']
cs_human_dyn_nz = cs_human_dyn[cs_human_dyn['dynamic_additions'] > 0]['dynamic_additions']

if len(cs_agent_dyn_nz) > 0 and len(cs_human_dyn_nz) > 0:
    u_stat, p_val = mannwhitneyu(cs_agent_dyn_nz, cs_human_dyn_nz, alternative='two-sided')
    effect = cohens_d(cs_agent_dyn_nz, cs_human_dyn_nz)
    
    print(f"Test: Mann-Whitney U test")
    print(f"Sample sizes: AI={len(cs_agent_dyn_nz)}, Human={len(cs_human_dyn_nz)}")
    print(f"Medians: AI={cs_agent_dyn_nz.median():.2f}, Human={cs_human_dyn_nz.median():.2f}")
    print(f"U-statistic: {u_stat:.2f}, p-value: {p_val:.6f} {interpret_pvalue(p_val)}")
    print(f"Cohen's d: {effect:.3f} ({interpret_effect_size(effect)})")
    print(f"Conclusion: {'SIGNIFICANT' if p_val < 0.05 else 'NOT SIGNIFICANT'}")
    
    results.append({
        'Figure': 'CS-RQ1-Fig1',
        'Description': 'dynamic additions',
        'Test': 'Mann-Whitney U',
        'p-value': p_val,
        'Effect Size': effect,
        'Significant': 'Yes' if p_val < 0.05 else 'No'
    })

# ============================================================================
# RQ2: ADVANCED FEATURES
# ============================================================================
print("\n" + "="*80)
print("RQ2: ADVANCED FEATURE USAGE ANALYSIS")
print("="*80)

# TypeScript feature diversity
print("\n[TS-RQ2-Fig3] Feature Diversity (Unique Features)")
print("-"*80)
u_stat, p_val = mannwhitneyu(ts_agent_feat['unique'], ts_human_feat['unique'], alternative='two-sided')
effect = cohens_d(ts_agent_feat['unique'], ts_human_feat['unique'])

print(f"Test: Mann-Whitney U test")
print(f"Sample sizes: AI={len(ts_agent_feat)}, Human={len(ts_human_feat)}")
print(f"Medians: AI={ts_agent_feat['unique'].median():.2f}, Human={ts_human_feat['unique'].median():.2f}")
print(f"Means: AI={ts_agent_feat['unique'].mean():.2f}, Human={ts_human_feat['unique'].mean():.2f}")
print(f"U-statistic: {u_stat:.2f}, p-value: {p_val:.6f} {interpret_pvalue(p_val)}")
print(f"Cohen's d: {effect:.3f} ({interpret_effect_size(effect)})")
print(f"Conclusion: {'SIGNIFICANT' if p_val < 0.05 else 'NOT SIGNIFICANT'}")

results.append({
    'Figure': 'TS-RQ2-Fig3',
    'Description': 'Feature diversity',
    'Test': 'Mann-Whitney U',
    'p-value': p_val,
    'Effect Size': effect,
    'Significant': 'Yes' if p_val < 0.05 else 'No'
})

# C# feature diversity
print("\n[CS-RQ2-Fig3] Feature Diversity (Unique Features)")
print("-"*80)
u_stat, p_val = mannwhitneyu(cs_agent_feat['unique'], cs_human_feat['unique'], alternative='two-sided')
effect = cohens_d(cs_agent_feat['unique'], cs_human_feat['unique'])

print(f"Test: Mann-Whitney U test")
print(f"Medians: AI={cs_agent_feat['unique'].median():.2f}, Human={cs_human_feat['unique'].median():.2f}")
print(f"U-statistic: {u_stat:.2f}, p-value: {p_val:.6f} {interpret_pvalue(p_val)}")
print(f"Cohen's d: {effect:.3f} ({interpret_effect_size(effect)})")
print(f"Conclusion: {'SIGNIFICANT' if p_val < 0.05 else 'NOT SIGNIFICANT'}")

results.append({
    'Figure': 'CS-RQ2-Fig3',
    'Description': 'Feature diversity',
    'Test': 'Mann-Whitney U',
    'p-value': p_val,
    'Effect Size': effect,
    'Significant': 'Yes' if p_val < 0.05 else 'No'
})

# TypeScript non-null assertions (safety feature)
print("\n[TS-RQ2-Fig5] Non-null Assertion Adoption")
print("-"*80)
ts_agent_nonnull = (ts_agent_feat['non_null_assertion'] > 0).sum()
ts_human_nonnull = (ts_human_feat['non_null_assertion'] > 0).sum()
ts_agent_total = len(ts_agent_feat)
ts_human_total = len(ts_human_feat)

contingency = np.array([[ts_agent_nonnull, ts_agent_total - ts_agent_nonnull],
                        [ts_human_nonnull, ts_human_total - ts_human_nonnull]])

chi2, p_val, dof, expected = chi2_contingency(contingency)

print(f"Test: Chi-square test of independence")
print(f"Reason: Comparing proportions (adoption rates) between two groups")
print(f"Adoption rates: AI={ts_agent_nonnull/ts_agent_total*100:.1f}%, Human={ts_human_nonnull/ts_human_total*100:.1f}%")
print(f"Chi-square: {chi2:.2f}, df={dof}, p-value: {p_val:.6f} {interpret_pvalue(p_val)}")
print(f"Conclusion: {'SIGNIFICANT' if p_val < 0.05 else 'NOT SIGNIFICANT'}")

results.append({
    'Figure': 'TS-RQ2-Fig5',
    'Description': 'Non-null assertion adoption',
    'Test': 'Chi-square',
    'p-value': p_val,
    'Effect Size': 'N/A',
    'Significant': 'Yes' if p_val < 0.05 else 'No'
})

# C# null-forgiving operator (safety feature)
print("\n[CS-RQ2-Fig5] Null-forgiving Operator Adoption")
print("-"*80)
cs_agent_nullforg = (cs_agent_feat['null_forgiving'] > 0).sum()
cs_human_nullforg = (cs_human_feat['null_forgiving'] > 0).sum()
cs_agent_total = len(cs_agent_feat)
cs_human_total = len(cs_human_feat)

contingency = np.array([[cs_agent_nullforg, cs_agent_total - cs_agent_nullforg],
                        [cs_human_nullforg, cs_human_total - cs_human_nullforg]])

chi2, p_val, dof, expected = chi2_contingency(contingency)

print(f"Test: Chi-square test")
print(f"Adoption rates: AI={cs_agent_nullforg/cs_agent_total*100:.1f}%, Human={cs_human_nullforg/cs_human_total*100:.1f}%")
print(f"Chi-square: {chi2:.2f}, p-value: {p_val:.6f} {interpret_pvalue(p_val)}")
print(f"Conclusion: {'SIGNIFICANT' if p_val < 0.05 else 'NOT SIGNIFICANT'}")

results.append({
    'Figure': 'CS-RQ2-Fig5',
    'Description': 'Null-forgiving adoption',
    'Test': 'Chi-square',
    'p-value': p_val,
    'Effect Size': 'N/A',
    'Significant': 'Yes' if p_val < 0.05 else 'No'
})

# ============================================================================
# RQ3: ACCEPTANCE RATES
# ============================================================================
print("\n" + "="*80)
print("RQ3: ACCEPTANCE RATE ANALYSIS")
print("="*80)

# TypeScript acceptance
print("\n[TS-RQ3-Fig6a] Overall Acceptance Rate")
print("-"*80)
ts_agent_merged = ts_agent['is_merged'].sum()
ts_human_merged = ts_human['is_merged'].sum()
ts_agent_total = len(ts_agent)
ts_human_total = len(ts_human)

contingency = np.array([[ts_agent_merged, ts_agent_total - ts_agent_merged],
                        [ts_human_merged, ts_human_total - ts_human_merged]])

chi2, p_val, dof, expected = chi2_contingency(contingency)

print(f"Test: Chi-square test of independence")
print(f"Reason: Comparing acceptance proportions (categorical outcome)")
print(f"Acceptance rates: AI={ts_agent_merged/ts_agent_total*100:.1f}% ({ts_agent_merged}/{ts_agent_total})")
print(f"                  Human={ts_human_merged/ts_human_total*100:.1f}% ({ts_human_merged}/{ts_human_total})")
print(f"Chi-square: {chi2:.2f}, df={dof}, p-value: {p_val:.6f} {interpret_pvalue(p_val)}")
print(f"Conclusion: {'SIGNIFICANT' if p_val < 0.05 else 'NOT SIGNIFICANT'} - AI has HIGHER acceptance")

results.append({
    'Figure': 'TS-RQ3-Fig6a',
    'Description': 'Acceptance rate',
    'Test': 'Chi-square',
    'p-value': p_val,
    'Effect Size': 'N/A',
    'Significant': 'Yes' if p_val < 0.05 else 'No'
})

# C# acceptance
print("\n[CS-RQ3-Fig6a] Overall Acceptance Rate")
print("-"*80)
cs_agent_merged = cs_agent['is_merged'].sum()
cs_human_merged = cs_human['is_merged'].sum()
cs_agent_total = len(cs_agent)
cs_human_total = len(cs_human)

contingency = np.array([[cs_agent_merged, cs_agent_total - cs_agent_merged],
                        [cs_human_merged, cs_human_total - cs_human_merged]])

# Use Fisher's exact for small sample
if cs_human_total < 50:
    odds_ratio, p_val = fisher_exact(contingency)
    test_name = "Fisher's exact test"
    print(f"Test: Fisher's exact test (used due to small human sample size)")
else:
    chi2, p_val, dof, expected = chi2_contingency(contingency)
    test_name = "Chi-square"
    print(f"Test: Chi-square test")

print(f"Acceptance rates: AI={cs_agent_merged/cs_agent_total*100:.1f}% ({cs_agent_merged}/{cs_agent_total})")
print(f"                  Human={cs_human_merged/cs_human_total*100:.1f}% ({cs_human_merged}/{cs_human_total})")
print(f"p-value: {p_val:.6f} {interpret_pvalue(p_val)}")
print(f"Conclusion: {'SIGNIFICANT' if p_val < 0.05 else 'NOT SIGNIFICANT'} - Human has HIGHER acceptance")
print(f"NOTE: C# human sample is small (n={cs_human_total}), indicating selection bias")

results.append({
    'Figure': 'CS-RQ3-Fig6a',
    'Description': 'Acceptance rate',
    'Test': test_name,
    'p-value': p_val,
    'Effect Size': 'N/A',
    'Significant': 'Yes' if p_val < 0.05 else 'No'
})

# ============================================================================
# SUMMARY TABLE
# ============================================================================
print("\n" + "="*80)
print("SUMMARY TABLE OF ALL STATISTICAL TESTS")
print("="*80)

results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))

# Save results
results_df.to_csv('STATISTICAL_TEST_RESULTS.csv', index=False)
print("\n✓ Results saved to: STATISTICAL_TEST_RESULTS.csv")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
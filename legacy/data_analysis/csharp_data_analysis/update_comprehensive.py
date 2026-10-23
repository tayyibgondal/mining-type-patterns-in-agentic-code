"""
Update C# analysis to match TypeScript format exactly
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import warnings
warnings.filterwarnings('ignore')

# Large fonts for readability
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 16
plt.rcParams['axes.titlesize'] = 20
plt.rcParams['axes.labelsize'] = 18
plt.rcParams['xtick.labelsize'] = 16
plt.rcParams['ytick.labelsize'] = 16
plt.rcParams['legend.fontsize'] = 16

COLOR_AI = '#E74C3C'
COLOR_HUMAN = '#3498DB'

# Load data
BASE = '/Users/tayyibgondal/Desktop/typescript-type-analysis'
agent_df = pd.read_csv(f'{BASE}/csharp_data/agent_type_prs_filtered_by_open_ai.csv')
agent_df = agent_df[agent_df['final_is_type_related'] == True]

human_df = pd.read_csv(f'{BASE}/csharp_data/human_type_prs_filtered_by_open_ai.csv')
human_df = human_df[human_df['final_is_type_related'] == True]

print(f"Loaded: AI={len(agent_df)}, Human={len(human_df)}")

# Extract features for safety graph
def extract_features(df):
    features = []
    
    # C# Safety features
    patterns = {
        'null_forgiving': r'![\.\[\(]',  # ! operator
        'nullable_types': r'\w+\?(?!\?)',  # T?
        'pattern_matching': r'\bis\s+(?:not\s+)?(?:\w+|\{)',  # is checks
        'null_coalescing': r'\?\?',  # ?? operator
        'null_conditional': r'\?\.',  # ?. operator
    }
    
    for _, row in df.iterrows():
        patch = str(row.get('patch_text', ''))
        added = '\n'.join([l for l in patch.split('\n') if l.startswith('+')])
        
        counts = {}
        for name, pattern in patterns.items():
            counts[name] = len(re.findall(pattern, added, re.IGNORECASE))
        
        counts['has_null_forgiving'] = counts['null_forgiving'] > 0
        counts['has_nullable'] = counts['nullable_types'] > 0
        counts['has_pattern_matching'] = counts['pattern_matching'] > 0
        counts['has_null_coalescing'] = counts['null_coalescing'] > 0
        counts['has_null_conditional'] = counts['null_conditional'] > 0
        
        features.append(counts)
    
    return pd.DataFrame(features)

agent_feat = extract_features(agent_df)
human_feat = extract_features(human_df)

# Generate Fig5: Safety Features
fig, ax = plt.subplots(figsize=(10, 6))

safety_features = {
    'Null-Forgiving (!)': 'has_null_forgiving',
    'Nullable Types (?)': 'has_nullable',
    'Pattern Matching': 'has_pattern_matching',
    'Null Coalescing (??)': 'has_null_coalescing',
    'Null Conditional (?.)': 'has_null_conditional'
}

agent_safety = []
human_safety = []
feature_names = []

for name, col in safety_features.items():
    agent_safety.append(agent_feat[col].mean() * 100)
    human_safety.append(human_feat[col].mean() * 100)
    feature_names.append(name)

x = np.arange(len(feature_names))
width = 0.35

bars1 = ax.bar(x - width/2, agent_safety, width, label='AI Agent',
               color=COLOR_AI, alpha=0.85, edgecolor='black', linewidth=1.5)
bars2 = ax.bar(x + width/2, human_safety, width, label='Human',
               color=COLOR_HUMAN, alpha=0.85, edgecolor='black', linewidth=1.5)

ax.set_xlabel('Type Safety Feature', fontweight='bold')
ax.set_ylabel('Adoption Rate (% of PRs)', fontweight='bold')
ax.set_title('C#: Type Safety Feature Adoption Patterns', fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(feature_names, fontweight='bold', rotation=20, ha='right', fontsize=14)
ax.legend(loc='upper right', frameon=True, shadow=True)
ax.grid(True, alpha=0.3, axis='y')

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2., h,
                   f'{h:.1f}%', ha='center', va='bottom',
                   fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig('final_figures/fig5_rq2_safety_features.png', bbox_inches='tight', dpi=300)
plt.close()
print("✓ Generated: fig5_rq2_safety_features.png")

# Update Fig6a: Add Merged/Closed/Open breakdown
fig, ax = plt.subplots(figsize=(10, 6))

# Calculate all three states
agent_merged = (agent_df['merged_at'].notna()).sum()
agent_closed = ((agent_df['state'].str.lower() == 'closed') & (agent_df['merged_at'].isna())).sum()
agent_open = (agent_df['state'].str.lower() == 'open').sum()

human_merged = (human_df['merged_at'].notna()).sum()
human_closed = ((human_df['state'].str.lower() == 'closed') & (human_df['merged_at'].isna())).sum()
human_open = (human_df['state'].str.lower() == 'open').sum()

agent_merged_pct = agent_merged / len(agent_df) * 100
agent_closed_pct = agent_closed / len(agent_df) * 100
agent_open_pct = agent_open / len(agent_df) * 100

human_merged_pct = human_merged / len(human_df) * 100
human_closed_pct = human_closed / len(human_df) * 100
human_open_pct = human_open / len(human_df) * 100

categories = ['Merged\n(Accepted)', 'Closed\n(Rejected)', 'Open\n(Pending)']
agent_vals = [agent_merged_pct, agent_closed_pct, agent_open_pct]
human_vals = [human_merged_pct, human_closed_pct, human_open_pct]

x = np.arange(len(categories))
width = 0.35

bars1 = ax.bar(x - width/2, agent_vals, width, label='AI Agent',
               color=COLOR_AI, alpha=0.85, edgecolor='black', linewidth=1.5)
bars2 = ax.bar(x + width/2, human_vals, width, label='Human',
               color=COLOR_HUMAN, alpha=0.85, edgecolor='black', linewidth=1.5)

ax.set_xlabel('PR Status', fontweight='bold')
ax.set_ylabel('Percentage of PRs (%)', fontweight='bold')
ax.set_title('C#: Pull Request Acceptance Rates in Type-Related Issues', fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontweight='bold')
ax.legend(loc='upper right', frameon=True, shadow=True)
ax.grid(True, alpha=0.3, axis='y')
ax.set_ylim(0, 110)

# Value labels
for bars in [bars1, bars2]:
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h,
               f'{h:.1f}%', ha='center', va='bottom',
               fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig('final_figures/fig6a_rq3_acceptance.png', bbox_inches='tight', dpi=300)
plt.close()
print("✓ Updated: fig6a_rq3_acceptance.png (with Merged/Closed/Open)")

print("\n" + "=" * 60)
print("C# Figures Updated to Match TypeScript Format!")
print("=" * 60)

print(f"\nC# Breakdown:")
print(f"  AI: Merged={agent_merged_pct:.1f}%, Closed={agent_closed_pct:.1f}%, Open={agent_open_pct:.1f}%")
print(f"  Human: Merged={human_merged_pct:.1f}%, Closed={human_closed_pct:.1f}%, Open={human_open_pct:.1f}%")


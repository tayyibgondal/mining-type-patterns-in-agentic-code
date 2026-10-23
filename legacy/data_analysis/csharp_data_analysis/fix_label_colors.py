"""
Fix label colors - make all labels black
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import warnings
warnings.filterwarnings('ignore')

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

BASE = '/Users/tayyibgondal/Desktop/typescript-type-analysis'
agent_df = pd.read_csv(f'{BASE}/csharp_data/agent_type_prs_filtered_by_open_ai.csv')
agent_df = agent_df[agent_df['final_is_type_related'] == True]

human_df = pd.read_csv(f'{BASE}/csharp_data/human_type_prs_filtered_by_open_ai.csv')
human_df = human_df[human_df['final_is_type_related'] == True]

def extract_features(df):
    features = []
    patterns = {
        'null_forgiving': r'![\.\[\(]',
        'nullable_types': r'\w+\?(?!\?)',
        'pattern_matching': r'\bis\s+(?:not\s+)?(?:\w+|\{)',
        'null_coalescing': r'\?\?',
        'null_conditional': r'\?\.',
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

fig, ax = plt.subplots(figsize=(10, 6))

safety_features = {
    'Null-Forgiving (!)': 'has_null_forgiving',
    'Nullable Types (?)': 'has_nullable',
    'Pattern Matching': 'has_pattern_matching',
    'Null Coalescing (??)': 'has_null_coalescing',
    'Null Conditional (?.)': 'has_null_conditional'
}

agent_safety = [agent_feat[col].mean() * 100 for col in safety_features.values()]
human_safety = [human_feat[col].mean() * 100 for col in safety_features.values()]
feature_names = list(safety_features.keys())

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
ax.set_ylim(0, 80)

# FIXED: All labels in BLACK with smart positioning
for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
    h1 = bar1.get_height()
    h2 = bar2.get_height()
    
    # AI Agent label
    if h1 > 2:
        if abs(h1 - h2) < 8:  # Close bars - offset slightly
            ax.text(bar1.get_x() + bar1.get_width()/2., h1 + 1.5,
                   f'{h1:.1f}%', ha='center', va='bottom',
                   fontsize=12, fontweight='bold', color='black')
        else:
            ax.text(bar1.get_x() + bar1.get_width()/2., h1,
                   f'{h1:.1f}%', ha='center', va='bottom',
                   fontsize=13, fontweight='bold', color='black')
    
    # Human label  
    if h2 > 2:
        if abs(h1 - h2) < 8:  # Close bars - offset slightly
            ax.text(bar2.get_x() + bar2.get_width()/2., h2 + 1.5,
                   f'{h2:.1f}%', ha='center', va='bottom',
                   fontsize=12, fontweight='bold', color='black')
        else:
            ax.text(bar2.get_x() + bar2.get_width()/2., h2,
                   f'{h2:.1f}%', ha='center', va='bottom',
                   fontsize=13, fontweight='bold', color='black')

plt.tight_layout()
plt.savefig('final_figures/fig5_rq2_safety_features.png', bbox_inches='tight', dpi=300)
plt.close()
print("✓ Fixed: All labels now BLACK")


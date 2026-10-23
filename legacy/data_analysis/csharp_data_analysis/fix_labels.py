"""
Fix overlapping labels in C# safety features graph
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import warnings
warnings.filterwarnings('ignore')

# Large fonts
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

# Fig5: Safety Features with FIXED LABELS
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
ax.set_ylim(0, 80)  # Set limit to prevent cramping

# FIXED: Smart label placement to avoid overlap
for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
    h1 = bar1.get_height()
    h2 = bar2.get_height()
    
    # AI Agent label
    if h1 > 5:  # Only show if bar is visible
        # Check if labels would overlap
        if abs(h1 - h2) < 8:  # If bars are close
            # Place AI label higher with offset
            ax.text(bar1.get_x() + bar1.get_width()/2., h1 + 2,
                   f'{h1:.1f}%', ha='center', va='bottom',
                   fontsize=12, fontweight='bold', color='#C0392B')
        else:
            ax.text(bar1.get_x() + bar1.get_width()/2., h1,
                   f'{h1:.1f}%', ha='center', va='bottom',
                   fontsize=13, fontweight='bold')
    
    # Human label
    if h2 > 5:  # Only show if bar is visible
        if abs(h1 - h2) < 8:  # If bars are close
            # Place human label with offset
            ax.text(bar2.get_x() + bar2.get_width()/2., h2 + 2,
                   f'{h2:.1f}%', ha='center', va='bottom',
                   fontsize=12, fontweight='bold', color='#2874A6')
        else:
            ax.text(bar2.get_x() + bar2.get_width()/2., h2,
                   f'{h2:.1f}%', ha='center', va='bottom',
                   fontsize=13, fontweight='bold')

plt.tight_layout()
plt.savefig('final_figures/fig5_rq2_safety_features.png', bbox_inches='tight', dpi=300)
plt.close()
print("✓ Fixed: fig5_rq2_safety_features.png (no overlapping labels)")


"""
Comprehensive C# Analysis for All Research Questions
Generates all figures for RQ1, RQ2, and RQ3
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import re
import warnings
import os
warnings.filterwarnings('ignore')

# Setup
BASE_PATH = '/Users/tayyibgondal/Desktop/typescript-type-analysis'
plt.style.use('seaborn-v0_8-whitegrid')
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

# C# Advanced Features (from extraction script)
CSHARP_FEATURES = {
    'generics': r'<[^<>]+>',
    'nullable': r'\w+\?(?!\?)',
    'null_forgiving': r'![\.\[\(]',
    'var_keyword': r'\bvar\s+\w+',
    'dynamic_keyword': r'\bdynamic\s+\w+',
    'record': r'\brecord\s+(?:class|struct)?\s*\w+',
    'init': r'\binit\s*;',
    'pattern_matching': r'\bis\s+(?:not\s+)?(?:\w+|\{)',
    'switch_expression': r'=>',
    'tuple': r'\([^)]*,\s*[^)]*\)',
    'readonly_struct': r'\breadonly\s+struct',
    'ref_struct': r'\bref\s+struct',
    'in_parameter': r'\bin\s+\w+',
    'out_parameter': r'\bout\s+\w+',
    'ref_parameter': r'\bref\s+\w+',
    'async_await': r'\b(?:async|await)\b',
    'linq': r'\b(?:from|where|select|join|group)\s+\w+'
}

def load_data():
    agent_df = pd.read_csv(f'{BASE_PATH}/csharp_data/agent_type_prs_filtered_by_open_ai.csv')
    agent_df = agent_df[agent_df['final_is_type_related'] == True]
    
    human_df = pd.read_csv(f'{BASE_PATH}/csharp_data/human_type_prs_filtered_by_open_ai.csv')
    human_df = human_df[human_df['final_is_type_related'] == True]
    
    print(f"C# Type-Related PRs: AI={len(agent_df)}, Human={len(human_df)}")
    return agent_df, human_df

def extract_dynamic(df):
    """RQ1: Extract dynamic type metrics"""
    metrics = []
    pattern = r'\bdynamic\s+\w+|\bdynamic\>|:\s*dynamic\b|<dynamic>'
    
    for _, row in df.iterrows():
        patch = str(row.get('patch_text', ''))
        adds, rems = 0, 0
        
        for line in patch.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                adds += len(re.findall(pattern, line, re.IGNORECASE))
            elif line.startswith('-') and not line.startswith('---'):
                rems += len(re.findall(pattern, line, re.IGNORECASE))
        
        metrics.append({
            'id': row['id'],
            'agent': row.get('agent', 'Human'),
            'dynamic_additions': adds,
            'dynamic_removals': rems,
            'net_change': adds - rems,
            'total_ops': adds + rems
        })
    
    return pd.DataFrame(metrics)

def extract_features(df):
    """RQ2: Extract advanced C# features"""
    features = []
    
    for _, row in df.iterrows():
        patch = str(row.get('patch_text', ''))
        added_lines = '\n'.join([l for l in patch.split('\n') if l.startswith('+')])
        
        counts = {}
        for name, pattern in CSHARP_FEATURES.items():
            counts[name] = len(re.findall(pattern, added_lines, re.IGNORECASE))
        
        counts['id'] = row['id']
        counts['agent'] = row.get('agent', 'Human')
        counts['total_features'] = sum(v for k, v in counts.items() if k not in ['id', 'agent'])
        counts['unique_features'] = sum(1 for k, v in counts.items() if k not in ['id', 'agent', 'total_features'] and v > 0)
        
        features.append(counts)
    
    return pd.DataFrame(features)

def generate_rq1_figures(agent_dyn, human_dyn):
    """Generate RQ1 figures for dynamic type"""
    os.makedirs('final_figures', exist_ok=True)
    
    # Fig 1: Dynamic additions
    fig, ax = plt.subplots(figsize=(8, 6))
    
    agent_adds = agent_dyn[agent_dyn['dynamic_additions'] > 0]['dynamic_additions']
    human_adds = human_dyn[human_dyn['dynamic_additions'] > 0]['dynamic_additions']
    
    if len(agent_adds) > 0 and len(human_adds) > 0:
        bp = ax.boxplot([agent_adds, human_adds], labels=['AI Agent', 'Human'],
                        patch_artist=True, showmeans=True)
        for patch, color in zip(bp['boxes'], [COLOR_AI, COLOR_HUMAN]):
            patch.set_facecolor(color)
            patch.set_alpha(0.85)
        
        ax.set_ylabel('"dynamic" Additions per PR', fontweight='bold')
        ax.set_xlabel('Developer Type', fontweight='bold')
        ax.set_title('C#: "dynamic" Type Additions', fontweight='bold', pad=20)
        ax.set_yscale('log')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('final_figures/fig1_rq1_dynamic_additions.png', bbox_inches='tight', dpi=300)
        plt.close()
        print("✓ Generated: fig1_rq1_dynamic_additions.png")
    else:
        print("⚠ Insufficient data for dynamic additions plot")
    
    # Fig 2: Agent breakdown
    fig, ax = plt.subplots(figsize=(10, 6))
    
    breakdown = agent_dyn.groupby('agent').agg({
        'dynamic_additions': 'sum',
        'dynamic_removals': 'sum'
    }).reset_index()
    
    if len(breakdown) > 0:
        x = np.arange(len(breakdown))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, breakdown['dynamic_additions'], width,
                      label='"dynamic" Additions', color='#E74C3C', alpha=0.85,
                      edgecolor='black', linewidth=1.5)
        bars2 = ax.bar(x + width/2, breakdown['dynamic_removals'], width,
                      label='"dynamic" Removals', color='#27AE60', alpha=0.85,
                      edgecolor='black', linewidth=1.5)
        
        ax.set_xlabel('AI Agent', fontweight='bold')
        ax.set_ylabel('Total "dynamic" Operations', fontweight='bold')
        ax.set_title('C#: "dynamic" Operations by Agent', fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(breakdown['agent'], fontweight='bold')
        ax.legend(loc='upper right', frameon=True, shadow=True)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., h,
                           f'{int(h)}', ha='center', va='bottom', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('final_figures/fig2_rq1_agent_breakdown.png', bbox_inches='tight', dpi=300)
        plt.close()
        print("✓ Generated: fig2_rq1_agent_breakdown.png")

def generate_rq2_figures(agent_feat, human_feat):
    """Generate RQ2 figures for advanced features"""
    
    # Fig 3: Feature diversity
    fig, ax = plt.subplots(figsize=(10, 6))
    
    agents = agent_feat['agent'].unique()
    diversity = []
    names = []
    
    for agent in agents:
        if agent != 'Human':
            mean_unique = agent_feat[agent_feat['agent'] == agent]['unique_features'].mean()
            diversity.append(mean_unique)
            names.append(agent)
    
    diversity.append(human_feat['unique_features'].mean())
    names.append('Human')
    
    colors = ['#E74C3C', '#9B59B6', '#3498DB', '#F39C12']
    bars = ax.bar(range(len(names)), diversity, color=colors, alpha=0.85,
                  edgecolor='black', linewidth=1.5)
    
    ax.set_xlabel('Developer/Agent', fontweight='bold')
    ax.set_ylabel('Mean Unique Features', fontweight='bold')
    ax.set_title('C#: Feature Diversity by Agent', fontweight='bold', pad=20)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, fontweight='bold', rotation=15, ha='right')
    ax.grid(True, alpha=0.3, axis='y')
    
    for bar, val in zip(bars, diversity):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
               f'{val:.2f}', ha='center', va='bottom', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('final_figures/fig3_rq2_feature_diversity.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("✓ Generated: fig3_rq2_feature_diversity.png")
    
    # Fig 4: Feature usage
    fig, ax = plt.subplots(figsize=(10, 8))
    
    top_features = ['generics', 'nullable', 'pattern_matching', 'async_await',
                    'linq', 'var_keyword', 'tuple', 'switch_expression']
    
    agent_means = [agent_feat[f].mean() for f in top_features if f in agent_feat.columns]
    human_means = [human_feat[f].mean() for f in top_features if f in human_feat.columns]
    labels = [f.replace('_', ' ').title() for f in top_features]
    
    y = np.arange(len(labels))
    height = 0.35
    
    bars1 = ax.barh(y + height/2, agent_means, height, label='AI Agent',
                    color=COLOR_AI, alpha=0.85, edgecolor='black', linewidth=1.5)
    bars2 = ax.barh(y - height/2, human_means, height, label='Human',
                    color=COLOR_HUMAN, alpha=0.85, edgecolor='black', linewidth=1.5)
    
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontweight='bold')
    ax.set_xlabel('Mean Usage per PR', fontweight='bold')
    ax.set_title('C#: Advanced Feature Usage', fontweight='bold', pad=20)
    ax.legend(loc='upper right', frameon=True, shadow=True)
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    plt.savefig('final_figures/fig4_rq2_feature_usage.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("✓ Generated: fig4_rq2_feature_usage.png")

def generate_rq3_figures(agent_df, human_df):
    """Generate RQ3 figures for acceptance rates"""
    
    # Fig 6a: Overall acceptance
    fig, ax = plt.subplots(figsize=(8, 6))
    
    agent_merged = (agent_df['merged_at'].notna()).sum()
    human_merged = (human_df['merged_at'].notna()).sum()
    
    agent_pct = agent_merged / len(agent_df) * 100
    human_pct = human_merged / len(human_df) * 100
    
    categories = ['Merged']
    agent_vals = [agent_pct]
    human_vals = [human_pct]
    
    x = np.arange(len(categories))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, agent_vals, width, label='AI Agent',
                   color=COLOR_AI, alpha=0.85, edgecolor='black', linewidth=1.5)
    bars2 = ax.bar(x + width/2, human_vals, width, label='Human',
                   color=COLOR_HUMAN, alpha=0.85, edgecolor='black', linewidth=1.5)
    
    ax.set_ylabel('Acceptance Rate (%)', fontweight='bold')
    ax.set_xlabel('PR Status', fontweight='bold')
    ax.set_title('C#: PR Acceptance Rates', fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontweight='bold')
    ax.legend(loc='upper right', frameon=True, shadow=True)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, 110)
    
    for bars in [bars1, bars2]:
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                   f'{bar.get_height():.1f}%', ha='center', va='bottom',
                   fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('final_figures/fig6a_rq3_acceptance.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("✓ Generated: fig6a_rq3_acceptance.png")
    
    # Fig 6b: By agent
    fig, ax = plt.subplots(figsize=(10, 6))
    
    agent_acc = agent_df.groupby('agent').apply(
        lambda x: (x['merged_at'].notna()).mean() * 100
    ).reset_index(name='rate')
    
    agents = list(agent_acc['agent'])
    rates = list(agent_acc['rate'])
    agents.append('Human')
    rates.append(human_pct)
    
    colors = ['#E74C3C', '#9B59B6', '#3498DB', '#F39C12']
    bars = ax.bar(range(len(agents)), rates, color=colors, alpha=0.85,
                  edgecolor='black', linewidth=1.5)
    
    ax.set_xlabel('Developer/Agent', fontweight='bold')
    ax.set_ylabel('Acceptance Rate (%)', fontweight='bold')
    ax.set_title('C#: Acceptance by Agent', fontweight='bold', pad=20)
    ax.set_xticks(range(len(agents)))
    ax.set_xticklabels(agents, fontweight='bold', rotation=15, ha='right')
    ax.grid(True, alpha=0.3, axis='y')
    
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
               f'{bar.get_height():.1f}%', ha='center', va='bottom',
               fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('final_figures/fig6b_rq3_by_agent.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("✓ Generated: fig6b_rq3_by_agent.png")

def main():
    print("=" * 70)
    print("COMPREHENSIVE C# ANALYSIS - All Research Questions")
    print("=" * 70)
    
    # Load
    agent_df, human_df = load_data()
    
    # RQ1
    print("\n[RQ1] Analyzing 'dynamic' type...")
    agent_dyn = extract_dynamic(agent_df)
    human_dyn = extract_dynamic(human_df)
    
    agent_with_dyn = (agent_dyn['total_ops'] > 0).sum()
    human_with_dyn = (human_dyn['total_ops'] > 0).sum()
    print(f"  PRs with 'dynamic': AI={agent_with_dyn} ({agent_with_dyn/len(agent_dyn)*100:.1f}%), Human={human_with_dyn} ({human_with_dyn/len(human_dyn)*100:.1f}%)")
    
    generate_rq1_figures(agent_dyn, human_dyn)
    agent_dyn.to_csv('final_figures/agent_dynamic.csv', index=False)
    
    # RQ2
    print("\n[RQ2] Extracting advanced C# features...")
    agent_feat = extract_features(agent_df)
    human_feat = extract_features(human_df)
    print(f"  Mean features: AI={agent_feat['total_features'].mean():.1f}, Human={human_feat['total_features'].mean():.1f}")
    
    generate_rq2_figures(agent_feat, human_feat)
    agent_feat.to_csv('final_figures/agent_features.csv', index=False)
    
    # RQ3
    print("\n[RQ3] Analyzing acceptance rates...")
    agent_merged = (agent_df['merged_at'].notna()).sum()
    human_merged = (human_df['merged_at'].notna()).sum()
    print(f"  Acceptance: AI={agent_merged/len(agent_df)*100:.1f}%, Human={human_merged/len(human_df)*100:.1f}%")
    
    generate_rq3_figures(agent_df, human_df)
    
    print("\n" + "=" * 70)
    print("COMPLETE! All C# figures in final_figures/")
    print("=" * 70)

if __name__ == "__main__":
    main()

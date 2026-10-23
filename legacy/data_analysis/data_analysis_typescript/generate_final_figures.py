"""
Generate Final Publication-Ready Figures for Research Paper

This script generates only the selected figures needed for the paper,
each as a standalone, beautiful visualization with striking colors.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import re
import warnings
warnings.filterwarnings('ignore')

# Set publication-quality style with striking colors and LARGE fonts
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 16
plt.rcParams['axes.titlesize'] = 20
plt.rcParams['axes.labelsize'] = 18
plt.rcParams['xtick.labelsize'] = 16
plt.rcParams['ytick.labelsize'] = 16
plt.rcParams['legend.fontsize'] = 16
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']

# Striking color palette
COLOR_AI = '#E74C3C'  # Vibrant red
COLOR_HUMAN = '#3498DB'  # Vibrant blue
COLOR_IMPROVE = '#27AE60'  # Green
COLOR_REDUCE = '#E74C3C'  # Red
COLOR_NEUTRAL = '#F39C12'  # Orange

def load_data():
    """Load all necessary data"""
    # Load agent data
    agent_df = pd.read_csv('../data/agent_type_prs_filtered_by_open_ai.csv')
    agent_df['developer_type'] = 'AI Agent'
    
    # Load human data
    human_df = pd.read_csv('../human_type_prs_filtered_by_open_ai.csv')
    human_df['developer_type'] = 'Human'
    
    # Filter for type-related PRs only
    agent_df = agent_df[agent_df['final_is_type_related'] == True]
    human_df = human_df[human_df['final_is_type_related'] == True]
    
    print(f"Loaded - AI Agents: {len(agent_df)}, Humans: {len(human_df)}")
    
    return agent_df, human_df

def extract_any_metrics(df):
    """Extract 'any' type usage metrics from patch text"""
    metrics = []
    
    for idx, row in df.iterrows():
        patch = str(row.get('patch_text', ''))
        
        # Look for TypeScript 'any' type annotations
        type_any_pattern = r':\s*any[\s,;>\)\|&]|<any>|as\s+any|\|\s*any|&\s*any|Array<any>|Promise<any>|Record<\w+,\s*any>|Record<any'
        
        any_additions = 0
        any_removals = 0
        
        lines = patch.split('\n')
        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                matches = re.findall(type_any_pattern, line)
                any_additions += len(matches)
            elif line.startswith('-') and not line.startswith('---'):
                matches = re.findall(type_any_pattern, line)
                any_removals += len(matches)
        
        metrics.append({
            'id': row['id'],
            'developer_type': row['developer_type'],
            'agent': row.get('agent', 'Human'),
            'any_additions': any_additions,
            'any_removals': any_removals,
            'net_any_change': any_additions - any_removals,
            'total_any_operations': any_additions + any_removals
        })
    
    return pd.DataFrame(metrics)

def extract_advanced_features(df):
    """Extract advanced TypeScript feature usage"""
    ADVANCED_FEATURES = {
        'generics': r'<[A-Z]\w*(?:\s+extends\s+[^>]+)?(?:,\s*[A-Z]\w*(?:\s+extends\s+[^>]+)?)*>',
        'conditional_types': r'\s+extends\s+.*\s+\?\s+.*\s+:\s+',
        'mapped_types': r'\[\s*(?:K|P|T)\s+in\s+(?:keyof\s+)?[^\]]+\]',
        'template_literals': r'`[^`]*\$\{[^}]+\}[^`]*`',
        'utility_types': r'\b(?:Partial|Required|Readonly|Record|Pick|Omit|Exclude|Extract|NonNullable|Parameters|ConstructorParameters|ReturnType|InstanceType)\s*<',
        'type_guards': r'\b(?:is|asserts)\s+\w+',
        'satisfies': r'\bsatisfies\s+',
        'as_const': r'\bas\s+const\b',
        'non_null_assertion': r'!\.',
        'keyof_typeof': r'\b(?:keyof|typeof)\s+',
        'indexed_access': r'\[\s*(?:number|string|symbol)\s*\]',
        'discriminated_unions': r'(?:type|interface)\s+\w+\s*=\s*(?:\{[^}]*\|\s*[^}]*\}|\w+\s*\|\s*\w+)',
        'intersection_types': r'&\s*\w+',
        'union_types': r'\|\s*\w+',
        'type_predicates': r':\s*\w+\s+is\s+\w+',
        'infer_keyword': r'\binfer\s+\w+',
        'namespace_types': r'namespace\s+\w+\s*\{',
        'enum_types': r'\benum\s+\w+\s*\{',
        'abstract_classes': r'\babstract\s+class\s+',
        'decorators': r'@\w+(?:\([^)]*\))?',
        'type_assertions': r'\bas\s+\w+',
        'optional_chaining': r'\?\.',
        'nullish_coalescing': r'\?\?'
    }
    
    features_list = []
    
    for idx, row in df.iterrows():
        patch = str(row.get('patch_text', ''))
        
        feature_counts = {}
        for feature_name, pattern in ADVANCED_FEATURES.items():
            try:
                added_lines = [line for line in patch.split('\n') if line.startswith('+')]
                added_text = '\n'.join(added_lines)
                matches = re.findall(pattern, added_text, re.IGNORECASE)
                feature_counts[feature_name] = len(matches)
            except:
                feature_counts[feature_name] = 0
        
        total_features = sum(feature_counts.values())
        unique_features = sum(1 for v in feature_counts.values() if v > 0)
        
        feature_counts['id'] = row['id']
        feature_counts['developer_type'] = row['developer_type']
        feature_counts['agent'] = row.get('agent', 'Human')
        feature_counts['total_advanced_features'] = total_features
        feature_counts['unique_features_used'] = unique_features
        feature_counts['additions'] = row.get('additions', 0)
        feature_counts['changes'] = row.get('changes', 0)
        
        if feature_counts['changes'] > 0:
            feature_counts['feature_density'] = (total_features / feature_counts['changes']) * 100
        else:
            feature_counts['feature_density'] = 0
        
        features_list.append(feature_counts)
    
    return pd.DataFrame(features_list)

def calculate_acceptance_metrics(df):
    """Calculate acceptance-related metrics"""
    metrics = {}
    
    total_prs = len(df)
    merged_prs = df['merged_at'].notna().sum()
    closed_prs = ((df['state'].str.lower() == 'closed') & (df['merged_at'].isna())).sum()
    open_prs = df['state'].str.lower().eq('open').sum()
    
    metrics['total_prs'] = total_prs
    metrics['merged_count'] = merged_prs
    metrics['closed_count'] = closed_prs
    metrics['open_count'] = open_prs
    metrics['acceptance_rate'] = (merged_prs / total_prs * 100) if total_prs > 0 else 0
    metrics['rejection_rate'] = (closed_prs / total_prs * 100) if total_prs > 0 else 0
    metrics['pending_rate'] = (open_prs / total_prs * 100) if total_prs > 0 else 0
    
    return metrics

# ==================== FIGURE 1: RQ1 - Any Type Additions ====================
def figure_rq1_any_additions(agent_metrics, human_metrics):
    """RQ1 Figure 1: Any Type Additions Comparison"""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Filter non-zero values
    agent_adds = agent_metrics['any_additions'][agent_metrics['any_additions'] > 0]
    human_adds = human_metrics['any_additions'][human_metrics['any_additions'] > 0]
    
    bp = ax.boxplot([agent_adds, human_adds],
                    labels=['AI Agent', 'Human Developer'],
                    patch_artist=True,
                    showmeans=True,
                    widths=0.6,
                    medianprops=dict(color='black', linewidth=2),
                    meanprops=dict(marker='D', markerfacecolor='yellow', 
                                  markeredgecolor='black', markersize=8))
    
    # Striking colors
    colors = [COLOR_AI, COLOR_HUMAN]
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
        patch.set_edgecolor('black')
        patch.set_linewidth(1.5)
    
    ax.set_ylabel('Number of "any" Type Additions per PR', fontsize=18, fontweight='bold')
    ax.set_xlabel('Developer Type', fontsize=18, fontweight='bold')
    ax.set_title('Impact of "any" Type Additions on Type Safety', 
                 fontsize=20, fontweight='bold', pad=20)
    ax.set_yscale('log')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plt.savefig('final_figures/fig1_rq1_any_additions.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("✓ Generated: fig1_rq1_any_additions.png")

# ==================== FIGURE 2: RQ1 - Any Operations by Agent ====================
def figure_rq1_agent_breakdown(agent_metrics):
    """RQ1 Figure 2: Any Operations by AI Agent"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    agent_breakdown = agent_metrics.groupby('agent').agg({
        'any_additions': 'sum',
        'any_removals': 'sum'
    }).reset_index()
    
    agents = agent_breakdown['agent']
    additions = agent_breakdown['any_additions']
    removals = agent_breakdown['any_removals']
    
    x = np.arange(len(agents))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, additions, width, label='"any" Additions',
                   color='#E74C3C', alpha=0.85, edgecolor='black', linewidth=1.5)
    bars2 = ax.bar(x + width/2, removals, width, label='"any" Removals',
                   color='#27AE60', alpha=0.85, edgecolor='black', linewidth=1.5)
    
    ax.set_xlabel('AI Agent Type', fontsize=18, fontweight='bold')
    ax.set_ylabel('Total "any" Type Operations', fontsize=18, fontweight='bold')
    ax.set_title('"any" Type Modifications by AI Agent', fontsize=20, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(agents, fontsize=16, fontweight='bold')
    ax.legend(fontsize=16, frameon=True, fancybox=True, shadow=True, loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}', ha='center', va='bottom',
                       fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('final_figures/fig2_rq1_agent_breakdown.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("✓ Generated: fig2_rq1_agent_breakdown.png")

# ==================== FIGURE 3: RQ2 - Feature Diversity by Agent ====================
def figure_rq2_feature_diversity(agent_features, human_features):
    """RQ2 Figure 3: Feature Diversity by Agent"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Get unique agents
    ai_agents = agent_features['agent'].unique()
    ai_agents = [a for a in ai_agents if a != 'Human']
    
    diversity_means = []
    diversity_stds = []
    agent_names = []
    
    for agent in ai_agents:
        agent_data = agent_features[agent_features['agent'] == agent]['unique_features_used']
        diversity_means.append(agent_data.mean())
        diversity_stds.append(agent_data.std())
        agent_names.append(agent)
    
    # Add human
    diversity_means.append(human_features['unique_features_used'].mean())
    diversity_stds.append(human_features['unique_features_used'].std())
    agent_names.append('Human')
    
    x = np.arange(len(agent_names))
    
    # Create gradient colors
    colors_agents = ['#E74C3C', '#9B59B6', '#3498DB', '#1ABC9C']
    colors_all = colors_agents + ['#F39C12']
    
    bars = ax.bar(x, diversity_means, yerr=diversity_stds, 
                  color=colors_all, alpha=0.85, capsize=8,
                  edgecolor='black', linewidth=1.5, error_kw={'linewidth': 2})
    
    ax.set_xlabel('Developer/Agent Type', fontsize=18, fontweight='bold')
    ax.set_ylabel('Mean Unique Advanced Features Used', fontsize=18, fontweight='bold')
    ax.set_title('Feature Diversity: Variety of TypeScript Features per PR', 
                 fontsize=20, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(agent_names, fontsize=16, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    
    # Add value labels
    for i, (bar, mean, std) in enumerate(zip(bars, diversity_means, diversity_stds)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + std,
               f'{mean:.2f}', ha='center', va='bottom',
               fontsize=14, fontweight='bold')
    
    # Add horizontal line for human baseline
    ax.axhline(y=diversity_means[-1], color='#F39C12', linestyle='--', 
               linewidth=2, alpha=0.7, label='Human Baseline')
    
    plt.tight_layout()
    plt.savefig('final_figures/fig3_rq2_feature_diversity.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("✓ Generated: fig3_rq2_feature_diversity.png")

# ==================== FIGURE 4: RQ2 - Mean Feature Usage ====================
def figure_rq2_feature_usage(agent_features, human_features):
    """RQ2 Figure 4: Mean Feature Usage Frequency"""
    fig, ax = plt.subplots(figsize=(10, 8))
    
    top_features = ['generics', 'union_types', 'type_assertions', 'optional_chaining',
                    'utility_types', 'intersection_types', 'keyof_typeof', 'type_guards',
                    'as_const', 'satisfies', 'nullish_coalescing', 'non_null_assertion']
    
    agent_means = []
    human_means = []
    feature_labels = []
    
    for feature in top_features:
        if feature in agent_features.columns:
            agent_means.append(agent_features[feature].mean())
            human_means.append(human_features[feature].mean())
            feature_labels.append(feature.replace('_', ' ').title())
    
    y = np.arange(len(feature_labels))
    height = 0.35
    
    bars1 = ax.barh(y + height/2, agent_means, height, label='AI Agent',
                    color=COLOR_AI, alpha=0.85, edgecolor='black', linewidth=1.5)
    bars2 = ax.barh(y - height/2, human_means, height, label='Human',
                    color=COLOR_HUMAN, alpha=0.85, edgecolor='black', linewidth=1.5)
    
    ax.set_yticks(y)
    ax.set_yticklabels(feature_labels, fontsize=14, fontweight='bold')
    ax.set_xlabel('Mean Usage per PR', fontsize=18, fontweight='bold')
    ax.set_title('Advanced TypeScript Feature Usage Frequency', 
                 fontsize=20, fontweight='bold', pad=20)
    ax.legend(fontsize=16, frameon=True, fancybox=True, shadow=True, loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='--', axis='x')
    
    # Add value labels
    for bars, means in [(bars1, agent_means), (bars2, human_means)]:
        for bar, mean in zip(bars, means):
            if mean > 0.5:
                ax.text(mean, bar.get_y() + bar.get_height()/2.,
                       f'{mean:.1f}', ha='left', va='center',
                       fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('final_figures/fig4_rq2_feature_usage.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("✓ Generated: fig4_rq2_feature_usage.png")

# ==================== FIGURE 5: RQ2 - Type Safety Feature Adoption ====================
def figure_rq2_safety_features(agent_features, human_features):
    """RQ2 Figure 5: Type Safety Feature Adoption"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    safety_features = {
        'Type Guards': 'type_guards',
        'Non-null Assertions': 'non_null_assertion',
        'Type Predicates': 'type_predicates',
        'Satisfies': 'satisfies',
        'As Const': 'as_const'
    }
    
    agent_safety = []
    human_safety = []
    feature_names = []
    
    for name, feature in safety_features.items():
        if feature in agent_features.columns:
            agent_safety.append((agent_features[feature] > 0).mean() * 100)
            human_safety.append((human_features[feature] > 0).mean() * 100)
            feature_names.append(name)
    
    x = np.arange(len(feature_names))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, agent_safety, width, label='AI Agent',
                   color=COLOR_AI, alpha=0.85, edgecolor='black', linewidth=1.5)
    bars2 = ax.bar(x + width/2, human_safety, width, label='Human',
                   color=COLOR_HUMAN, alpha=0.85, edgecolor='black', linewidth=1.5)
    
    ax.set_xlabel('Type Safety Feature', fontsize=18, fontweight='bold')
    ax.set_ylabel('Adoption Rate (% of PRs)', fontsize=18, fontweight='bold')
    ax.set_title('Type Safety Feature Adoption Patterns', 
                 fontsize=20, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(feature_names, fontsize=14, fontweight='bold', rotation=20, ha='right')
    ax.legend(fontsize=16, frameon=True, fancybox=True, shadow=True, loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%', ha='center', va='bottom',
                       fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('final_figures/fig5_rq2_safety_features.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("✓ Generated: fig5_rq2_safety_features.png")

# ==================== FIGURE 6: RQ3 - Acceptance Rates ====================
def figure_rq3_acceptance_overall(agent_df, human_df):
    """RQ3 Figure 6a: Overall PR Acceptance Rates"""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    agent_metrics = calculate_acceptance_metrics(agent_df)
    human_metrics = calculate_acceptance_metrics(human_df)
    
    categories = ['Merged\n(Accepted)', 'Closed\n(Rejected)', 'Open\n(Pending)']
    agent_values = [agent_metrics['acceptance_rate'],
                   agent_metrics['rejection_rate'],
                   agent_metrics['pending_rate']]
    human_values = [human_metrics['acceptance_rate'],
                   human_metrics['rejection_rate'],
                   human_metrics['pending_rate']]
    
    x = np.arange(len(categories))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, agent_values, width, label='AI Agent',
                   color=COLOR_AI, alpha=0.85, edgecolor='black', linewidth=1.5)
    bars2 = ax.bar(x + width/2, human_values, width, label='Human',
                   color=COLOR_HUMAN, alpha=0.85, edgecolor='black', linewidth=1.5)
    
    ax.set_xlabel('PR Status', fontsize=18, fontweight='bold')
    ax.set_ylabel('Percentage of PRs (%)', fontsize=18, fontweight='bold')
    ax.set_title('Pull Request Acceptance Rates in Type-Related Issues', 
                 fontsize=20, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=16, fontweight='bold')
    ax.legend(fontsize=16, frameon=True, fancybox=True, shadow=True, loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax.set_ylim(0, 80)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%', ha='center', va='bottom',
                   fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('final_figures/fig6a_rq3_acceptance_overall.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("✓ Generated: fig6a_rq3_acceptance_overall.png")

# ==================== FIGURE 7: RQ3 - Acceptance by Agent ====================
def figure_rq3_acceptance_by_agent(agent_df, human_df):
    """RQ3 Figure 6b: Acceptance Rate by Agent"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    agent_acceptance = agent_df.groupby('agent').apply(
        lambda x: (x['merged_at'].notna()).mean() * 100
    ).reset_index(name='acceptance_rate')
    
    # Add human baseline
    human_acceptance = (human_df['merged_at'].notna()).mean() * 100
    
    agents = list(agent_acceptance['agent'])
    rates = list(agent_acceptance['acceptance_rate'])
    
    # Sort by acceptance rate
    sorted_indices = np.argsort(rates)[::-1]
    agents = [agents[i] for i in sorted_indices]
    rates = [rates[i] for i in sorted_indices]
    
    # Add human
    agents.append('Human')
    rates.append(human_acceptance)
    
    # Create gradient colors
    colors = ['#E74C3C', '#9B59B6', '#3498DB', '#1ABC9C', '#F39C12']
    
    bars = ax.bar(range(len(agents)), rates, color=colors, alpha=0.85,
                  edgecolor='black', linewidth=1.5)
    
    ax.set_xlabel('Developer/Agent Type', fontsize=18, fontweight='bold')
    ax.set_ylabel('Acceptance Rate (%)', fontsize=18, fontweight='bold')
    ax.set_title('PR Acceptance Rate by AI Agent and Human Developers', 
                 fontsize=20, fontweight='bold', pad=20)
    ax.set_xticks(range(len(agents)))
    ax.set_xticklabels(agents, fontsize=16, fontweight='bold', rotation=15, ha='right')
    ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax.set_ylim(0, 70)
    
    # Add value labels
    for i, (bar, rate) in enumerate(zip(bars, rates)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{rate:.1f}%', ha='center', va='bottom',
               fontsize=14, fontweight='bold')
    
    # Highlight human bar
    bars[-1].set_edgecolor('#F39C12')
    bars[-1].set_linewidth(3)
    
    plt.tight_layout()
    plt.savefig('final_figures/fig6b_rq3_acceptance_by_agent.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("✓ Generated: fig6b_rq3_acceptance_by_agent.png")

# ==================== MAIN EXECUTION ====================
def main():
    print("=" * 60)
    print("Generating Final Publication-Ready Figures")
    print("=" * 60)
    
    # Load data
    print("\nLoading data...")
    agent_df, human_df = load_data()
    
    # Extract metrics for RQ1
    print("\nExtracting 'any' metrics for RQ1...")
    agent_any = extract_any_metrics(agent_df)
    human_any = extract_any_metrics(human_df)
    
    # Extract features for RQ2
    print("Extracting advanced features for RQ2...")
    agent_features = extract_advanced_features(agent_df)
    human_features = extract_advanced_features(human_df)
    
    # Generate figures
    print("\n" + "=" * 60)
    print("Generating Figures...")
    print("=" * 60 + "\n")
    
    print("[RQ1] Generating any type analysis figures...")
    figure_rq1_any_additions(agent_any, human_any)
    figure_rq1_agent_breakdown(agent_any)
    
    print("\n[RQ2] Generating advanced feature figures...")
    figure_rq2_feature_diversity(agent_features, human_features)
    figure_rq2_feature_usage(agent_features, human_features)
    figure_rq2_safety_features(agent_features, human_features)
    
    print("\n[RQ3] Generating acceptance rate figures...")
    figure_rq3_acceptance_overall(agent_df, human_df)
    figure_rq3_acceptance_by_agent(agent_df, human_df)
    
    print("\n" + "=" * 60)
    print("All figures generated successfully!")
    print("Saved in: final_figures/")
    print("=" * 60)

if __name__ == "__main__":
    main()


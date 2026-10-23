"""
RQ1 Analysis: Does Agentic PR actually resolve type-related problems, 
or does it simply bypass them using the any type?

This script analyzes the use of 'any' type in AI agent vs human PRs
to determine if agents are genuinely solving type issues or bypassing them.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import json
import warnings
warnings.filterwarnings('ignore')

# Set style for publication-quality figures
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['figure.figsize'] = (6, 4)

def load_and_filter_data():
    """Load and filter datasets for type-related PRs only"""
    # Load agent data
    agent_df = pd.read_csv('../data/agent_type_prs_filtered_by_open_ai.csv')
    agent_df['developer_type'] = 'AI Agent'
    
    # Load human data
    human_df = pd.read_csv('../human_type_prs_filtered_by_open_ai.csv')
    human_df['developer_type'] = 'Human'
    
    # Filter for type-related PRs only
    agent_df = agent_df[agent_df['final_is_type_related'] == True]
    human_df = human_df[human_df['final_is_type_related'] == True]
    
    print(f"Type-related PRs - AI Agents: {len(agent_df)}, Humans: {len(human_df)}")
    
    return agent_df, human_df

def extract_any_metrics(df):
    """Extract 'any' type usage metrics from patch text"""
    import re
    
    metrics = []
    
    for idx, row in df.iterrows():
        patch = str(row.get('patch_text', ''))
        
        # Look for TypeScript 'any' type annotations in diff format
        # Match patterns like ': any', '<any>', 'as any', '| any', '& any'
        type_any_pattern = r':\s*any[\s,;>\)\|&]|<any>|as\s+any|\|\s*any|&\s*any|Array<any>|Promise<any>|Record<\w+,\s*any>|Record<any'
        
        any_additions = 0
        any_removals = 0
        type_to_any_conversions = 0
        
        lines = patch.split('\n')
        for line in lines:
            # Count 'any' occurrences in added lines (start with +)
            if line.startswith('+') and not line.startswith('+++'):
                matches = re.findall(type_any_pattern, line)
                any_additions += len(matches)
            
            # Count 'any' occurrences in removed lines (start with -)
            elif line.startswith('-') and not line.startswith('---'):
                matches = re.findall(type_any_pattern, line)
                any_removals += len(matches)
        
        # Detect type-to-any conversions (specific type replaced with any)
        # Look for patterns where a specific type is removed and any is added
        for i, line in enumerate(lines):
            if line.startswith('-') and not line.startswith('---'):
                # Check if next line adds 'any' in similar context
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.startswith('+') and re.search(type_any_pattern, next_line):
                        # Check if the removed line had a different type
                        if ':' in line and 'any' not in line.lower():
                            type_to_any_conversions += 1
        
        metrics.append({
            'id': row['id'],
            'developer_type': row['developer_type'],
            'agent': row.get('agent', 'Human'),
            'any_additions': any_additions,
            'any_removals': any_removals,
            'any_replacements': min(any_additions, any_removals),  # Conservative estimate
            'type_to_any_conversions': type_to_any_conversions,
            'net_any_change': any_additions - any_removals,
            'total_any_operations': any_additions + any_removals
        })
    
    return pd.DataFrame(metrics)

def figure1_any_usage_comparison(agent_metrics, human_metrics):
    """Figure 1: Overall 'any' type usage comparison"""
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    
    # 1.1: Any additions comparison
    ax1 = axes[0]
    data_additions = pd.DataFrame({
        'AI Agent': agent_metrics['any_additions'],
        'Human': human_metrics['any_additions']
    })
    
    bp1 = ax1.boxplot([agent_metrics['any_additions'][agent_metrics['any_additions'] > 0],
                        human_metrics['any_additions'][human_metrics['any_additions'] > 0]],
                       labels=['AI Agent', 'Human'],
                       patch_artist=True,
                       showmeans=True)
    
    for patch, color in zip(bp1['boxes'], ['#FF6B6B', '#4ECDC4']):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax1.set_ylabel('Number of "any" Additions per PR')
    ax1.set_title('(a) "any" Type Additions')
    ax1.set_yscale('log')
    ax1.grid(True, alpha=0.3)
    
    # 1.2: Any removals comparison
    ax2 = axes[1]
    bp2 = ax2.boxplot([agent_metrics['any_removals'][agent_metrics['any_removals'] > 0],
                        human_metrics['any_removals'][human_metrics['any_removals'] > 0]],
                       labels=['AI Agent', 'Human'],
                       patch_artist=True,
                       showmeans=True)
    
    for patch, color in zip(bp2['boxes'], ['#FF6B6B', '#4ECDC4']):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax2.set_ylabel('Number of "any" Removals per PR')
    ax2.set_title('(b) "any" Type Removals')
    ax2.set_yscale('log')
    ax2.grid(True, alpha=0.3)
    
    # 1.3: Net any change
    ax3 = axes[2]
    agent_net = agent_metrics['net_any_change']
    human_net = human_metrics['net_any_change']
    
    bp3 = ax3.boxplot([agent_net[agent_net != 0],
                        human_net[human_net != 0]],
                       labels=['AI Agent', 'Human'],
                       patch_artist=True,
                       showmeans=True)
    
    for patch, color in zip(bp3['boxes'], ['#FF6B6B', '#4ECDC4']):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax3.set_ylabel('Net "any" Change (Additions - Removals)')
    ax3.set_title('(c) Net "any" Type Change')
    ax3.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('figures_rq1/fig1_any_usage_comparison.png', bbox_inches='tight')
    plt.close()
    
    # Statistical tests
    print("\n=== Statistical Tests for Figure 1 ===")
    print("Mann-Whitney U test for any additions:")
    u_stat, p_val = stats.mannwhitneyu(agent_metrics['any_additions'], 
                                        human_metrics['any_additions'], 
                                        alternative='two-sided')
    print(f"  U-statistic: {u_stat:.2f}, p-value: {p_val:.4f}")
    
    print("Mann-Whitney U test for any removals:")
    u_stat, p_val = stats.mannwhitneyu(agent_metrics['any_removals'], 
                                        human_metrics['any_removals'], 
                                        alternative='two-sided')
    print(f"  U-statistic: {u_stat:.2f}, p-value: {p_val:.4f}")

def figure2_any_behavior_patterns(agent_metrics, human_metrics):
    """Figure 2: Patterns of 'any' type behavior"""
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    
    # Filter to only PRs with any changes
    agent_with_changes = agent_metrics[agent_metrics['total_any_operations'] > 0].copy()
    human_with_changes = human_metrics[human_metrics['total_any_operations'] > 0].copy()
    
    # 2.1: Distribution of PRs by any behavior
    ax1 = axes[0, 0]
    
    def categorize_pr(row):
        if row['any_additions'] > 0 and row['any_removals'] == 0:
            return 'Only Adds'
        elif row['any_removals'] > 0 and row['any_additions'] == 0:
            return 'Only Removes'
        elif row['any_additions'] > 0 and row['any_removals'] > 0:
            return 'Both'
    
    agent_with_changes['category'] = agent_with_changes.apply(categorize_pr, axis=1)
    human_with_changes['category'] = human_with_changes.apply(categorize_pr, axis=1)
    
    agent_counts = agent_with_changes['category'].value_counts()
    human_counts = human_with_changes['category'].value_counts()
    
    categories = ['Only Adds', 'Only Removes', 'Both']
    agent_vals = [agent_counts.get(cat, 0) for cat in categories]
    human_vals = [human_counts.get(cat, 0) for cat in categories]
    
    # Normalize to percentages (of PRs with changes)
    agent_pct = [v/sum(agent_vals)*100 if sum(agent_vals) > 0 else 0 for v in agent_vals]
    human_pct = [v/sum(human_vals)*100 if sum(human_vals) > 0 else 0 for v in human_vals]
    
    x = np.arange(len(categories))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, agent_pct, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax1.bar(x + width/2, human_pct, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax1.set_xlabel('PR Behavior Category')
    ax1.set_ylabel('Percentage of PRs with "any" Changes (%)')
    ax1.set_title('(a) Distribution of "any" Modification Patterns\n(Only PRs with "any" changes)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, rotation=45, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add text showing count of PRs with changes
    ax1.text(0.5, 0.95, f'AI: {len(agent_with_changes)} PRs, Human: {len(human_with_changes)} PRs',
            transform=ax1.transAxes, ha='center', va='top', fontsize=8, alpha=0.7)
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%', ha='center', va='bottom', fontsize=8)
    
    # 2.2: Type-to-any conversions (only PRs with conversions)
    ax2 = axes[0, 1]
    
    agent_conversions = agent_metrics[agent_metrics['type_to_any_conversions'] > 0]['type_to_any_conversions']
    human_conversions = human_metrics[human_metrics['type_to_any_conversions'] > 0]['type_to_any_conversions']
    
    # Count PRs with conversions
    agent_with_conv = len(agent_conversions)
    human_with_conv = len(human_conversions)
    
    # Calculate total conversions
    agent_total_conv = agent_conversions.sum() if len(agent_conversions) > 0 else 0
    human_total_conv = human_conversions.sum() if len(human_conversions) > 0 else 0
    
    labels = ['AI Agent', 'Human']
    pr_counts = [agent_with_conv, human_with_conv]
    
    x = np.arange(len(labels))
    
    bars = ax2.bar(x, pr_counts, color=['#E74C3C', '#4ECDC4'], alpha=0.7)
    
    ax2.set_ylabel('Number of PRs with Type→any Conversions')
    ax2.set_title('(b) Type-to-any Conversions\n(Only PRs with conversions)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.grid(True, alpha=0.3)
    
    # Add value labels
    for bar, count, total in zip(bars, pr_counts, [agent_total_conv, human_total_conv]):
        height = bar.get_height()
        if height > 0:
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(count)} PRs\n({int(total)} total)',
                    ha='center', va='bottom', fontsize=8)
    
    # Add percentage of all PRs
    agent_pct = (agent_with_conv / len(agent_metrics) * 100) if len(agent_metrics) > 0 else 0
    human_pct = (human_with_conv / len(human_metrics) * 100) if len(human_metrics) > 0 else 0
    ax2.text(0.02, 0.98, f'AI: {agent_pct:.1f}% of all PRs\nHuman: {human_pct:.1f}% of all PRs',
            transform=ax2.transAxes, fontsize=7, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # 2.3: Cumulative distribution of net any changes
    ax3 = axes[1, 0]
    
    agent_net_sorted = np.sort(agent_metrics['net_any_change'])
    human_net_sorted = np.sort(human_metrics['net_any_change'])
    
    agent_cdf = np.arange(1, len(agent_net_sorted) + 1) / len(agent_net_sorted)
    human_cdf = np.arange(1, len(human_net_sorted) + 1) / len(human_net_sorted)
    
    ax3.plot(agent_net_sorted, agent_cdf, label='AI Agent', color='#FF6B6B', linewidth=2)
    ax3.plot(human_net_sorted, human_cdf, label='Human', color='#4ECDC4', linewidth=2)
    
    ax3.axvline(x=0, color='black', linestyle='--', alpha=0.5)
    ax3.set_xlabel('Net "any" Change per PR')
    ax3.set_ylabel('Cumulative Probability')
    ax3.set_title('(c) CDF of Net "any" Changes')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(-20, 20)
    
    # 2.4: Agent-specific breakdown
    ax4 = axes[1, 1]
    
    if 'agent' in agent_metrics.columns:
        agent_breakdown = agent_metrics.groupby('agent').agg({
            'any_additions': 'sum',
            'any_removals': 'sum'
        }).reset_index()
        
        agents = agent_breakdown['agent']
        additions = agent_breakdown['any_additions']
        removals = agent_breakdown['any_removals']
        
        x = np.arange(len(agents))
        width = 0.35
        
        bars1 = ax4.bar(x - width/2, additions, width, label='Additions', color='#E74C3C', alpha=0.7)
        bars2 = ax4.bar(x + width/2, removals, width, label='Removals', color='#27AE60', alpha=0.7)
        
        ax4.set_xlabel('AI Agent')
        ax4.set_ylabel('Total "any" Operations')
        ax4.set_title('(d) "any" Operations by AI Agent')
        ax4.set_xticks(x)
        ax4.set_xticklabels(agents, rotation=45, ha='right')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('figures_rq1/fig2_any_behavior_patterns.png', bbox_inches='tight')
    plt.close()

def figure3_any_resolution_quality(agent_metrics, human_metrics):
    """Figure 3: Quality of type problem resolution - Only PRs with 'any' changes"""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    
    # Filter to only PRs with any changes
    agent_with_changes = agent_metrics[agent_metrics['total_any_operations'] > 0].copy()
    human_with_changes = human_metrics[human_metrics['total_any_operations'] > 0].copy()
    
    # 3.1: Resolution approach classification
    ax1 = axes[0]
    
    def classify_resolution(row):
        if row['any_removals'] > row['any_additions']:
            return 'Improves Type Safety'
        elif row['any_additions'] > row['any_removals']:
            return 'Reduces Type Safety'
        else:
            return 'Neutral'
    
    agent_with_changes['resolution'] = agent_with_changes.apply(classify_resolution, axis=1)
    human_with_changes['resolution'] = human_with_changes.apply(classify_resolution, axis=1)
    
    resolution_types = ['Improves Type Safety', 'Reduces Type Safety', 'Neutral']
    
    agent_res_counts = agent_with_changes['resolution'].value_counts()
    human_res_counts = human_with_changes['resolution'].value_counts()
    
    agent_res_pct = [agent_res_counts.get(r, 0)/len(agent_with_changes)*100 if len(agent_with_changes) > 0 else 0 for r in resolution_types]
    human_res_pct = [human_res_counts.get(r, 0)/len(human_with_changes)*100 if len(human_with_changes) > 0 else 0 for r in resolution_types]
    
    x = np.arange(len(resolution_types))
    width = 0.35
    
    colors = ['#27AE60', '#E74C3C', '#F39C12']
    
    bars1 = ax1.bar(x - width/2, agent_res_pct, width, label='AI Agent', alpha=0.7)
    bars2 = ax1.bar(x + width/2, human_res_pct, width, label='Human', alpha=0.7)
    
    # Color bars by resolution type
    for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
        bar1.set_color(colors[i])
        bar2.set_color(colors[i])
        bar2.set_alpha(0.5)
    
    ax1.set_xlabel('Resolution Type')
    ax1.set_ylabel('Percentage of PRs with "any" Changes (%)')
    ax1.set_title('(a) Type Safety Impact\n(Only PRs with "any" changes)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(resolution_types, rotation=45, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add text showing sample sizes
    ax1.text(0.5, 0.95, f'AI: {len(agent_with_changes)} PRs, Human: {len(human_with_changes)} PRs',
            transform=ax1.transAxes, ha='center', va='top', fontsize=8, alpha=0.7)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%', ha='center', va='bottom', fontsize=8)
    
    # 3.2: Ratio of removals to additions (safety improvement metric)
    ax2 = axes[1]
    
    # Calculate safety improvement ratio
    agent_with_changes = agent_metrics[agent_metrics['total_any_operations'] > 0].copy()
    human_with_changes = human_metrics[human_metrics['total_any_operations'] > 0].copy()
    
    agent_with_changes['safety_ratio'] = (agent_with_changes['any_removals'] - agent_with_changes['any_additions']) / agent_with_changes['total_any_operations']
    human_with_changes['safety_ratio'] = (human_with_changes['any_removals'] - human_with_changes['any_additions']) / human_with_changes['total_any_operations']
    
    # Create violin plot (handle empty data)
    agent_ratio = agent_with_changes['safety_ratio'].dropna()
    human_ratio = human_with_changes['safety_ratio'].dropna()
    
    positions = [1, 2]
    if len(agent_ratio) > 0 and len(human_ratio) > 0:
        parts = ax2.violinplot([agent_ratio, human_ratio],
                               positions=positions,
                               showmeans=True,
                               showmedians=True)
        
        # Customize colors
        for pc, color in zip(parts['bodies'], ['#FF6B6B', '#4ECDC4']):
            pc.set_facecolor(color)
            pc.set_alpha(0.7)
    else:
        # If no data, create a placeholder
        ax2.text(0.5, 0.5, 'Insufficient data\nfor visualization',
                transform=ax2.transAxes, ha='center', va='center',
                fontsize=10, alpha=0.5)
    
    ax2.set_xticks(positions)
    ax2.set_xticklabels(['AI Agent', 'Human'])
    ax2.set_ylabel('Safety Improvement Ratio')
    ax2.set_title('(b) Type Safety Improvement Distribution')
    ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax2.set_ylim(-1, 1)
    ax2.grid(True, alpha=0.3)
    
    # Add annotations
    ax2.text(0.5, 0.5, 'Improves\nSafety', transform=ax2.transAxes, 
            fontsize=9, alpha=0.5, ha='center')
    ax2.text(0.5, 0.1, 'Reduces\nSafety', transform=ax2.transAxes,
            fontsize=9, alpha=0.5, ha='center')
    
    plt.tight_layout()
    plt.savefig('figures_rq1/fig3_resolution_quality.png', bbox_inches='tight')
    plt.close()
    
    # Statistical comparison
    print("\n=== Type Safety Resolution Analysis (PRs with 'any' changes only) ===")
    print(f"Total PRs with 'any' changes - AI Agents: {len(agent_with_changes)}, Humans: {len(human_with_changes)}")
    print(f"\nAI Agents improving type safety: {agent_res_counts.get('Improves Type Safety', 0)} PRs ({agent_res_pct[0]:.1f}%)")
    print(f"Humans improving type safety: {human_res_counts.get('Improves Type Safety', 0)} PRs ({human_res_pct[0]:.1f}%)")
    print(f"\nAI Agents reducing type safety: {agent_res_counts.get('Reduces Type Safety', 0)} PRs ({agent_res_pct[1]:.1f}%)")
    print(f"Humans reducing type safety: {human_res_counts.get('Reduces Type Safety', 0)} PRs ({human_res_pct[1]:.1f}%)")
    print(f"\nNeutral (equal adds/removes) - AI: {agent_res_counts.get('Neutral', 0)}, Human: {human_res_counts.get('Neutral', 0)}")

def figure4_statistical_summary(agent_metrics, human_metrics):
    """Figure 4: Statistical summary and hypothesis testing"""
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    
    # 4.1: Mean comparisons with confidence intervals
    ax1 = axes[0, 0]
    
    metrics_to_compare = ['any_additions', 'any_removals', 'net_any_change']
    metric_labels = ['Additions', 'Removals', 'Net Change']
    
    agent_means = []
    agent_ci_lower = []
    agent_ci_upper = []
    human_means = []
    human_ci_lower = []
    human_ci_upper = []
    
    for metric in metrics_to_compare:
        # Bootstrap confidence intervals
        agent_data = agent_metrics[metric]
        human_data = human_metrics[metric]
        
        # Calculate mean and 95% CI
        agent_mean = agent_data.mean()
        human_mean = human_data.mean()
        
        agent_se = agent_data.sem()
        human_se = human_data.sem()
        
        agent_ci = 1.96 * agent_se
        human_ci = 1.96 * human_se
        
        agent_means.append(agent_mean)
        agent_ci_lower.append(agent_mean - agent_ci)
        agent_ci_upper.append(agent_mean + agent_ci)
        
        human_means.append(human_mean)
        human_ci_lower.append(human_mean - human_ci)
        human_ci_upper.append(human_mean + human_ci)
    
    x = np.arange(len(metrics_to_compare))
    width = 0.35
    
    ax1.bar(x - width/2, agent_means, width, label='AI Agent', 
            color='#FF6B6B', alpha=0.7, yerr=[np.array(agent_means) - np.array(agent_ci_lower),
                                               np.array(agent_ci_upper) - np.array(agent_means)])
    ax1.bar(x + width/2, human_means, width, label='Human',
            color='#4ECDC4', alpha=0.7, yerr=[np.array(human_means) - np.array(human_ci_lower),
                                               np.array(human_ci_upper) - np.array(human_means)])
    
    ax1.set_xlabel('Metric')
    ax1.set_ylabel('Mean Value (with 95% CI)')
    ax1.set_title('(a) Mean "any" Metrics Comparison')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metric_labels)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 4.2: Effect size comparison
    ax2 = axes[0, 1]
    
    effect_sizes = []
    effect_labels = []
    
    for metric, label in zip(metrics_to_compare, metric_labels):
        # Calculate Cohen's d
        agent_data = agent_metrics[metric]
        human_data = human_metrics[metric]
        
        pooled_std = np.sqrt((agent_data.std()**2 + human_data.std()**2) / 2)
        if pooled_std > 0:
            cohens_d = (agent_data.mean() - human_data.mean()) / pooled_std
            effect_sizes.append(cohens_d)
            effect_labels.append(label)
    
    colors = ['#E74C3C' if d > 0 else '#27AE60' for d in effect_sizes]
    bars = ax2.barh(range(len(effect_sizes)), effect_sizes, color=colors, alpha=0.7)
    
    ax2.set_yticks(range(len(effect_sizes)))
    ax2.set_yticklabels(effect_labels)
    ax2.set_xlabel("Cohen's d (Effect Size)")
    ax2.set_title("(b) Effect Sizes: Agent vs Human")
    ax2.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax2.axvline(x=0.2, color='gray', linestyle='--', alpha=0.5)
    ax2.axvline(x=-0.2, color='gray', linestyle='--', alpha=0.5)
    ax2.axvline(x=0.5, color='gray', linestyle='--', alpha=0.5)
    ax2.axvline(x=-0.5, color='gray', linestyle='--', alpha=0.5)
    ax2.grid(True, alpha=0.3)
    
    # Add effect size labels
    ax2.text(0.3, len(effect_sizes)-0.5, 'Small', fontsize=8, alpha=0.5)
    ax2.text(0.6, len(effect_sizes)-0.5, 'Medium', fontsize=8, alpha=0.5)
    
    # 4.3: Probability of adding vs removing any
    ax3 = axes[1, 0]
    
    agent_adds_any = (agent_metrics['any_additions'] > 0).sum()
    agent_removes_any = (agent_metrics['any_removals'] > 0).sum()
    human_adds_any = (human_metrics['any_additions'] > 0).sum()
    human_removes_any = (human_metrics['any_removals'] > 0).sum()
    
    prob_data = pd.DataFrame({
        'AI Agent': [agent_adds_any/len(agent_metrics)*100, 
                     agent_removes_any/len(agent_metrics)*100],
        'Human': [human_adds_any/len(human_metrics)*100, 
                  human_removes_any/len(human_metrics)*100]
    }, index=['Adds any', 'Removes any'])
    
    prob_data.plot(kind='bar', ax=ax3, color=['#FF6B6B', '#4ECDC4'], alpha=0.7)
    ax3.set_ylabel('Probability (%)')
    ax3.set_title('(c) Probability of "any" Operations')
    ax3.set_xticklabels(ax3.get_xticklabels(), rotation=45, ha='right')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # 4.4: Summary statistics table
    ax4 = axes[1, 1]
    ax4.axis('tight')
    ax4.axis('off')
    
    # Create summary statistics
    summary_data = []
    
    for name, df in [('AI Agent', agent_metrics), ('Human', human_metrics)]:
        summary_data.append([
            name,
            f"{df['any_additions'].mean():.2f} ± {df['any_additions'].std():.2f}",
            f"{df['any_removals'].mean():.2f} ± {df['any_removals'].std():.2f}",
            f"{df['net_any_change'].mean():.2f} ± {df['net_any_change'].std():.2f}",
            f"{(df['any_additions'] > 0).mean()*100:.1f}%"
        ])
    
    table = ax4.table(cellText=summary_data,
                     colLabels=['Developer', 'Mean Adds', 'Mean Removes', 'Mean Net', 'PRs w/ Adds'],
                     cellLoc='center',
                     loc='center',
                     bbox=[0, 0, 1, 1])
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)
    
    # Style the header
    for i in range(5):
        table[(0, i)].set_facecolor('#E8E8E8')
        table[(0, i)].set_text_props(weight='bold')
    
    ax4.set_title('(d) Summary Statistics', pad=20)
    
    plt.tight_layout()
    plt.savefig('figures_rq1/fig4_statistical_summary.png', bbox_inches='tight')
    plt.close()

def main():
    """Main analysis pipeline for RQ1"""
    print("=" * 60)
    print("RQ1 Analysis: Any Type Usage in AI Agent vs Human PRs")
    print("=" * 60)
    
    # Load and filter data
    agent_df, human_df = load_and_filter_data()
    
    # Extract any metrics
    print("\nExtracting 'any' type metrics...")
    agent_metrics = extract_any_metrics(agent_df)
    human_metrics = extract_any_metrics(human_df)
    
    print(f"Agent metrics extracted: {len(agent_metrics)} PRs")
    print(f"Human metrics extracted: {len(human_metrics)} PRs")
    
    # Generate figures
    print("\nGenerating Figure 1: Overall any usage comparison...")
    figure1_any_usage_comparison(agent_metrics, human_metrics)
    
    print("\nGenerating Figure 2: Any behavior patterns...")
    figure2_any_behavior_patterns(agent_metrics, human_metrics)
    
    print("\nGenerating Figure 3: Resolution quality analysis...")
    figure3_any_resolution_quality(agent_metrics, human_metrics)
    
    print("\nGenerating Figure 4: Statistical summary...")
    figure4_statistical_summary(agent_metrics, human_metrics)
    
    # Save processed metrics for further analysis
    agent_metrics.to_csv('figures_rq1/agent_any_metrics.csv', index=False)
    human_metrics.to_csv('figures_rq1/human_any_metrics.csv', index=False)
    
    print("\n" + "=" * 60)
    print("RQ1 Analysis Complete!")
    print("Figures saved in figures_rq1/")
    print("=" * 60)

if __name__ == "__main__":
    main()

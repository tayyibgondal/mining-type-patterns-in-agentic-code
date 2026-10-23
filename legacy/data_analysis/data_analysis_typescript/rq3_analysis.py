"""
RQ3 Analysis: How similar are the acceptance rate and code accuracy of
Agentic PRs to those of human developers in TypeScript bug fixes?

This script analyzes acceptance rates, code quality metrics, and accuracy
indicators between AI agents and human developers.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from datetime import datetime
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

def calculate_acceptance_metrics(df):
    """Calculate acceptance-related metrics"""
    metrics = {}
    
    # Basic acceptance rate (merged PRs - identified by merged_at field)
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
    
    # Time to merge (for merged PRs - identified by merged_at field)
    merged_df = df[df['merged_at'].notna()].copy()
    if len(merged_df) > 0:
        merged_df['created_at'] = pd.to_datetime(merged_df['created_at'], errors='coerce')
        merged_df['merged_at'] = pd.to_datetime(merged_df['merged_at'], errors='coerce')
        merged_df['time_to_merge'] = (merged_df['merged_at'] - merged_df['created_at']).dt.total_seconds() / 3600  # hours
        
        # Filter out invalid times
        valid_times = merged_df['time_to_merge'].dropna()
        valid_times = valid_times[valid_times > 0]
        
        if len(valid_times) > 0:
            metrics['median_time_to_merge'] = valid_times.median()
            metrics['mean_time_to_merge'] = valid_times.mean()
            metrics['std_time_to_merge'] = valid_times.std()
        else:
            metrics['median_time_to_merge'] = 0
            metrics['mean_time_to_merge'] = 0
            metrics['std_time_to_merge'] = 0
    else:
        metrics['median_time_to_merge'] = 0
        metrics['mean_time_to_merge'] = 0
        metrics['std_time_to_merge'] = 0
    
    return metrics

def calculate_accuracy_metrics(df):
    """Calculate code accuracy and quality metrics"""
    accuracy_metrics = []
    
    for idx, row in df.iterrows():
        # Determine if PR was merged (has merged_at value)
        is_merged = pd.notna(row.get('merged_at'))
        pr_status = 'merged' if is_merged else row['state']
        
        metrics = {
            'id': row['id'],
            'developer_type': row['developer_type'],
            'agent': row.get('agent', 'Human'),
            'state': row['state'],
            'pr_status': pr_status,  # merged, closed, or open
            'is_merged': is_merged,
            
            # Validation metrics
            'classifier_confidence': row.get('classifier_confidence', 0),
            'validator_confidence': row.get('validator_confidence', 0),
            'validator_agreed': row.get('validator_agreed', False),
            
            # Code change metrics
            'additions': row.get('additions', 0),
            'deletions': row.get('deletions', 0),
            'changes': row.get('changes', 0),
            'ts_files_changed': row.get('ts_files_changed', 0),
            
            # Calculate change ratio
            'change_ratio': row.get('deletions', 0) / row.get('additions', 1) if row.get('additions', 0) > 0 else 0,
            
            # PR complexity (based on changes)
            'pr_size': 'small' if row.get('changes', 0) <= 10 else ('medium' if row.get('changes', 0) <= 50 else 'large')
        }
        
        # Analyze patch for potential issues
        patch = str(row.get('patch_text', ''))
        
        # Look for common quality indicators
        metrics['has_tests'] = 'test' in patch.lower() or 'spec' in patch.lower()
        metrics['has_todo'] = 'todo' in patch.lower() or 'fixme' in patch.lower()
        metrics['has_eslint_disable'] = 'eslint-disable' in patch.lower()
        metrics['has_ts_ignore'] = '@ts-ignore' in patch or '@ts-nocheck' in patch
        metrics['has_any_type'] = ': any' in patch or '<any>' in patch
        
        accuracy_metrics.append(metrics)
    
    return pd.DataFrame(accuracy_metrics)

def figure1_acceptance_rates(agent_df, human_df):
    """Figure 1: PR Acceptance Rate Analysis"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 1.1: Overall acceptance rates
    ax1 = axes[0, 0]
    
    agent_metrics = calculate_acceptance_metrics(agent_df)
    human_metrics = calculate_acceptance_metrics(human_df)
    
    categories = ['Merged', 'Closed', 'Open']
    agent_values = [agent_metrics['acceptance_rate'], 
                    agent_metrics['rejection_rate'],
                    agent_metrics['pending_rate']]
    human_values = [human_metrics['acceptance_rate'],
                    human_metrics['rejection_rate'],
                    human_metrics['pending_rate']]
    
    x = np.arange(len(categories))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, agent_values, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax1.bar(x + width/2, human_values, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax1.set_xlabel('PR Status')
    ax1.set_ylabel('Percentage (%)')
    ax1.set_title('(a) PR Acceptance Rates')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=8)
    
    # 1.2: Acceptance by agent type
    ax2 = axes[0, 1]
    
    agent_acceptance = agent_df.groupby('agent').apply(
        lambda x: (x['merged_at'].notna()).mean() * 100
    ).reset_index(name='acceptance_rate')
    
    # Add human baseline
    human_acceptance = human_metrics['acceptance_rate']
    
    agents = list(agent_acceptance['agent'])
    rates = list(agent_acceptance['acceptance_rate'])
    
    # Sort by acceptance rate
    sorted_indices = np.argsort(rates)[::-1]
    agents = [agents[i] for i in sorted_indices]
    rates = [rates[i] for i in sorted_indices]
    
    # Add human at the end for comparison
    agents.append('Human')
    rates.append(human_acceptance)
    
    colors = plt.cm.Set3(np.linspace(0, 1, len(agents)))
    bars = ax2.bar(range(len(agents)), rates, color=colors, alpha=0.7)
    
    ax2.set_xlabel('Developer/Agent')
    ax2.set_ylabel('Acceptance Rate (%)')
    ax2.set_title('(b) Acceptance Rate by Agent')
    ax2.set_xticks(range(len(agents)))
    ax2.set_xticklabels(agents, rotation=45, ha='right')
    ax2.grid(True, alpha=0.3)
    
    # Add value labels
    for bar, rate in zip(bars, rates):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{rate:.1f}%', ha='center', va='bottom', fontsize=8)
    
    # 1.3: Time to merge distribution
    ax3 = axes[1, 0]
    
    # Calculate time to merge for merged PRs
    agent_merged = agent_df[agent_df['merged_at'].notna()].copy()
    human_merged = human_df[human_df['merged_at'].notna()].copy()
    
    if len(agent_merged) > 0 and len(human_merged) > 0:
        agent_merged['created_at'] = pd.to_datetime(agent_merged['created_at'], errors='coerce')
        agent_merged['merged_at'] = pd.to_datetime(agent_merged['merged_at'], errors='coerce')
        agent_merged['time_to_merge'] = (agent_merged['merged_at'] - agent_merged['created_at']).dt.total_seconds() / 3600
        
        human_merged['created_at'] = pd.to_datetime(human_merged['created_at'], errors='coerce')
        human_merged['merged_at'] = pd.to_datetime(human_merged['merged_at'], errors='coerce')
        human_merged['time_to_merge'] = (human_merged['merged_at'] - human_merged['created_at']).dt.total_seconds() / 3600
        
        # Filter valid times (positive and reasonable)
        agent_times = agent_merged['time_to_merge'].dropna()
        agent_times = agent_times[(agent_times > 0) & (agent_times < 10000)]
        
        human_times = human_merged['time_to_merge'].dropna()
        human_times = human_times[(human_times > 0) & (human_times < 10000)]
        
        if len(agent_times) > 0 and len(human_times) > 0:
            # Create violin plot
            positions = [1, 2]
            parts = ax3.violinplot([agent_times, human_times],
                                   positions=positions,
                                   showmeans=True,
                                   showmedians=True)
            
            for pc, color in zip(parts['bodies'], ['#FF6B6B', '#4ECDC4']):
                pc.set_facecolor(color)
                pc.set_alpha(0.7)
            
            ax3.set_xticks(positions)
            ax3.set_xticklabels(['AI Agent', 'Human'])
            ax3.set_ylabel('Time to Merge (hours)')
            ax3.set_yscale('log')
        else:
            ax3.text(0.5, 0.5, 'Insufficient data', transform=ax3.transAxes,
                    ha='center', va='center', fontsize=10, alpha=0.5)
    else:
        ax3.text(0.5, 0.5, 'No merged PRs', transform=ax3.transAxes,
                ha='center', va='center', fontsize=10, alpha=0.5)
    
    ax3.set_title('(c) Time to Merge Distribution')
    ax3.grid(True, alpha=0.3)
    
    # 1.4: PR size distribution
    ax4 = axes[1, 1]
    
    def categorize_pr_size(changes):
        if changes <= 10:
            return 'Small (≤10)'
        elif changes <= 50:
            return 'Medium (11-50)'
        elif changes <= 200:
            return 'Large (51-200)'
        else:
            return 'Very Large (>200)'
    
    agent_df['size_category'] = agent_df['changes'].apply(categorize_pr_size)
    human_df['size_category'] = human_df['changes'].apply(categorize_pr_size)
    
    size_order = ['Small (≤10)', 'Medium (11-50)', 'Large (51-200)', 'Very Large (>200)']
    
    agent_sizes = agent_df['size_category'].value_counts()
    human_sizes = human_df['size_category'].value_counts()
    
    agent_pct = [agent_sizes.get(s, 0)/len(agent_df)*100 for s in size_order]
    human_pct = [human_sizes.get(s, 0)/len(human_df)*100 for s in size_order]
    
    x = np.arange(len(size_order))
    
    bars1 = ax4.bar(x - width/2, agent_pct, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax4.bar(x + width/2, human_pct, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax4.set_xlabel('PR Size')
    ax4.set_ylabel('Percentage (%)')
    ax4.set_title('(d) PR Size Distribution')
    ax4.set_xticks(x)
    ax4.set_xticklabels(size_order, rotation=45, ha='right')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('figures_rq3/fig1_acceptance_rates.png', bbox_inches='tight')
    plt.close()
    
    # Print statistics
    print("\n=== Acceptance Rate Statistics ===")
    print(f"AI Agent: {agent_metrics['acceptance_rate']:.1f}% accepted, {agent_metrics['rejection_rate']:.1f}% rejected")
    print(f"Human: {human_metrics['acceptance_rate']:.1f}% accepted, {human_metrics['rejection_rate']:.1f}% rejected")
    
    # Chi-square test for independence (if there's enough data)
    if agent_metrics['merged_count'] > 0 or human_metrics['merged_count'] > 0:
        contingency_table = np.array([
            [max(1, agent_metrics['merged_count']), max(1, agent_metrics['closed_count'])],
            [max(1, human_metrics['merged_count']), max(1, human_metrics['closed_count'])]
        ])
        try:
            chi2, p_val, dof, expected = stats.chi2_contingency(contingency_table)
            print(f"\nChi-square test for acceptance rates: χ²={chi2:.2f}, p={p_val:.4f}")
        except ValueError:
            print("\nChi-square test: Insufficient data for statistical test")
    else:
        print("\nNote: No merged PRs found for statistical comparison")

def figure2_code_quality_metrics(agent_accuracy, human_accuracy):
    """Figure 2: Code quality and accuracy metrics"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 2.1: Quality indicators presence
    ax1 = axes[0, 0]
    
    quality_indicators = {
        'Has Tests': 'has_tests',
        'Has TODO/FIXME': 'has_todo',
        'Has ESLint Disable': 'has_eslint_disable',
        'Has @ts-ignore': 'has_ts_ignore',
        'Has any Type': 'has_any_type'
    }
    
    agent_quality = []
    human_quality = []
    indicator_names = []
    
    for name, col in quality_indicators.items():
        agent_quality.append(agent_accuracy[col].mean() * 100)
        human_quality.append(human_accuracy[col].mean() * 100)
        indicator_names.append(name)
    
    x = np.arange(len(indicator_names))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, agent_quality, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax1.bar(x + width/2, human_quality, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax1.set_xlabel('Quality Indicator')
    ax1.set_ylabel('Percentage of PRs (%)')
    ax1.set_title('(a) Code Quality Indicators')
    ax1.set_xticks(x)
    ax1.set_xticklabels(indicator_names, rotation=45, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2.2: Confidence score distribution
    ax2 = axes[0, 1]
    
    # Create violin plots for confidence scores
    positions = [1, 2, 3, 4]
    data_to_plot = [
        agent_accuracy['classifier_confidence'].dropna(),
        human_accuracy['classifier_confidence'].dropna(),
        agent_accuracy['validator_confidence'].dropna(),
        human_accuracy['validator_confidence'].dropna()
    ]
    
    parts = ax2.violinplot(data_to_plot, positions=positions,
                           showmeans=True, showmedians=True)
    
    colors = ['#FF6B6B', '#4ECDC4', '#FF6B6B', '#4ECDC4']
    for i, pc in enumerate(parts['bodies']):
        pc.set_facecolor(colors[i])
        pc.set_alpha(0.7)
    
    ax2.set_xticks(positions)
    ax2.set_xticklabels(['Agent\nClassifier', 'Human\nClassifier',
                         'Agent\nValidator', 'Human\nValidator'], fontsize=8)
    ax2.set_ylabel('Confidence Score')
    ax2.set_title('(b) Classification Confidence Scores')
    ax2.grid(True, alpha=0.3)
    
    # 2.3: Code change patterns
    ax3 = axes[1, 0]
    
    # Calculate change ratios
    agent_accuracy['balanced_changes'] = np.abs(agent_accuracy['change_ratio'] - 1) < 0.5
    human_accuracy['balanced_changes'] = np.abs(human_accuracy['change_ratio'] - 1) < 0.5
    
    change_patterns = ['Balanced Changes', 'More Additions', 'More Deletions']
    
    agent_patterns = [
        agent_accuracy['balanced_changes'].mean() * 100,
        (agent_accuracy['change_ratio'] < 0.5).mean() * 100,
        (agent_accuracy['change_ratio'] > 1.5).mean() * 100
    ]
    
    human_patterns = [
        human_accuracy['balanced_changes'].mean() * 100,
        (human_accuracy['change_ratio'] < 0.5).mean() * 100,
        (human_accuracy['change_ratio'] > 1.5).mean() * 100
    ]
    
    x = np.arange(len(change_patterns))
    
    bars1 = ax3.bar(x - width/2, agent_patterns, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax3.bar(x + width/2, human_patterns, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax3.set_xlabel('Change Pattern')
    ax3.set_ylabel('Percentage of PRs (%)')
    ax3.set_title('(c) Code Change Patterns')
    ax3.set_xticks(x)
    ax3.set_xticklabels(change_patterns)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 2.4: Validator agreement rates
    ax4 = axes[1, 1]
    
    # Group by pr_status (which includes merged) and validator agreement
    agent_agreement = agent_accuracy.groupby('pr_status')['validator_agreed'].mean() * 100
    human_agreement = human_accuracy.groupby('pr_status')['validator_agreed'].mean() * 100
    
    states = ['merged', 'closed', 'open']
    agent_vals = [agent_agreement.get(s, 0) for s in states]
    human_vals = [human_agreement.get(s, 0) for s in states]
    
    x = np.arange(len(states))
    
    bars1 = ax4.bar(x - width/2, agent_vals, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax4.bar(x + width/2, human_vals, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax4.set_xlabel('PR State')
    ax4.set_ylabel('Validator Agreement Rate (%)')
    ax4.set_title('(d) Validator Agreement by PR State')
    ax4.set_xticks(x)
    ax4.set_xticklabels([s.capitalize() for s in states])
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax4.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    plt.savefig('figures_rq3/fig2_code_quality_metrics.png', bbox_inches='tight')
    plt.close()

def figure3_accuracy_by_complexity(agent_accuracy, human_accuracy):
    """Figure 3: Accuracy analysis by PR complexity"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 3.1: Acceptance rate by PR size
    ax1 = axes[0, 0]
    
    size_order = ['small', 'medium', 'large']
    
    agent_by_size = agent_accuracy.groupby('pr_size').agg({
        'is_merged': lambda x: x.mean() * 100
    }).rename(columns={'is_merged': 'acceptance_rate'})
    
    human_by_size = human_accuracy.groupby('pr_size').agg({
        'is_merged': lambda x: x.mean() * 100
    }).rename(columns={'is_merged': 'acceptance_rate'})
    
    agent_size_rates = [agent_by_size.loc[s, 'acceptance_rate'] if s in agent_by_size.index else 0 for s in size_order]
    human_size_rates = [human_by_size.loc[s, 'acceptance_rate'] if s in human_by_size.index else 0 for s in size_order]
    
    x = np.arange(len(size_order))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, agent_size_rates, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax1.bar(x + width/2, human_size_rates, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax1.set_xlabel('PR Size')
    ax1.set_ylabel('Acceptance Rate (%)')
    ax1.set_title('(a) Acceptance Rate by PR Size')
    ax1.set_xticks(x)
    ax1.set_xticklabels([s.capitalize() for s in size_order])
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 3.2: TypeScript files changed distribution
    ax2 = axes[0, 1]
    
    agent_ts_files = agent_accuracy['ts_files_changed']
    human_ts_files = human_accuracy['ts_files_changed']
    
    # Create histogram
    bins = np.arange(0, min(agent_ts_files.max(), human_ts_files.max(), 20) + 2)
    
    ax2.hist([agent_ts_files, human_ts_files], bins=bins, 
             label=['AI Agent', 'Human'], color=['#FF6B6B', '#4ECDC4'],
             alpha=0.7, density=True)
    
    ax2.set_xlabel('Number of TypeScript Files Changed')
    ax2.set_ylabel('Density')
    ax2.set_title('(b) Distribution of TypeScript Files Changed')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3.3: Quality score composite
    ax3 = axes[1, 0]
    
    # Calculate quality score
    def calculate_quality_score(row):
        score = 0
        score += 2 if row['has_tests'] else 0
        score -= 1 if row['has_todo'] else 0
        score -= 2 if row['has_eslint_disable'] else 0
        score -= 3 if row['has_ts_ignore'] else 0
        score -= 2 if row['has_any_type'] else 0
        score += 1 if row['validator_agreed'] else 0
        score += row['validator_confidence']
        return score
    
    agent_accuracy['quality_score'] = agent_accuracy.apply(calculate_quality_score, axis=1)
    human_accuracy['quality_score'] = human_accuracy.apply(calculate_quality_score, axis=1)
    
    # Box plot comparison
    bp = ax3.boxplot([agent_accuracy['quality_score'], human_accuracy['quality_score']],
                      labels=['AI Agent', 'Human'],
                      patch_artist=True,
                      showmeans=True)
    
    for patch, color in zip(bp['boxes'], ['#FF6B6B', '#4ECDC4']):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax3.set_ylabel('Quality Score')
    ax3.set_title('(c) Composite Quality Score')
    ax3.grid(True, alpha=0.3)
    
    # 3.4: Acceptance probability model
    ax4 = axes[1, 1]
    
    # Calculate acceptance probability based on various factors
    factors = ['has_tests', 'has_ts_ignore', 'validator_agreed']
    
    acceptance_probs = []
    labels = []
    
    for factor in factors:
        agent_with = agent_accuracy[agent_accuracy[factor] == True]
        agent_without = agent_accuracy[agent_accuracy[factor] == False]
        human_with = human_accuracy[human_accuracy[factor] == True]
        human_without = human_accuracy[human_accuracy[factor] == False]
        
        agent_with_acc = agent_with['is_merged'].mean() * 100
        agent_without_acc = agent_without['is_merged'].mean() * 100
        human_with_acc = human_with['is_merged'].mean() * 100
        human_without_acc = human_without['is_merged'].mean() * 100
        
        acceptance_probs.append([agent_with_acc, agent_without_acc, human_with_acc, human_without_acc])
        labels.append(factor.replace('_', ' ').replace('has ', '').title())
    
    # Create grouped bar chart
    x = np.arange(len(labels))
    width = 0.2
    
    patterns = ['With', 'Without', 'With', 'Without']
    colors_plot = ['#FF6B6B', '#FF6B6B', '#4ECDC4', '#4ECDC4']
    alphas = [0.9, 0.5, 0.9, 0.5]
    
    for i in range(4):
        values = [acceptance_probs[j][i] for j in range(len(labels))]
        offset = (i - 1.5) * width
        label = f"{'AI' if i < 2 else 'Human'} {patterns[i]}"
        bars = ax4.bar(x + offset, values, width, label=label,
                      color=colors_plot[i], alpha=alphas[i])
    
    ax4.set_xlabel('Factor')
    ax4.set_ylabel('Acceptance Rate (%)')
    ax4.set_title('(d) Impact of Quality Factors on Acceptance')
    ax4.set_xticks(x)
    ax4.set_xticklabels(labels)
    ax4.legend(fontsize=7, loc='upper left')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('figures_rq3/fig3_accuracy_by_complexity.png', bbox_inches='tight')
    plt.close()

def figure4_temporal_analysis(agent_df, human_df):
    """Figure 4: Temporal patterns and trends"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Convert dates
    agent_df['created_date'] = pd.to_datetime(agent_df['created_at'], errors='coerce')
    human_df['created_date'] = pd.to_datetime(human_df['created_at'], errors='coerce')
    
    # 4.1: PR volume over time
    ax1 = axes[0, 0]
    
    # Group by month
    agent_monthly = agent_df.set_index('created_date').resample('M').size()
    human_monthly = human_df.set_index('created_date').resample('M').size()
    
    # Filter to common date range
    common_dates = agent_monthly.index.intersection(human_monthly.index)
    
    if len(common_dates) > 0:
        ax1.plot(agent_monthly.index, agent_monthly.values, 
                label='AI Agent', color='#FF6B6B', marker='o', alpha=0.7)
        ax1.plot(human_monthly.index, human_monthly.values,
                label='Human', color='#4ECDC4', marker='s', alpha=0.7)
        
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Number of PRs')
        ax1.set_title('(a) PR Volume Over Time')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
    else:
        ax1.text(0.5, 0.5, 'Insufficient temporal data',
                transform=ax1.transAxes, ha='center', va='center',
                fontsize=10, alpha=0.5)
    
    # 4.2: Acceptance rate trend
    ax2 = axes[0, 1]
    
    # Calculate rolling acceptance rate (based on merged_at field)
    agent_df['is_merged'] = agent_df['merged_at'].notna()
    human_df['is_merged'] = human_df['merged_at'].notna()
    
    # Filter out NaT values and sort by date
    agent_df_valid = agent_df[agent_df['created_date'].notna()].sort_values('created_date')
    human_df_valid = human_df[human_df['created_date'].notna()].sort_values('created_date')
    
    if len(agent_df_valid) > 0 and len(human_df_valid) > 0:
        agent_rolling = agent_df_valid.set_index('created_date')['is_merged'].rolling('30D').mean() * 100
        human_rolling = human_df_valid.set_index('created_date')['is_merged'].rolling('30D').mean() * 100
    else:
        agent_rolling = pd.Series()
        human_rolling = pd.Series()
    
    if len(agent_rolling) > 0 and len(human_rolling) > 0:
        ax2.plot(agent_rolling.index, agent_rolling.values,
                label='AI Agent', color='#FF6B6B', alpha=0.7)
        ax2.plot(human_rolling.index, human_rolling.values,
                label='Human', color='#4ECDC4', alpha=0.7)
        
        ax2.set_xlabel('Date')
        ax2.set_ylabel('30-Day Rolling Acceptance Rate (%)')
        ax2.set_title('(b) Acceptance Rate Trend')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='x', rotation=45)
    else:
        ax2.text(0.5, 0.5, 'Insufficient data for trend',
                transform=ax2.transAxes, ha='center', va='center',
                fontsize=10, alpha=0.5)
    
    # 4.3: Day of week analysis
    ax3 = axes[1, 0]
    
    agent_df['day_of_week'] = agent_df['created_date'].dt.dayofweek
    human_df['day_of_week'] = human_df['created_date'].dt.dayofweek
    
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    agent_by_day = agent_df.groupby('day_of_week').size()
    human_by_day = human_df.groupby('day_of_week').size()
    
    agent_day_counts = [agent_by_day.get(i, 0) for i in range(7)]
    human_day_counts = [human_by_day.get(i, 0) for i in range(7)]
    
    # Normalize to percentages
    agent_day_pct = [c/sum(agent_day_counts)*100 if sum(agent_day_counts) > 0 else 0 for c in agent_day_counts]
    human_day_pct = [c/sum(human_day_counts)*100 if sum(human_day_counts) > 0 else 0 for c in human_day_counts]
    
    x = np.arange(len(days))
    width = 0.35
    
    bars1 = ax3.bar(x - width/2, agent_day_pct, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax3.bar(x + width/2, human_day_pct, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax3.set_xlabel('Day of Week')
    ax3.set_ylabel('Percentage of PRs (%)')
    ax3.set_title('(c) PR Distribution by Day of Week')
    ax3.set_xticks(x)
    ax3.set_xticklabels(days)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4.4: Time to merge evolution
    ax4 = axes[1, 1]
    
    # Calculate monthly median time to merge
    agent_merged = agent_df[agent_df['merged_at'].notna()].copy()
    human_merged = human_df[human_df['merged_at'].notna()].copy()
    
    if len(agent_merged) > 0 and len(human_merged) > 0:
        agent_merged['merged_at'] = pd.to_datetime(agent_merged['merged_at'], errors='coerce')
        agent_merged['time_to_merge'] = (agent_merged['merged_at'] - agent_merged['created_date']).dt.total_seconds() / 3600
        
        human_merged['merged_at'] = pd.to_datetime(human_merged['merged_at'], errors='coerce')
        human_merged['time_to_merge'] = (human_merged['merged_at'] - human_merged['created_date']).dt.total_seconds() / 3600
        
        # Filter valid times
        agent_merged = agent_merged[agent_merged['time_to_merge'] > 0]
        human_merged = human_merged[human_merged['time_to_merge'] > 0]
        
        if len(agent_merged) > 0 and len(human_merged) > 0:
            agent_monthly_time = agent_merged.set_index('created_date')['time_to_merge'].resample('M').median()
            human_monthly_time = human_merged.set_index('created_date')['time_to_merge'].resample('M').median()
            
            ax4.plot(agent_monthly_time.index, agent_monthly_time.values,
                    label='AI Agent', color='#FF6B6B', marker='o', alpha=0.7)
            ax4.plot(human_monthly_time.index, human_monthly_time.values,
                    label='Human', color='#4ECDC4', marker='s', alpha=0.7)
            
            ax4.set_xlabel('Date')
            ax4.set_ylabel('Median Time to Merge (hours)')
            ax4.set_title('(d) Time to Merge Evolution')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            ax4.tick_params(axis='x', rotation=45)
        else:
            ax4.text(0.5, 0.5, 'Insufficient merge data',
                    transform=ax4.transAxes, ha='center', va='center',
                    fontsize=10, alpha=0.5)
    else:
        ax4.text(0.5, 0.5, 'No merged PRs for analysis',
                transform=ax4.transAxes, ha='center', va='center',
                fontsize=10, alpha=0.5)
    
    plt.tight_layout()
    plt.savefig('figures_rq3/fig4_temporal_analysis.png', bbox_inches='tight')
    plt.close()

def figure5_statistical_summary(agent_df, human_df, agent_accuracy, human_accuracy):
    """Figure 5: Comprehensive statistical summary"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 5.1: Key metrics comparison
    ax1 = axes[0, 0]
    
    agent_metrics = calculate_acceptance_metrics(agent_df)
    human_metrics = calculate_acceptance_metrics(human_df)
    
    metrics = ['Acceptance\nRate', 'Has Tests', 'Has @ts-ignore', 'Quality Score']
    
    agent_values = [
        agent_metrics['acceptance_rate'],
        agent_accuracy['has_tests'].mean() * 100,
        agent_accuracy['has_ts_ignore'].mean() * 100,
        agent_accuracy['quality_score'].mean() * 10  # Scale for visibility
    ]
    
    human_values = [
        human_metrics['acceptance_rate'],
        human_accuracy['has_tests'].mean() * 100,
        human_accuracy['has_ts_ignore'].mean() * 100,
        human_accuracy['quality_score'].mean() * 10  # Scale for visibility
    ]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, agent_values, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax1.bar(x + width/2, human_values, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax1.set_xlabel('Metric')
    ax1.set_ylabel('Value')
    ax1.set_title('(a) Key Metrics Comparison')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=8)
    
    # 5.2: Effect sizes
    ax2 = axes[0, 1]
    
    effect_metrics = ['Acceptance Rate', 'Has Tests', 'Quality Score', 'Confidence']
    effect_sizes = []
    
    # Calculate Cohen's d for each metric
    metrics_pairs = [
        (agent_metrics['acceptance_rate'], human_metrics['acceptance_rate']),
        (agent_accuracy['has_tests'].mean(), human_accuracy['has_tests'].mean()),
        (agent_accuracy['quality_score'], human_accuracy['quality_score']),
        (agent_accuracy['classifier_confidence'], human_accuracy['classifier_confidence'])
    ]
    
    for agent_data, human_data in metrics_pairs:
        if hasattr(agent_data, 'std'):
            pooled_std = np.sqrt((agent_data.std()**2 + human_data.std()**2) / 2)
            mean_diff = agent_data.mean() - human_data.mean()
        else:
            # For single values
            pooled_std = np.sqrt((agent_data**2 + human_data**2) / 2)
            mean_diff = agent_data - human_data
        
        if pooled_std > 0:
            cohens_d = mean_diff / pooled_std
        else:
            cohens_d = 0
        effect_sizes.append(cohens_d)
    
    colors = ['#E74C3C' if d > 0 else '#27AE60' for d in effect_sizes]
    
    bars = ax2.barh(range(len(effect_sizes)), effect_sizes, color=colors, alpha=0.7)
    
    ax2.set_yticks(range(len(effect_sizes)))
    ax2.set_yticklabels(effect_metrics)
    ax2.set_xlabel("Cohen's d (Effect Size)")
    ax2.set_title("(b) Effect Sizes: Agent vs Human")
    ax2.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax2.axvline(x=0.2, color='gray', linestyle='--', alpha=0.5)
    ax2.axvline(x=-0.2, color='gray', linestyle='--', alpha=0.5)
    ax2.grid(True, alpha=0.3)
    
    # 5.3: Statistical tests summary
    ax3 = axes[1, 0]
    ax3.axis('tight')
    ax3.axis('off')
    
    # Perform statistical tests
    test_results = []
    
    # Chi-square test for acceptance rates (if data available)
    if agent_metrics['merged_count'] > 0 or human_metrics['merged_count'] > 0:
        contingency_table = np.array([
            [max(1, agent_metrics['merged_count']), max(1, agent_metrics['closed_count'])],
            [max(1, human_metrics['merged_count']), max(1, human_metrics['closed_count'])]
        ])
        try:
            chi2, p_val_accept, _, _ = stats.chi2_contingency(contingency_table)
            test_results.append(['Acceptance Rate', 'Chi-square', f'{chi2:.2f}', f'{p_val_accept:.4f}',
                                '✓' if p_val_accept < 0.05 else '✗'])
        except ValueError:
            test_results.append(['Acceptance Rate', 'Chi-square', 'N/A', 'N/A', 'N/A'])
    else:
        test_results.append(['Acceptance Rate', 'Chi-square', 'N/A', 'N/A', 'N/A'])
    
    # Mann-Whitney U tests
    if len(agent_accuracy) > 0 and len(human_accuracy) > 0:
        u_stat, p_val_quality = stats.mannwhitneyu(agent_accuracy['quality_score'],
                                                   human_accuracy['quality_score'],
                                                   alternative='two-sided')
        test_results.append(['Quality Score', 'Mann-Whitney U', f'{u_stat:.2f}', f'{p_val_quality:.4f}',
                            '✓' if p_val_quality < 0.05 else '✗'])
        
        u_stat, p_val_conf = stats.mannwhitneyu(agent_accuracy['classifier_confidence'],
                                                human_accuracy['classifier_confidence'],
                                                alternative='two-sided')
        test_results.append(['Confidence', 'Mann-Whitney U', f'{u_stat:.2f}', f'{p_val_conf:.4f}',
                            '✓' if p_val_conf < 0.05 else '✗'])
    
    table = ax3.table(cellText=test_results,
                     colLabels=['Metric', 'Test', 'Statistic', 'p-value', 'Sig.'],
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
    
    ax3.set_title('(c) Statistical Tests Summary', pad=20)
    
    # 5.4: Summary metrics table
    ax4 = axes[1, 1]
    ax4.axis('tight')
    ax4.axis('off')
    
    summary_data = []
    
    summary_data.append(['Metric', 'AI Agent', 'Human', 'Difference'])
    summary_data.append(['Total PRs', f"{agent_metrics['total_prs']}", f"{human_metrics['total_prs']}", 
                        f"{agent_metrics['total_prs'] - human_metrics['total_prs']}"])
    summary_data.append(['Acceptance Rate', f"{agent_metrics['acceptance_rate']:.1f}%", 
                        f"{human_metrics['acceptance_rate']:.1f}%",
                        f"{agent_metrics['acceptance_rate'] - human_metrics['acceptance_rate']:.1f}%"])
    summary_data.append(['Median Time to Merge', f"{agent_metrics['median_time_to_merge']:.1f}h",
                        f"{human_metrics['median_time_to_merge']:.1f}h",
                        f"{agent_metrics['median_time_to_merge'] - human_metrics['median_time_to_merge']:.1f}h"])
    summary_data.append(['Has Tests', f"{agent_accuracy['has_tests'].mean()*100:.1f}%",
                        f"{human_accuracy['has_tests'].mean()*100:.1f}%",
                        f"{(agent_accuracy['has_tests'].mean() - human_accuracy['has_tests'].mean())*100:.1f}%"])
    summary_data.append(['Mean Quality Score', f"{agent_accuracy['quality_score'].mean():.2f}",
                        f"{human_accuracy['quality_score'].mean():.2f}",
                        f"{agent_accuracy['quality_score'].mean() - human_accuracy['quality_score'].mean():.2f}"])
    
    table = ax4.table(cellText=summary_data,
                     cellLoc='center',
                     loc='center',
                     bbox=[0, 0, 1, 1])
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.8)
    
    # Style the header
    for i in range(4):
        table[(0, i)].set_facecolor('#E8E8E8')
        table[(0, i)].set_text_props(weight='bold')
    
    ax4.set_title('(d) Summary Statistics', pad=20)
    
    plt.tight_layout()
    plt.savefig('figures_rq3/fig5_statistical_summary.png', bbox_inches='tight')
    plt.close()

def main():
    """Main analysis pipeline for RQ3"""
    print("=" * 60)
    print("RQ3 Analysis: Acceptance Rates and Code Accuracy")
    print("=" * 60)
    
    # Create output directory
    import os
    os.makedirs('figures_rq3', exist_ok=True)
    
    # Load and filter data
    agent_df, human_df = load_and_filter_data()
    
    # Calculate accuracy metrics
    print("\nCalculating accuracy metrics...")
    agent_accuracy = calculate_accuracy_metrics(agent_df)
    human_accuracy = calculate_accuracy_metrics(human_df)
    
    print(f"Agent accuracy metrics: {len(agent_accuracy)} PRs")
    print(f"Human accuracy metrics: {len(human_accuracy)} PRs")
    
    # Generate figures
    print("\nGenerating Figure 1: Acceptance rates analysis...")
    figure1_acceptance_rates(agent_df, human_df)
    
    print("\nGenerating Figure 2: Code quality metrics...")
    figure2_code_quality_metrics(agent_accuracy, human_accuracy)
    
    print("\nGenerating Figure 3: Accuracy by complexity...")
    figure3_accuracy_by_complexity(agent_accuracy, human_accuracy)
    
    print("\nGenerating Figure 4: Temporal analysis...")
    figure4_temporal_analysis(agent_df, human_df)
    
    print("\nGenerating Figure 5: Statistical summary...")
    figure5_statistical_summary(agent_df, human_df, agent_accuracy, human_accuracy)
    
    # Save processed data
    agent_accuracy.to_csv('figures_rq3/agent_accuracy_metrics.csv', index=False)
    human_accuracy.to_csv('figures_rq3/human_accuracy_metrics.csv', index=False)
    
    # Print final summary
    print("\n" + "=" * 60)
    print("Summary Statistics:")
    
    agent_metrics = calculate_acceptance_metrics(agent_df)
    human_metrics = calculate_acceptance_metrics(human_df)
    
    print(f"\nAcceptance Rates:")
    print(f"  AI Agent: {agent_metrics['acceptance_rate']:.1f}%")
    print(f"  Human: {human_metrics['acceptance_rate']:.1f}%")
    
    print(f"\nCode Quality Indicators:")
    print(f"  AI Agent - Has Tests: {agent_accuracy['has_tests'].mean()*100:.1f}%")
    print(f"  Human - Has Tests: {human_accuracy['has_tests'].mean()*100:.1f}%")
    print(f"  AI Agent - Has @ts-ignore: {agent_accuracy['has_ts_ignore'].mean()*100:.1f}%")
    print(f"  Human - Has @ts-ignore: {human_accuracy['has_ts_ignore'].mean()*100:.1f}%")
    
    print("\n" + "=" * 60)
    print("RQ3 Analysis Complete!")
    print("Figures saved in figures_rq3/")
    print("=" * 60)

if __name__ == "__main__":
    main()

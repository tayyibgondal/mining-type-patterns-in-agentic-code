"""
RQ2 Analysis: How do AI agents and human developers differ in their use 
of advanced type features and type safety patterns?

This script analyzes the use of advanced TypeScript features to understand
the sophistication of type system usage between AI agents and humans.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
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

# Define advanced TypeScript features based on official handbook
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

def extract_advanced_features(df):
    """Extract advanced TypeScript feature usage from patch text"""
    import re
    
    features_list = []
    
    for idx, row in df.iterrows():
        patch = str(row.get('patch_text', ''))
        
        # Count occurrences of each advanced feature
        feature_counts = {}
        for feature_name, pattern in ADVANCED_FEATURES.items():
            try:
                # Count in added lines only (lines starting with +)
                added_lines = [line for line in patch.split('\n') if line.startswith('+')]
                added_text = '\n'.join(added_lines)
                matches = re.findall(pattern, added_text, re.IGNORECASE)
                feature_counts[feature_name] = len(matches)
            except:
                feature_counts[feature_name] = 0
        
        # Calculate metrics
        total_features = sum(feature_counts.values())
        unique_features = sum(1 for v in feature_counts.values() if v > 0)
        
        # Add metadata
        feature_counts['id'] = row['id']
        feature_counts['developer_type'] = row['developer_type']
        feature_counts['agent'] = row.get('agent', 'Human')
        feature_counts['total_advanced_features'] = total_features
        feature_counts['unique_features_used'] = unique_features
        feature_counts['additions'] = row.get('additions', 0)
        feature_counts['deletions'] = row.get('deletions', 0)
        feature_counts['changes'] = row.get('changes', 0)
        
        # Calculate feature density (features per 100 lines of code)
        if feature_counts['changes'] > 0:
            feature_counts['feature_density'] = (total_features / feature_counts['changes']) * 100
        else:
            feature_counts['feature_density'] = 0
        
        features_list.append(feature_counts)
    
    return pd.DataFrame(features_list)

def figure1_feature_usage_overview(agent_features, human_features):
    """Figure 1: Overview of advanced feature usage"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 1.1: Total advanced features comparison (for PRs with features only)
    ax1 = axes[0, 0]
    
    agent_total = agent_features['total_advanced_features']
    human_total = human_features['total_advanced_features']
    
    # Filter non-zero values for better visualization
    agent_nonzero = agent_total[agent_total > 0]
    human_nonzero = human_total[human_total > 0]
    
    bp = ax1.boxplot([agent_nonzero, human_nonzero],
                      labels=['AI Agent', 'Human'],
                      patch_artist=True,
                      showmeans=True,
                      showfliers=False)  # Remove extreme outliers for better scale
    
    for patch, color in zip(bp['boxes'], ['#FF6B6B', '#4ECDC4']):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax1.set_ylabel('Total Advanced Features per PR')
    ax1.set_title('(a) Total Advanced Feature Usage\n(PRs with features only, outliers removed)')
    ax1.set_yscale('log')
    ax1.grid(True, alpha=0.3)
    
    # Add statistics text - median is more informative with skewed data
    ax1.text(0.02, 0.98, f'AI Median: {agent_nonzero.median():.1f} (Mean: {agent_nonzero.mean():.1f})\nHuman Median: {human_nonzero.median():.1f} (Mean: {human_nonzero.mean():.1f})',
             transform=ax1.transAxes, fontsize=8, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Add sample sizes
    ax1.text(0.98, 0.02, f'n={len(agent_nonzero)} AI, {len(human_nonzero)} Human',
             transform=ax1.transAxes, fontsize=7, ha='right', alpha=0.6)
    
    # 1.2: Feature diversity (unique features used)
    ax2 = axes[0, 1]
    
    agent_unique = agent_features['unique_features_used']
    human_unique = human_features['unique_features_used']
    
    # Count distribution
    max_features = max(agent_unique.max(), human_unique.max()) + 1
    agent_counts = [sum(agent_unique == i) for i in range(max_features)]
    human_counts = [sum(human_unique == i) for i in range(max_features)]
    
    x = np.arange(min(max_features, 15))  # Limit to 15 for readability
    width = 0.35
    
    bars1 = ax2.bar(x - width/2, [agent_counts[i] if i < len(agent_counts) else 0 for i in x], 
                    width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax2.bar(x + width/2, [human_counts[i] if i < len(human_counts) else 0 for i in x],
                    width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax2.set_xlabel('Number of Unique Features Used')
    ax2.set_ylabel('Number of PRs')
    ax2.set_title('(b) Feature Diversity Distribution')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 1.3: Feature density comparison
    ax3 = axes[1, 0]
    
    agent_density = agent_features[agent_features['feature_density'] > 0]['feature_density']
    human_density = human_features[human_features['feature_density'] > 0]['feature_density']
    
    # Create violin plot
    positions = [1, 2]
    parts = ax3.violinplot([agent_density.dropna(), human_density.dropna()],
                           positions=positions,
                           showmeans=True,
                           showmedians=True,
                           widths=0.7)
    
    for pc, color in zip(parts['bodies'], ['#FF6B6B', '#4ECDC4']):
        pc.set_facecolor(color)
        pc.set_alpha(0.7)
    
    ax3.set_xticks(positions)
    ax3.set_xticklabels(['AI Agent', 'Human'])
    ax3.set_ylabel('Feature Density (Features per 100 LoC)')
    ax3.set_title('(c) Feature Density Distribution')
    ax3.grid(True, alpha=0.3)
    
    # 1.4: Percentage of PRs using advanced features
    ax4 = axes[1, 1]
    
    agent_with_features = (agent_features['total_advanced_features'] > 0).mean() * 100
    human_with_features = (human_features['total_advanced_features'] > 0).mean() * 100
    
    categories = ['AI Agent', 'Human']
    percentages = [agent_with_features, human_with_features]
    colors = ['#FF6B6B', '#4ECDC4']
    
    bars = ax4.bar(categories, percentages, color=colors, alpha=0.7)
    
    # Add value labels
    for bar, pct in zip(bars, percentages):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{pct:.1f}%', ha='center', va='bottom')
    
    ax4.set_ylabel('Percentage of PRs (%)')
    ax4.set_title('(d) PRs Using Advanced Features')
    ax4.set_ylim(0, 100)
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('figures_rq2/fig1_feature_usage_overview.png', bbox_inches='tight')
    plt.close()
    
    # Statistical tests
    print("\n=== Statistical Tests for Advanced Features ===")
    print("Mann-Whitney U test for total features:")
    u_stat, p_val = stats.mannwhitneyu(agent_features['total_advanced_features'],
                                        human_features['total_advanced_features'],
                                        alternative='two-sided')
    print(f"  U-statistic: {u_stat:.2f}, p-value: {p_val:.6f}")

def figure2_individual_features(agent_features, human_features):
    """Figure 2: Individual feature comparison"""
    
    # Select top features to display
    top_features = ['generics', 'utility_types', 'type_guards', 'conditional_types',
                    'union_types', 'intersection_types', 'as_const', 'satisfies',
                    'keyof_typeof', 'optional_chaining', 'nullish_coalescing', 'type_assertions']
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 2.1: Feature usage frequency
    ax1 = axes[0, 0]
    
    agent_means = []
    human_means = []
    
    for feature in top_features:
        agent_means.append(agent_features[feature].mean())
        human_means.append(human_features[feature].mean())
    
    x = np.arange(len(top_features))
    width = 0.35
    
    bars1 = ax1.barh(x - width/2, agent_means, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax1.barh(x + width/2, human_means, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax1.set_yticks(x)
    ax1.set_yticklabels(top_features, fontsize=8)
    ax1.set_xlabel('Mean Usage per PR')
    ax1.set_title('(a) Mean Feature Usage Frequency')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2.2: Feature adoption rate
    ax2 = axes[0, 1]
    
    agent_adoption = []
    human_adoption = []
    
    for feature in top_features:
        agent_adoption.append((agent_features[feature] > 0).mean() * 100)
        human_adoption.append((human_features[feature] > 0).mean() * 100)
    
    # Sort by difference
    differences = [a - h for a, h in zip(agent_adoption, human_adoption)]
    sorted_indices = np.argsort(differences)[::-1]
    
    sorted_features = [top_features[i] for i in sorted_indices]
    sorted_agent = [agent_adoption[i] for i in sorted_indices]
    sorted_human = [human_adoption[i] for i in sorted_indices]
    
    x = np.arange(len(sorted_features))
    
    bars1 = ax2.barh(x - width/2, sorted_agent, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax2.barh(x + width/2, sorted_human, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax2.set_yticks(x)
    ax2.set_yticklabels(sorted_features, fontsize=8)
    ax2.set_xlabel('Adoption Rate (%)')
    ax2.set_title('(b) Feature Adoption Rate (% of PRs)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 2.3: Feature complexity heatmap
    ax3 = axes[1, 0]
    
    # Define feature complexity categories
    basic_features = ['union_types', 'type_assertions', 'optional_chaining', 'nullish_coalescing']
    intermediate_features = ['generics', 'utility_types', 'keyof_typeof', 'as_const']
    advanced_features = ['conditional_types', 'type_guards', 'satisfies', 'intersection_types']
    
    complexity_data = []
    
    for features, complexity in [(basic_features, 'Basic'),
                                 (intermediate_features, 'Intermediate'),
                                 (advanced_features, 'Advanced')]:
        agent_score = sum(agent_features[f].mean() for f in features if f in agent_features.columns)
        human_score = sum(human_features[f].mean() for f in features if f in human_features.columns)
        complexity_data.append([agent_score, human_score])
    
    complexity_df = pd.DataFrame(complexity_data,
                                 columns=['AI Agent', 'Human'],
                                 index=['Basic', 'Intermediate', 'Advanced'])
    
    sns.heatmap(complexity_df, annot=True, fmt='.2f', cmap='YlOrRd', ax=ax3,
                cbar_kws={'label': 'Mean Usage'})
    ax3.set_title('(c) Feature Usage by Complexity Level')
    ax3.set_xlabel('Developer Type')
    ax3.set_ylabel('Feature Complexity')
    
    # 2.4: Feature correlation matrix
    ax4 = axes[1, 1]
    
    # Calculate correlation between feature usage
    selected_features = ['generics', 'utility_types', 'conditional_types', 
                        'type_guards', 'union_types', 'as_const']
    
    agent_corr = agent_features[selected_features].corr()
    
    sns.heatmap(agent_corr, annot=True, fmt='.2f', cmap='coolwarm',
                center=0, ax=ax4, cbar_kws={'label': 'Correlation'},
                vmin=-1, vmax=1)
    ax4.set_title('(d) Feature Co-occurrence (AI Agent)')
    ax4.set_xticklabels(ax4.get_xticklabels(), rotation=45, ha='right')
    ax4.set_yticklabels(ax4.get_yticklabels(), rotation=0)
    
    plt.tight_layout()
    plt.savefig('figures_rq2/fig2_individual_features.png', bbox_inches='tight')
    plt.close()

def figure3_agent_comparison(agent_features, human_features):
    """Figure 3: Individual AI agent comparison"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Get unique agents
    ai_agents = agent_features['agent'].unique()
    ai_agents = [a for a in ai_agents if a != 'Human']
    
    # 3.1: Total features by agent
    ax1 = axes[0, 0]
    
    agent_totals = []
    agent_names = []
    
    for agent in ai_agents:
        agent_data = agent_features[agent_features['agent'] == agent]['total_advanced_features']
        if len(agent_data) > 0:
            agent_totals.append(agent_data)
            agent_names.append(agent)
    
    # Add human data
    agent_totals.append(human_features['total_advanced_features'])
    agent_names.append('Human')
    
    bp = ax1.boxplot(agent_totals, labels=agent_names, patch_artist=True, showmeans=True)
    
    colors = plt.cm.Set3(np.linspace(0, 1, len(agent_names)))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax1.set_ylabel('Total Advanced Features per PR')
    ax1.set_title('(a) Feature Usage by AI Agent')
    ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha='right')
    ax1.grid(True, alpha=0.3)
    
    # 3.2: Feature diversity by agent
    ax2 = axes[0, 1]
    
    diversity_means = []
    diversity_stds = []
    
    for agent in agent_names[:-1]:  # Exclude human for now
        agent_data = agent_features[agent_features['agent'] == agent]['unique_features_used']
        diversity_means.append(agent_data.mean())
        diversity_stds.append(agent_data.std())
    
    # Add human
    diversity_means.append(human_features['unique_features_used'].mean())
    diversity_stds.append(human_features['unique_features_used'].std())
    
    x = np.arange(len(agent_names))
    bars = ax2.bar(x, diversity_means, yerr=diversity_stds, color=colors, alpha=0.7, capsize=5)
    
    ax2.set_xlabel('Developer/Agent')
    ax2.set_ylabel('Mean Unique Features Used')
    ax2.set_title('(b) Feature Diversity by Agent')
    ax2.set_xticks(x)
    ax2.set_xticklabels(agent_names, rotation=45, ha='right')
    ax2.grid(True, alpha=0.3)
    
    # Add value labels
    for bar, mean in zip(bars, diversity_means):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{mean:.2f}', ha='center', va='bottom', fontsize=8)
    
    # 3.3: Agent-specific feature preferences
    ax3 = axes[1, 0]
    
    # Select key features for comparison
    key_features = ['generics', 'utility_types', 'conditional_types', 'type_guards']
    
    feature_preferences = []
    
    for agent in agent_names[:-1]:  # AI agents only
        agent_data = agent_features[agent_features['agent'] == agent]
        preferences = []
        for feature in key_features:
            pref = (agent_data[feature] > 0).mean()
            preferences.append(pref)
        feature_preferences.append(preferences)
    
    # Add human preferences
    human_prefs = []
    for feature in key_features:
        pref = (human_features[feature] > 0).mean()
        human_prefs.append(pref)
    feature_preferences.append(human_prefs)
    
    # Create grouped bar chart
    x = np.arange(len(key_features))
    width = 0.15
    
    for i, (agent, prefs) in enumerate(zip(agent_names, feature_preferences)):
        offset = (i - len(agent_names)/2) * width
        bars = ax3.bar(x + offset, prefs, width, label=agent, color=colors[i], alpha=0.7)
    
    ax3.set_xlabel('Feature Type')
    ax3.set_ylabel('Adoption Rate')
    ax3.set_title('(c) Feature Preferences by Agent')
    ax3.set_xticks(x)
    ax3.set_xticklabels(key_features, rotation=45, ha='right')
    ax3.legend(fontsize=8, loc='upper right')
    ax3.grid(True, alpha=0.3)
    
    # 3.4: Agent sophistication score
    ax4 = axes[1, 1]
    
    # Calculate sophistication score (weighted by feature complexity)
    complexity_weights = {
        'generics': 2.0,
        'conditional_types': 3.0,
        'mapped_types': 3.0,
        'type_guards': 2.5,
        'utility_types': 1.5,
        'satisfies': 2.5,
        'template_literals': 2.0,
        'union_types': 1.0,
        'intersection_types': 1.5,
        'as_const': 1.5
    }
    
    sophistication_scores = []
    
    for agent in agent_names[:-1]:
        agent_data = agent_features[agent_features['agent'] == agent]
        score = 0
        for feature, weight in complexity_weights.items():
            if feature in agent_data.columns:
                score += agent_data[feature].mean() * weight
        sophistication_scores.append(score)
    
    # Human score
    human_score = 0
    for feature, weight in complexity_weights.items():
        if feature in human_features.columns:
            human_score += human_features[feature].mean() * weight
    sophistication_scores.append(human_score)
    
    # Sort by score
    sorted_indices = np.argsort(sophistication_scores)[::-1]
    sorted_agents = [agent_names[i] for i in sorted_indices]
    sorted_scores = [sophistication_scores[i] for i in sorted_indices]
    sorted_colors = [colors[i] for i in sorted_indices]
    
    bars = ax4.barh(range(len(sorted_agents)), sorted_scores, color=sorted_colors, alpha=0.7)
    
    ax4.set_yticks(range(len(sorted_agents)))
    ax4.set_yticklabels(sorted_agents)
    ax4.set_xlabel('Sophistication Score')
    ax4.set_title('(d) Type System Sophistication Score')
    ax4.grid(True, alpha=0.3)
    
    # Add value labels
    for bar, score in zip(bars, sorted_scores):
        width = bar.get_width()
        ax4.text(width, bar.get_y() + bar.get_height()/2.,
                f'{score:.2f}', ha='left', va='center', fontsize=8)
    
    plt.tight_layout()
    plt.savefig('figures_rq2/fig3_agent_comparison.png', bbox_inches='tight')
    plt.close()

def figure4_pattern_analysis(agent_features, human_features):
    """Figure 4: Type safety pattern analysis"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 4.1: Type safety indicators
    ax1 = axes[0, 0]
    
    # Define type safety indicators
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
    
    bars1 = ax1.bar(x - width/2, agent_safety, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax1.bar(x + width/2, human_safety, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax1.set_xlabel('Type Safety Feature')
    ax1.set_ylabel('Usage Rate (%)')
    ax1.set_title('(a) Type Safety Feature Adoption')
    ax1.set_xticks(x)
    ax1.set_xticklabels(feature_names, rotation=45, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 4.2: Modern vs Legacy patterns
    ax2 = axes[0, 1]
    
    modern_features = ['optional_chaining', 'nullish_coalescing', 'satisfies', 'template_literals']
    legacy_features = ['type_assertions', 'namespace_types', 'enum_types']
    
    agent_modern = sum(agent_features[f].mean() for f in modern_features if f in agent_features.columns)
    agent_legacy = sum(agent_features[f].mean() for f in legacy_features if f in agent_features.columns)
    human_modern = sum(human_features[f].mean() for f in modern_features if f in human_features.columns)
    human_legacy = sum(human_features[f].mean() for f in legacy_features if f in human_features.columns)
    
    categories = ['Modern Patterns', 'Legacy Patterns']
    agent_vals = [agent_modern, agent_legacy]
    human_vals = [human_modern, human_legacy]
    
    x = np.arange(len(categories))
    
    bars1 = ax2.bar(x - width/2, agent_vals, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax2.bar(x + width/2, human_vals, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax2.set_ylabel('Mean Usage per PR')
    ax2.set_title('(b) Modern vs Legacy Pattern Usage')
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}', ha='center', va='bottom', fontsize=8)
    
    # 4.3: Complexity distribution (based on unique features used)
    ax3 = axes[1, 0]
    
    # Define complexity levels based on unique features (better indicator of sophistication)
    def categorize_complexity(row):
        unique = row['unique_features_used']
        if unique == 0:
            return 'None'
        elif unique <= 2:
            return 'Low (1-2)'
        elif unique <= 5:
            return 'Medium (3-5)'
        else:
            return 'High (6+)'
    
    agent_features['complexity'] = agent_features.apply(categorize_complexity, axis=1)
    human_features['complexity'] = human_features.apply(categorize_complexity, axis=1)
    
    complexity_order = ['None', 'Low (1-2)', 'Medium (3-5)', 'High (6+)']
    
    agent_complexity = agent_features['complexity'].value_counts()
    human_complexity = human_features['complexity'].value_counts()
    
    agent_pct = [agent_complexity.get(c, 0)/len(agent_features)*100 for c in complexity_order]
    human_pct = [human_complexity.get(c, 0)/len(human_features)*100 for c in complexity_order]
    
    x = np.arange(len(complexity_order))
    
    bars1 = ax3.bar(x - width/2, agent_pct, width, label='AI Agent', color='#FF6B6B', alpha=0.7)
    bars2 = ax3.bar(x + width/2, human_pct, width, label='Human', color='#4ECDC4', alpha=0.7)
    
    ax3.set_xlabel('Type System Complexity Level')
    ax3.set_ylabel('Percentage of PRs (%)')
    ax3.set_title('(c) PR Type System Sophistication\n(Based on unique advanced features)')
    ax3.set_xticks(x)
    ax3.set_xticklabels(complexity_order, rotation=15, ha='right', fontsize=8)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 1:  # Only show if >1%
                ax3.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%', ha='center', va='bottom', fontsize=7)
    
    # 4.4: PCA visualization
    ax4 = axes[1, 1]
    
    # Prepare data for PCA
    feature_cols = [col for col in ADVANCED_FEATURES.keys() 
                   if col in agent_features.columns and col in human_features.columns]
    
    combined_data = pd.concat([
        agent_features[feature_cols + ['developer_type']],
        human_features[feature_cols + ['developer_type']]
    ])
    
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(combined_data[feature_cols])
    
    # Perform PCA
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    
    # Plot
    agent_mask = combined_data['developer_type'] == 'AI Agent'
    human_mask = combined_data['developer_type'] == 'Human'
    
    ax4.scatter(X_pca[agent_mask, 0], X_pca[agent_mask, 1], 
               alpha=0.5, color='#FF6B6B', label='AI Agent', s=10)
    ax4.scatter(X_pca[human_mask, 0], X_pca[human_mask, 1],
               alpha=0.5, color='#4ECDC4', label='Human', s=10)
    
    ax4.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
    ax4.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
    ax4.set_title('(d) PCA of Advanced Feature Usage')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('figures_rq2/fig4_pattern_analysis.png', bbox_inches='tight')
    plt.close()
    
    print(f"\nPCA Explained Variance: PC1={pca.explained_variance_ratio_[0]*100:.1f}%, PC2={pca.explained_variance_ratio_[1]*100:.1f}%")

def figure5_statistical_analysis(agent_features, human_features):
    """Figure 5: Comprehensive statistical analysis"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 5.1: Effect sizes for key features
    ax1 = axes[0, 0]
    
    key_features = ['generics', 'utility_types', 'conditional_types', 'type_guards',
                   'union_types', 'satisfies', 'as_const', 'keyof_typeof']
    
    effect_sizes = []
    feature_labels = []
    
    for feature in key_features:
        if feature in agent_features.columns and feature in human_features.columns:
            agent_data = agent_features[feature]
            human_data = human_features[feature]
            
            # Calculate Cohen's d
            pooled_std = np.sqrt((agent_data.std()**2 + human_data.std()**2) / 2)
            if pooled_std > 0:
                cohens_d = (agent_data.mean() - human_data.mean()) / pooled_std
                effect_sizes.append(cohens_d)
                feature_labels.append(feature.replace('_', ' ').title())
    
    # Sort by effect size
    sorted_indices = np.argsort(effect_sizes)
    sorted_effects = [effect_sizes[i] for i in sorted_indices]
    sorted_labels = [feature_labels[i] for i in sorted_indices]
    
    colors = ['#E74C3C' if d > 0 else '#27AE60' for d in sorted_effects]
    
    bars = ax1.barh(range(len(sorted_effects)), sorted_effects, color=colors, alpha=0.7)
    
    ax1.set_yticks(range(len(sorted_effects)))
    ax1.set_yticklabels(sorted_labels, fontsize=8)
    ax1.set_xlabel("Cohen's d (Effect Size)")
    ax1.set_title("(a) Effect Sizes for Advanced Features")
    ax1.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax1.axvline(x=0.2, color='gray', linestyle='--', alpha=0.5)
    ax1.axvline(x=-0.2, color='gray', linestyle='--', alpha=0.5)
    ax1.grid(True, alpha=0.3)
    
    # Add annotations
    ax1.text(0.3, len(sorted_effects)-0.5, 'AI > Human', fontsize=8, alpha=0.5)
    ax1.text(-0.3, len(sorted_effects)-0.5, 'Human > AI', fontsize=8, alpha=0.5)
    
    # 5.2: Statistical significance matrix
    ax2 = axes[0, 1]
    
    # Perform statistical tests
    p_values = []
    test_features = key_features[:6]  # Limit for readability
    
    for feature in test_features:
        if feature in agent_features.columns:
            _, p_val = stats.mannwhitneyu(agent_features[feature],
                                          human_features[feature],
                                          alternative='two-sided')
            p_values.append(p_val)
    
    # Create significance matrix
    sig_matrix = np.array(p_values).reshape(-1, 1)
    
    # Define significance levels
    sig_levels = sig_matrix.copy()
    sig_levels[sig_matrix < 0.001] = 3  # ***
    sig_levels[(sig_matrix >= 0.001) & (sig_matrix < 0.01)] = 2  # **
    sig_levels[(sig_matrix >= 0.01) & (sig_matrix < 0.05)] = 1  # *
    sig_levels[sig_matrix >= 0.05] = 0  # n.s.
    
    im = ax2.imshow(sig_levels, cmap='RdYlGn_r', vmin=0, vmax=3, aspect='auto')
    
    ax2.set_yticks(range(len(test_features)))
    ax2.set_yticklabels([f.replace('_', ' ').title() for f in test_features], fontsize=8)
    ax2.set_xticks([0])
    ax2.set_xticklabels(['p-value'])
    ax2.set_title('(b) Statistical Significance')
    
    # Add text annotations
    for i in range(len(test_features)):
        p = p_values[i]
        if p < 0.001:
            text = '***'
        elif p < 0.01:
            text = '**'
        elif p < 0.05:
            text = '*'
        else:
            text = 'n.s.'
        ax2.text(0, i, f'{text}\n({p:.3f})', ha='center', va='center', fontsize=8)
    
    # 5.3: Correlation analysis
    ax3 = axes[1, 0]
    
    # Calculate correlations between features and PR metrics
    correlation_features = ['total_advanced_features', 'unique_features_used', 
                           'feature_density', 'additions', 'deletions']
    
    if all(f in agent_features.columns for f in correlation_features):
        corr_matrix = agent_features[correlation_features].corr()
        
        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm',
                   center=0, ax=ax3, cbar_kws={'label': 'Correlation'},
                   vmin=-1, vmax=1)
        ax3.set_title('(c) Feature Correlations (AI Agent)')
        ax3.set_xticklabels(ax3.get_xticklabels(), rotation=45, ha='right', fontsize=8)
        ax3.set_yticklabels(ax3.get_yticklabels(), rotation=0, fontsize=8)
    
    # 5.4: Summary statistics table
    ax4 = axes[1, 1]
    ax4.axis('tight')
    ax4.axis('off')
    
    # Create comprehensive summary
    summary_data = []
    
    metrics = ['Total Features', 'Unique Features', 'Feature Density', '% with Features']
    
    for metric in metrics:
        if metric == 'Total Features':
            agent_val = f"{agent_features['total_advanced_features'].mean():.2f} ± {agent_features['total_advanced_features'].std():.2f}"
            human_val = f"{human_features['total_advanced_features'].mean():.2f} ± {human_features['total_advanced_features'].std():.2f}"
        elif metric == 'Unique Features':
            agent_val = f"{agent_features['unique_features_used'].mean():.2f} ± {agent_features['unique_features_used'].std():.2f}"
            human_val = f"{human_features['unique_features_used'].mean():.2f} ± {human_features['unique_features_used'].std():.2f}"
        elif metric == 'Feature Density':
            agent_val = f"{agent_features['feature_density'].mean():.2f} ± {agent_features['feature_density'].std():.2f}"
            human_val = f"{human_features['feature_density'].mean():.2f} ± {human_features['feature_density'].std():.2f}"
        else:  # % with Features
            agent_val = f"{(agent_features['total_advanced_features'] > 0).mean()*100:.1f}%"
            human_val = f"{(human_features['total_advanced_features'] > 0).mean()*100:.1f}%"
        
        summary_data.append([metric, agent_val, human_val])
    
    table = ax4.table(cellText=summary_data,
                     colLabels=['Metric', 'AI Agent', 'Human'],
                     cellLoc='center',
                     loc='center',
                     bbox=[0, 0, 1, 1])
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.8)
    
    # Style the header
    for i in range(3):
        table[(0, i)].set_facecolor('#E8E8E8')
        table[(0, i)].set_text_props(weight='bold')
    
    ax4.set_title('(d) Summary Statistics', pad=20)
    
    plt.tight_layout()
    plt.savefig('figures_rq2/fig5_statistical_analysis.png', bbox_inches='tight')
    plt.close()

def main():
    """Main analysis pipeline for RQ2"""
    print("=" * 60)
    print("RQ2 Analysis: Advanced Type Features Comparison")
    print("=" * 60)
    
    # Load and filter data
    agent_df, human_df = load_and_filter_data()
    
    # Extract advanced features
    print("\nExtracting advanced TypeScript features...")
    agent_features = extract_advanced_features(agent_df)
    human_features = extract_advanced_features(human_df)
    
    print(f"Agent features extracted: {len(agent_features)} PRs")
    print(f"Human features extracted: {len(human_features)} PRs")
    
    # Generate figures
    print("\nGenerating Figure 1: Feature usage overview...")
    figure1_feature_usage_overview(agent_features, human_features)
    
    print("\nGenerating Figure 2: Individual feature comparison...")
    figure2_individual_features(agent_features, human_features)
    
    print("\nGenerating Figure 3: Agent-specific comparison...")
    figure3_agent_comparison(agent_features, human_features)
    
    print("\nGenerating Figure 4: Pattern analysis...")
    figure4_pattern_analysis(agent_features, human_features)
    
    print("\nGenerating Figure 5: Statistical analysis...")
    figure5_statistical_analysis(agent_features, human_features)
    
    # Save processed data
    agent_features.to_csv('figures_rq2/agent_advanced_features.csv', index=False)
    human_features.to_csv('figures_rq2/human_advanced_features.csv', index=False)
    
    print("\n" + "=" * 60)
    print("RQ2 Analysis Complete!")
    print("Figures saved in figures_rq2/")
    print("=" * 60)

if __name__ == "__main__":
    main()

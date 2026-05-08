"""
RQ2 (Rust): How do AI agents and human developers differ in their use of
advanced Rust type features?

For each PR, count usage of advanced Rust type features (generics, lifetimes,
trait bounds, where clauses, impl/dyn Trait, derive, smart pointers, etc.) on
the ADDED lines of the patch. Compare AI vs Human means + per-feature
breakdown via Mann-Whitney U test.
"""

import os
import re
import json
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

warnings.filterwarnings('ignore')

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(HERE, '..', '..', 'datasets', 'rust_data'))
OUT_DIR = os.path.join(HERE, 'figures_rq2')
os.makedirs(OUT_DIR, exist_ok=True)

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 11

COLOR_AI = '#E74C3C'
COLOR_HUMAN = '#3498DB'

# Same patterns as the extractors so AI and Human counts are comparable.
RUST_FEATURES = {
    'generics': r'<[^<>]+>',
    'lifetimes': r"'[a-zA-Z_]\w*\b",
    'trait_bound': r'<[^<>]*\b\w+\s*:\s*[A-Z]\w*[^<>]*>',
    'where_clause': r'\bwhere\s+\w+\s*:',
    'impl_trait': r'\bimpl\s+[A-Z]\w*',
    'dyn_trait': r'\bdyn\s+[A-Z]\w*',
    'box_dyn': r'\bBox\s*<\s*dyn\s+',
    'type_alias': r'\btype\s+[A-Z]\w*\s*(<[^>]*>)?\s*=',
    'phantom_data': r'\bPhantomData\s*<',
    'derive': r'#\[derive\([^\)]+\)\]',
    'match_expr': r'\bmatch\s+\w',
    'if_let': r'\b(?:if|while)\s+let\b',
    'enum_def': r'\benum\s+[A-Z]\w*',
    'struct_def': r'\bstruct\s+[A-Z]\w*',
    'trait_def': r'\btrait\s+[A-Z]\w*',
    'impl_block': r'\bimpl(?:\s*<[^>]+>)?\s+[A-Z]\w*',
    'send_sync': r'\b(?:Send|Sync)\b',
    'smart_pointer': r'\b(?:Arc|Rc|Mutex|RwLock|RefCell|Cell)\s*<',
    'option_result': r'\b(?:Option|Result)\s*<',
    'unsafe_impl': r'\bunsafe\s+impl\b',
    'transmute': r'\bmem::transmute\b|\btransmute\s*::\s*<',
    'any_trait': r'\b(?:std::)?any::Any\b|\bdyn\s+Any\b',
}

COMPILED = {name: re.compile(pat) for name, pat in RUST_FEATURES.items()}


def load_data():
    agent_path = os.path.join(DATA_DIR, 'rust_classified_type_prs.csv')
    human_path = os.path.join(DATA_DIR, 'human_rust_classified_type_prs.csv')

    agent_df = pd.read_csv(agent_path)
    human_df = pd.read_csv(human_path)

    if 'final_is_type_related' in agent_df.columns:
        agent_df = agent_df[agent_df['final_is_type_related'] == True]
    if 'final_is_type_related' in human_df.columns:
        human_df = human_df[human_df['final_is_type_related'] == True]

    print(f"Type-related PRs: AI={len(agent_df)}, Human={len(human_df)}")
    return agent_df, human_df


def extract_features_for_pr(patch_text):
    if pd.isna(patch_text):
        return {name: 0 for name in RUST_FEATURES}
    added = '\n'.join(
        line[1:] for line in str(patch_text).split('\n')
        if line.startswith('+') and not line.startswith('+++')
    )
    return {name: len(pat.findall(added)) for name, pat in COMPILED.items()}


def extract_features(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Extract per-PR feature counts. Reuse pre-computed columns when available."""
    rows = []
    feature_cols = list(RUST_FEATURES.keys())

    for _, r in df.iterrows():
        # Map pre-computed extractor columns onto the analysis-side names where
        # they exist; fallback to recomputing from patch_text otherwise.
        mapping = {
            'generics': 'generics_count',
            'lifetimes': 'lifetime_count',
            'trait_bound': 'trait_bound_count',
            'where_clause': 'where_clause_count',
            'impl_trait': 'impl_trait_count',
            'dyn_trait': 'dyn_trait_count',
            'box_dyn': 'box_dyn_count',
            'type_alias': 'type_alias_count',
            'phantom_data': 'phantom_data_count',
            'derive': 'derive_count',
            'match_expr': 'match_count',
            'if_let': 'if_let_count',
            'enum_def': 'enum_count',
            'struct_def': 'struct_count',
            'trait_def': 'trait_count',
            'impl_block': 'impl_block_count',
            'send_sync': 'send_sync_count',
            'smart_pointer': 'smart_pointer_count',
            'option_result': 'option_result_count',
            'unsafe_impl': 'unsafe_impl_count',
            'transmute': 'transmute_count',
            'any_trait': 'any_trait_count',
        }

        counts = {}
        if all(c in r.index and not pd.isna(r[c]) for c in mapping.values()):
            for k, v in mapping.items():
                counts[k] = int(r[v])
        else:
            counts = extract_features_for_pr(r.get('patch_text', ''))

        counts['id'] = r.get('id')
        counts['agent'] = r.get('agent', label)
        counts['developer_type'] = label
        counts['total_features'] = sum(counts[k] for k in feature_cols)
        counts['unique_features'] = sum(1 for k in feature_cols if counts[k] > 0)
        rows.append(counts)

    return pd.DataFrame(rows)


def run_stats(agent_feat, human_feat):
    a_total = agent_feat['total_features'].values
    h_total = human_feat['total_features'].values

    if len(a_total) > 0 and len(h_total) > 0:
        u, p = stats.mannwhitneyu(a_total, h_total, alternative='two-sided')
    else:
        u, p = float('nan'), float('nan')

    nx, ny = len(a_total), len(h_total)
    if nx >= 2 and ny >= 2:
        vx, vy = np.var(a_total, ddof=1), np.var(h_total, ddof=1)
        pooled = np.sqrt(((nx - 1) * vx + (ny - 1) * vy) / (nx + ny - 2))
        d = (np.mean(a_total) - np.mean(h_total)) / pooled if pooled != 0 else 0.0
    else:
        d = float('nan')

    print(f"\n[RQ2] Total advanced features per PR")
    print(f"  AI:    n={nx:,}, mean={np.mean(a_total):.2f} (per PR)")
    print(f"  Human: n={ny:,}, mean={np.mean(h_total):.2f} (per PR)")
    print(f"  Mann-Whitney U: U={u:.0f}, p={p:.4g}")
    print(f"  Cohen's d:      {d:.3f}")

    # Per-feature p-values
    per_feat = []
    for feat in RUST_FEATURES:
        a = agent_feat[feat].values
        h = human_feat[feat].values
        if len(a) > 0 and len(h) > 0 and (np.any(a > 0) or np.any(h > 0)):
            try:
                u_f, p_f = stats.mannwhitneyu(a, h, alternative='two-sided')
            except Exception:
                u_f, p_f = float('nan'), float('nan')
        else:
            u_f, p_f = float('nan'), float('nan')
        per_feat.append({
            'feature': feat,
            'ai_mean': float(np.mean(a)) if len(a) else 0.0,
            'human_mean': float(np.mean(h)) if len(h) else 0.0,
            'mann_whitney_u': float(u_f) if not np.isnan(u_f) else None,
            'p_value': float(p_f) if not np.isnan(p_f) else None,
        })

    return {
        'overall': {
            'ai_n': int(nx), 'human_n': int(ny),
            'ai_mean': float(np.mean(a_total)) if nx else 0.0,
            'human_mean': float(np.mean(h_total)) if ny else 0.0,
            'mann_whitney_u': float(u) if not np.isnan(u) else None,
            'p_value': float(p) if not np.isnan(p) else None,
            'cohens_d': float(d) if not np.isnan(d) else None,
        },
        'per_feature': per_feat,
    }


def plot_feature_means(agent_feat, human_feat):
    feature_cols = list(RUST_FEATURES.keys())
    ai_means = [agent_feat[f].mean() for f in feature_cols]
    hu_means = [human_feat[f].mean() for f in feature_cols]
    labels = [f.replace('_', ' ').title() for f in feature_cols]

    fig, ax = plt.subplots(figsize=(10, 9))
    y = np.arange(len(labels))
    height = 0.4

    ax.barh(y + height / 2, ai_means, height, label='AI Agent',
            color=COLOR_AI, alpha=0.85, edgecolor='black', linewidth=1.0)
    ax.barh(y - height / 2, hu_means, height, label='Human',
            color=COLOR_HUMAN, alpha=0.85, edgecolor='black', linewidth=1.0)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontweight='bold')
    ax.set_xlabel('Mean Usage per PR', fontweight='bold')
    ax.set_title('Rust: Advanced Type Feature Usage', fontweight='bold')
    ax.legend(loc='lower right', frameon=True, shadow=True)
    ax.grid(True, alpha=0.3, axis='x')

    out = os.path.join(OUT_DIR, 'rq2_feature_means.png')
    plt.tight_layout()
    plt.savefig(out, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {out}")


def plot_agent_heatmap(agent_feat, human_feat):
    """Heatmap of mean feature usage by agent (rows) x feature (cols)."""
    feature_cols = list(RUST_FEATURES.keys())
    rows = []
    index = []

    for agent in sorted(agent_feat['agent'].dropna().unique()):
        sub = agent_feat[agent_feat['agent'] == agent]
        rows.append([sub[f].mean() for f in feature_cols])
        index.append(str(agent))

    rows.append([human_feat[f].mean() for f in feature_cols])
    index.append('Human')

    mat = pd.DataFrame(rows, index=index, columns=feature_cols)

    fig, ax = plt.subplots(figsize=(14, max(4, 0.5 * len(index) + 2)))
    sns.heatmap(mat, annot=True, fmt='.2f', cmap='Reds',
                cbar_kws={'label': 'Mean per PR'}, ax=ax, linewidths=0.5)
    ax.set_xlabel('Feature', fontweight='bold')
    ax.set_ylabel('Developer / Agent', fontweight='bold')
    ax.set_title('Rust: Advanced Feature Usage by Agent', fontweight='bold')
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)

    out = os.path.join(OUT_DIR, 'rq2_feature_heatmap.png')
    plt.tight_layout()
    plt.savefig(out, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {out}")
    return mat


def plot_diversity(agent_feat, human_feat):
    """Mean unique-features per PR by agent."""
    fig, ax = plt.subplots(figsize=(10, 6))

    rows = []
    for agent in sorted(agent_feat['agent'].dropna().unique()):
        rows.append({
            'agent': agent,
            'unique': agent_feat[agent_feat['agent'] == agent]['unique_features'].mean(),
        })
    rows.append({'agent': 'Human', 'unique': human_feat['unique_features'].mean()})
    div = pd.DataFrame(rows)

    bars = ax.bar(div['agent'], div['unique'],
                  color=plt.cm.Set2(range(len(div))),
                  alpha=0.85, edgecolor='black', linewidth=1.5)
    ax.set_xlabel('Developer / Agent', fontweight='bold')
    ax.set_ylabel('Mean Unique Features per PR', fontweight='bold')
    ax.set_title('Rust: Feature Diversity by Agent', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=15, ha='right')
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height(),
                f'{bar.get_height():.2f}', ha='center', va='bottom',
                fontweight='bold')

    out = os.path.join(OUT_DIR, 'rq2_feature_diversity.png')
    plt.tight_layout()
    plt.savefig(out, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {out}")


def main():
    print("=" * 70)
    print("RUST RQ2: Advanced Type Feature Usage")
    print("=" * 70)

    agent_df, human_df = load_data()

    agent_feat = extract_features(agent_df, 'AI Agent')
    human_feat = extract_features(human_df, 'Human')

    stats_dict = run_stats(agent_feat, human_feat)

    plot_feature_means(agent_feat, human_feat)
    mat = plot_agent_heatmap(agent_feat, human_feat)
    plot_diversity(agent_feat, human_feat)

    agent_feat.to_csv(os.path.join(OUT_DIR, 'agent_features.csv'), index=False)
    human_feat.to_csv(os.path.join(OUT_DIR, 'human_features.csv'), index=False)
    mat.to_csv(os.path.join(OUT_DIR, 'feature_means_by_agent.csv'))
    with open(os.path.join(OUT_DIR, 'rq2_stats.json'), 'w') as f:
        json.dump(stats_dict, f, indent=2)

    print("\nRQ2 analysis complete.")


if __name__ == '__main__':
    main()

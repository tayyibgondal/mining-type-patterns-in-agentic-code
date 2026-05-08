"""
Comprehensive Rust Analysis - All Research Questions

Generates publication-ready figures for RQ1, RQ2, and RQ3 in a single run.
Mirrors `data_analysis/csharp_data_analysis/comprehensive_csharp_analysis.py`
but uses repo-relative paths and Rust-specific metrics.
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
OUT_DIR = os.path.join(HERE, 'final_figures')
os.makedirs(OUT_DIR, exist_ok=True)

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 16
plt.rcParams['axes.titlesize'] = 20
plt.rcParams['axes.labelsize'] = 18
plt.rcParams['xtick.labelsize'] = 14
plt.rcParams['ytick.labelsize'] = 14
plt.rcParams['legend.fontsize'] = 14

COLOR_AI = '#E74C3C'
COLOR_HUMAN = '#3498DB'

# Same feature pattern set used by the analysis scripts.
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

UNSAFE_PATTERN = re.compile(r'\bunsafe\b')


# ----------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------

def load_data():
    agent_path = os.path.join(DATA_DIR, 'rust_classified_type_prs.csv')
    human_path = os.path.join(DATA_DIR, 'human_rust_classified_type_prs.csv')

    agent_df = pd.read_csv(agent_path)
    human_df = pd.read_csv(human_path)

    if 'final_is_type_related' in agent_df.columns:
        agent_df = agent_df[agent_df['final_is_type_related'] == True]
    if 'final_is_type_related' in human_df.columns:
        human_df = human_df[human_df['final_is_type_related'] == True]

    print(f"Rust Type-Related PRs: AI={len(agent_df)}, Human={len(human_df)}")
    return agent_df, human_df


# ----------------------------------------------------------------------------
# RQ1: unsafe usage
# ----------------------------------------------------------------------------

def extract_unsafe(df):
    rows = []
    for _, r in df.iterrows():
        if 'unsafe_additions' in r.index and not pd.isna(r['unsafe_additions']):
            adds = int(r['unsafe_additions'])
            rems = int(r.get('unsafe_removals', 0) or 0)
        else:
            patch = str(r.get('patch_text', ''))
            adds = rems = 0
            for line in patch.split('\n'):
                if line.startswith('+') and not line.startswith('+++'):
                    adds += len(UNSAFE_PATTERN.findall(line))
                elif line.startswith('-') and not line.startswith('---'):
                    rems += len(UNSAFE_PATTERN.findall(line))
        rows.append({
            'id': r.get('id'),
            'agent': r.get('agent', 'Human'),
            'unsafe_additions': adds,
            'unsafe_removals': rems,
            'net_change': adds - rems,
            'total_ops': adds + rems,
        })
    return pd.DataFrame(rows)


def generate_rq1_figures(agent_dyn, human_dyn):
    a_pos = agent_dyn[agent_dyn['unsafe_additions'] > 0]['unsafe_additions']
    h_pos = human_dyn[human_dyn['unsafe_additions'] > 0]['unsafe_additions']

    fig, ax = plt.subplots(figsize=(8, 6))
    if len(a_pos) > 0 and len(h_pos) > 0:
        bp = ax.boxplot([a_pos, h_pos], labels=['AI Agent', 'Human'],
                        patch_artist=True, showmeans=True)
        for patch, color in zip(bp['boxes'], [COLOR_AI, COLOR_HUMAN]):
            patch.set_facecolor(color)
            patch.set_alpha(0.85)
        ax.set_yscale('log')
    else:
        means = [agent_dyn['unsafe_additions'].mean(),
                 human_dyn['unsafe_additions'].mean()]
        ax.bar(['AI Agent', 'Human'], means, color=[COLOR_AI, COLOR_HUMAN],
               alpha=0.85, edgecolor='black', linewidth=1.5)

    ax.set_ylabel('"unsafe" Additions per PR', fontweight='bold')
    ax.set_xlabel('Developer Type', fontweight='bold')
    ax.set_title('Rust: "unsafe" Additions', fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'fig1_rq1_unsafe_additions.png'),
                bbox_inches='tight', dpi=300)
    plt.close()
    print("Generated: fig1_rq1_unsafe_additions.png")

    # Per-agent breakdown
    fig, ax = plt.subplots(figsize=(11, 6))
    breakdown = agent_dyn.groupby('agent').agg(
        unsafe_additions=('unsafe_additions', 'sum'),
        unsafe_removals=('unsafe_removals', 'sum'),
    ).reset_index()
    breakdown = pd.concat([
        breakdown,
        pd.DataFrame([{
            'agent': 'Human',
            'unsafe_additions': int(human_dyn['unsafe_additions'].sum()),
            'unsafe_removals': int(human_dyn['unsafe_removals'].sum()),
        }])
    ], ignore_index=True)

    x = np.arange(len(breakdown))
    width = 0.35
    bars1 = ax.bar(x - width/2, breakdown['unsafe_additions'], width,
                   label='"unsafe" Additions', color='#E74C3C', alpha=0.85,
                   edgecolor='black', linewidth=1.5)
    bars2 = ax.bar(x + width/2, breakdown['unsafe_removals'], width,
                   label='"unsafe" Removals', color='#27AE60', alpha=0.85,
                   edgecolor='black', linewidth=1.5)
    ax.set_xlabel('Developer / Agent', fontweight='bold')
    ax.set_ylabel('Total "unsafe" Operations', fontweight='bold')
    ax.set_title('Rust: "unsafe" Operations by Agent', fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(breakdown['agent'], rotation=15, ha='right', fontweight='bold')
    ax.legend(loc='upper right', frameon=True, shadow=True)
    ax.grid(True, alpha=0.3, axis='y')
    for bars in [bars1, bars2]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2.0, h,
                        f'{int(h)}', ha='center', va='bottom',
                        fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'fig2_rq1_agent_breakdown.png'),
                bbox_inches='tight', dpi=300)
    plt.close()
    print("Generated: fig2_rq1_agent_breakdown.png")


# ----------------------------------------------------------------------------
# RQ2: advanced features
# ----------------------------------------------------------------------------

def extract_features(df):
    features = []
    for _, r in df.iterrows():
        patch = str(r.get('patch_text', ''))
        added_lines = '\n'.join(
            line[1:] for line in patch.split('\n')
            if line.startswith('+') and not line.startswith('+++')
        )
        counts = {name: len(re.findall(pat, added_lines))
                  for name, pat in RUST_FEATURES.items()}
        counts['id'] = r.get('id')
        counts['agent'] = r.get('agent', 'Human')
        counts['total_features'] = sum(counts[k] for k in RUST_FEATURES)
        counts['unique_features'] = sum(1 for k in RUST_FEATURES if counts[k] > 0)
        features.append(counts)
    return pd.DataFrame(features)


def generate_rq2_figures(agent_feat, human_feat, agent_df=None, human_df=None):
    fig, ax = plt.subplots(figsize=(10, 6))
    rows = []
    for agent in sorted(agent_feat['agent'].dropna().unique()):
        rows.append({
            'agent': str(agent),
            'unique': agent_feat[agent_feat['agent'] == agent]['unique_features'].mean(),
        })
    rows.append({'agent': 'Human', 'unique': human_feat['unique_features'].mean()})
    div = pd.DataFrame(rows)
    bars = ax.bar(div['agent'], div['unique'],
                  color=plt.cm.Set2(range(len(div))),
                  alpha=0.85, edgecolor='black', linewidth=1.5)
    ax.set_xlabel('Developer / Agent', fontweight='bold')
    ax.set_ylabel('Mean Unique Features', fontweight='bold')
    ax.set_title('Rust: Feature Diversity by Agent', fontweight='bold', pad=20)
    plt.xticks(rotation=15, ha='right')
    ax.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars, div['unique']):
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height(),
                f'{val:.2f}', ha='center', va='bottom',
                fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'fig3_rq2_feature_diversity.png'),
                bbox_inches='tight', dpi=300)
    plt.close()
    print("Generated: fig3_rq2_feature_diversity.png")

    # Top features bar chart (AI vs Human)
    top_features = [
        'generics', 'lifetimes', 'trait_bound', 'impl_trait', 'dyn_trait',
        'derive', 'match_expr', 'option_result', 'smart_pointer', 'where_clause',
    ]
    fig, ax = plt.subplots(figsize=(10, 8))
    ai_means = [agent_feat[f].mean() if f in agent_feat.columns else 0
                for f in top_features]
    hu_means = [human_feat[f].mean() if f in human_feat.columns else 0
                for f in top_features]
    labels = [f.replace('_', ' ').title() for f in top_features]
    y = np.arange(len(labels))
    height = 0.35
    ax.barh(y + height / 2, ai_means, height, label='AI Agent',
            color=COLOR_AI, alpha=0.85, edgecolor='black', linewidth=1.5)
    ax.barh(y - height / 2, hu_means, height, label='Human',
            color=COLOR_HUMAN, alpha=0.85, edgecolor='black', linewidth=1.5)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontweight='bold')
    ax.set_xlabel('Mean Usage per PR', fontweight='bold')
    ax.set_title('Rust: Advanced Feature Usage', fontweight='bold', pad=20)
    ax.legend(loc='lower right', frameon=True, shadow=True)
    ax.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'fig4_rq2_feature_usage.png'),
                bbox_inches='tight', dpi=300)
    plt.close()
    print("Generated: fig4_rq2_feature_usage.png")

    # Safety / anti-pattern features (Rust analog of fig5_rq2_safety_features
    # in the TS paper). For Rust the safety-bypassing constructs are:
    # unsafe blocks (per-PR additions), unsafe impl, mem::transmute,
    # `dyn Any`, .unwrap()/.expect() additions, `as` cast additions.
    safety_cols = [
        ('unsafe_impl', 'unsafe_impl'),
        ('transmute', 'transmute'),
        ('any_trait', 'any_trait'),
    ]
    fig, ax = plt.subplots(figsize=(11, 7))
    feat_labels = ['unsafe blocks', 'unsafe impl', 'transmute', 'dyn Any',
                   '.unwrap()/.expect()', '`as` casts']

    def safe_mean(df, col):
        if df is None or col not in df.columns:
            return 0.0
        return float(pd.to_numeric(df[col], errors='coerce').fillna(0).mean())

    ai_unsafe_per_pr = safe_mean(agent_df, 'unsafe_additions')
    hu_unsafe_per_pr = safe_mean(human_df, 'unsafe_additions')
    ai_unwrap_per_pr = safe_mean(agent_df, 'unwrap_additions')
    hu_unwrap_per_pr = safe_mean(human_df, 'unwrap_additions')
    ai_ascast_per_pr = safe_mean(agent_df, 'as_cast_additions')
    hu_ascast_per_pr = safe_mean(human_df, 'as_cast_additions')

    ai_safety_means = [
        ai_unsafe_per_pr,
        agent_feat['unsafe_impl'].mean() if 'unsafe_impl' in agent_feat else 0.0,
        agent_feat['transmute'].mean() if 'transmute' in agent_feat else 0.0,
        agent_feat['any_trait'].mean() if 'any_trait' in agent_feat else 0.0,
        ai_unwrap_per_pr,
        ai_ascast_per_pr,
    ]
    hu_safety_means = [
        hu_unsafe_per_pr,
        human_feat['unsafe_impl'].mean() if 'unsafe_impl' in human_feat else 0.0,
        human_feat['transmute'].mean() if 'transmute' in human_feat else 0.0,
        human_feat['any_trait'].mean() if 'any_trait' in human_feat else 0.0,
        hu_unwrap_per_pr,
        hu_ascast_per_pr,
    ]

    y = np.arange(len(feat_labels))
    height = 0.35
    ax.barh(y + height / 2, ai_safety_means, height, label='AI Agent',
            color=COLOR_AI, alpha=0.85, edgecolor='black', linewidth=1.5)
    ax.barh(y - height / 2, hu_safety_means, height, label='Human',
            color=COLOR_HUMAN, alpha=0.85, edgecolor='black', linewidth=1.5)
    ax.set_yticks(y)
    ax.set_yticklabels(feat_labels, fontweight='bold')
    ax.set_xlabel('Mean Usage per PR', fontweight='bold')
    ax.set_title('Rust: Type-Safety Anti-Pattern Usage', fontweight='bold', pad=20)
    ax.legend(loc='lower right', frameon=True, shadow=True)
    ax.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'fig5_rq2_safety_features.png'),
                bbox_inches='tight', dpi=300)
    plt.close()
    print("Generated: fig5_rq2_safety_features.png")


# ----------------------------------------------------------------------------
# RQ3: acceptance rate
# ----------------------------------------------------------------------------

def is_merged(s):
    if pd.isna(s):
        return False
    if isinstance(s, str) and s.strip() == '':
        return False
    return True


def cramers_v(chi2, n, r, c):
    if n == 0:
        return 0.0
    denom = n * (min(r, c) - 1)
    return float(np.sqrt(chi2 / denom)) if denom > 0 else 0.0


def generate_rq3_figures(agent_df, human_df):
    a_merged = agent_df['merged_at'].apply(is_merged).sum()
    h_merged = human_df['merged_at'].apply(is_merged).sum()
    a_pct = 100.0 * a_merged / len(agent_df) if len(agent_df) else 0.0
    h_pct = 100.0 * h_merged / len(human_df) if len(human_df) else 0.0

    contingency = np.array([
        [a_merged, len(agent_df) - a_merged],
        [h_merged, len(human_df) - h_merged],
    ])
    chi2, p, dof, _ = stats.chi2_contingency(contingency)
    v = cramers_v(chi2, contingency.sum(), *contingency.shape)

    print(f"  Acceptance: AI={a_pct:.1f}%, Human={h_pct:.1f}% "
          f"| chi2={chi2:.2f}, p={p:.4g}, V={v:.3f}")

    # Overall
    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar(['AI Agent', 'Human'], [a_pct, h_pct],
                  color=[COLOR_AI, COLOR_HUMAN], alpha=0.85,
                  edgecolor='black', linewidth=1.5)
    ax.set_ylabel('Acceptance Rate (%)', fontweight='bold')
    ax.set_xlabel('Developer Type', fontweight='bold')
    ax.set_title('Rust: PR Acceptance Rates', fontweight='bold', pad=20)
    ax.set_ylim(0, max(110, max(a_pct, h_pct) + 15))
    ax.grid(True, alpha=0.3, axis='y')
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height(),
                f'{bar.get_height():.1f}%', ha='center', va='bottom',
                fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'fig6a_rq3_acceptance_overall.png'),
                bbox_inches='tight', dpi=300)
    plt.close()
    print("Generated: fig6a_rq3_acceptance_overall.png")

    # By agent
    fig, ax = plt.subplots(figsize=(11, 6))
    by_agent = (
        agent_df.assign(_m=agent_df['merged_at'].apply(is_merged))
        .groupby('agent')
        .agg(merged=('_m', 'sum'), total=('_m', 'size'))
        .reset_index()
    )
    by_agent['rate'] = 100.0 * by_agent['merged'] / by_agent['total']
    rows = by_agent[['agent', 'rate', 'total']].to_dict('records')
    rows.append({'agent': 'Human', 'rate': h_pct, 'total': len(human_df)})
    df = pd.DataFrame(rows)

    bars = ax.bar(df['agent'], df['rate'],
                  color=plt.cm.Set2(range(len(df))),
                  alpha=0.85, edgecolor='black', linewidth=1.5)
    ax.set_xlabel('Developer / Agent', fontweight='bold')
    ax.set_ylabel('Acceptance Rate (%)', fontweight='bold')
    ax.set_title('Rust: Acceptance by Agent', fontweight='bold', pad=20)
    ax.set_ylim(0, max(110, df['rate'].max() + 15))
    plt.xticks(rotation=15, ha='right')
    ax.grid(True, alpha=0.3, axis='y')
    for bar, row in zip(bars, df.itertuples()):
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height(),
                f'{row.rate:.1f}%\n(n={int(row.total)})',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'fig6b_rq3_acceptance_by_agent.png'),
                bbox_inches='tight', dpi=300)
    plt.close()
    print("Generated: fig6b_rq3_acceptance_by_agent.png")

    return {
        'ai_acceptance_pct': float(a_pct),
        'human_acceptance_pct': float(h_pct),
        'chi2': float(chi2),
        'p_value': float(p),
        'dof': int(dof),
        'cramers_v': float(v),
    }


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("COMPREHENSIVE RUST ANALYSIS - All Research Questions")
    print("=" * 70)

    agent_df, human_df = load_data()

    print("\n[RQ1] Analyzing 'unsafe' type escape...")
    agent_dyn = extract_unsafe(agent_df)
    human_dyn = extract_unsafe(human_df)
    a_with = (agent_dyn['total_ops'] > 0).sum()
    h_with = (human_dyn['total_ops'] > 0).sum()
    print(f"  PRs with 'unsafe': AI={a_with} ({a_with/max(1,len(agent_dyn))*100:.1f}%), "
          f"Human={h_with} ({h_with/max(1,len(human_dyn))*100:.1f}%)")
    generate_rq1_figures(agent_dyn, human_dyn)
    agent_dyn.to_csv(os.path.join(OUT_DIR, 'agent_unsafe.csv'), index=False)
    human_dyn.to_csv(os.path.join(OUT_DIR, 'human_unsafe.csv'), index=False)

    print("\n[RQ2] Extracting advanced Rust features...")
    agent_feat = extract_features(agent_df)
    human_feat = extract_features(human_df)
    print(f"  Mean total features: AI={agent_feat['total_features'].mean():.1f}, "
          f"Human={human_feat['total_features'].mean():.1f}")
    print(f"  Mean unique features: AI={agent_feat['unique_features'].mean():.2f}, "
          f"Human={human_feat['unique_features'].mean():.2f}")
    generate_rq2_figures(agent_feat, human_feat, agent_df=agent_df, human_df=human_df)
    agent_feat.to_csv(os.path.join(OUT_DIR, 'agent_features.csv'), index=False)
    human_feat.to_csv(os.path.join(OUT_DIR, 'human_features.csv'), index=False)

    print("\n[RQ3] Analyzing acceptance rates...")
    rq3_stats = generate_rq3_figures(agent_df, human_df)

    summary = {
        'rq1': {
            'ai_pr_count': int(len(agent_dyn)),
            'human_pr_count': int(len(human_dyn)),
            'ai_unsafe_additions_total': int(agent_dyn['unsafe_additions'].sum()),
            'human_unsafe_additions_total': int(human_dyn['unsafe_additions'].sum()),
            'ai_unsafe_mean_per_pr': float(agent_dyn['unsafe_additions'].mean())
                if len(agent_dyn) else 0.0,
            'human_unsafe_mean_per_pr': float(human_dyn['unsafe_additions'].mean())
                if len(human_dyn) else 0.0,
        },
        'rq2': {
            'ai_total_features_mean': float(agent_feat['total_features'].mean())
                if len(agent_feat) else 0.0,
            'human_total_features_mean': float(human_feat['total_features'].mean())
                if len(human_feat) else 0.0,
            'ai_unique_features_mean': float(agent_feat['unique_features'].mean())
                if len(agent_feat) else 0.0,
            'human_unique_features_mean': float(human_feat['unique_features'].mean())
                if len(human_feat) else 0.0,
        },
        'rq3': rq3_stats,
    }
    with open(os.path.join(OUT_DIR, 'rust_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 70)
    print(f"COMPLETE. All Rust figures in {OUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()

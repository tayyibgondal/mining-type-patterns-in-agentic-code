"""
RQ1 (Rust): Do AI agents introduce more `unsafe` code than humans?

Mirrors `data_analysis/data_analysis_typescript/rq1_analysis.py` but uses
`unsafe` (and supporting `.unwrap()` / `as` cast) escape-hatch counts instead
of TypeScript's `any` keyword.

Statistical tests: Mann-Whitney U (non-parametric), Cohen's d effect size.
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

# Use repo-relative paths so this script works on any machine.
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(HERE, '..', '..', 'datasets', 'rust_data'))
OUT_DIR = os.path.join(HERE, 'figures_rq1')
os.makedirs(OUT_DIR, exist_ok=True)

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['axes.labelsize'] = 12

COLOR_AI = '#E74C3C'
COLOR_HUMAN = '#3498DB'

UNSAFE_PATTERN = re.compile(r'\bunsafe\b')


def load_data():
    """Load LLM-classified Rust PRs (AI agent + human)."""
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


def extract_unsafe_metrics(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Count `unsafe` additions and removals per PR from the patch text."""
    rows = []
    for _, r in df.iterrows():
        patch = str(r.get('patch_text', ''))
        adds = rems = 0
        for line in patch.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                adds += len(UNSAFE_PATTERN.findall(line))
            elif line.startswith('-') and not line.startswith('---'):
                rems += len(UNSAFE_PATTERN.findall(line))

        # Prefer pre-computed counts if present (more reliable)
        if 'unsafe_additions' in r and not pd.isna(r['unsafe_additions']):
            adds = int(r['unsafe_additions'])
        if 'unsafe_removals' in r and not pd.isna(r['unsafe_removals']):
            rems = int(r['unsafe_removals'])

        rows.append({
            'id': r.get('id'),
            'agent': r.get('agent', label),
            'developer_type': label,
            'unsafe_additions': adds,
            'unsafe_removals': rems,
            'net_change': adds - rems,
            'total_ops': adds + rems,
        })
    return pd.DataFrame(rows)


def cohens_d(x, y):
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return float('nan')
    vx, vy = np.var(x, ddof=1), np.var(y, ddof=1)
    pooled = np.sqrt(((nx - 1) * vx + (ny - 1) * vy) / (nx + ny - 2))
    if pooled == 0:
        return 0.0
    return (np.mean(x) - np.mean(y)) / pooled


def run_stats(agent_metrics, human_metrics):
    """Mann-Whitney U + Cohen's d for unsafe additions."""
    a = agent_metrics['unsafe_additions'].values
    h = human_metrics['unsafe_additions'].values

    if len(a) > 0 and len(h) > 0:
        u, p = stats.mannwhitneyu(a, h, alternative='two-sided')
    else:
        u, p = float('nan'), float('nan')
    d = cohens_d(a, h)

    print(f"\n[RQ1] Unsafe additions per PR")
    print(f"  AI:    n={len(a):,}, mean={np.mean(a):.3f}, median={np.median(a):.0f}")
    print(f"  Human: n={len(h):,}, mean={np.mean(h):.3f}, median={np.median(h):.0f}")
    print(f"  Mann-Whitney U: U={u:.0f}, p={p:.4g}")
    print(f"  Cohen's d:      {d:.3f}")

    return {
        'ai_n': int(len(a)),
        'human_n': int(len(h)),
        'ai_mean': float(np.mean(a)) if len(a) else 0.0,
        'human_mean': float(np.mean(h)) if len(h) else 0.0,
        'ai_median': float(np.median(a)) if len(a) else 0.0,
        'human_median': float(np.median(h)) if len(h) else 0.0,
        'mann_whitney_u': float(u) if not np.isnan(u) else None,
        'p_value': float(p) if not np.isnan(p) else None,
        'cohens_d': float(d) if not np.isnan(d) else None,
    }


def plot_unsafe_distribution(agent_metrics, human_metrics):
    fig, ax = plt.subplots(figsize=(8, 6))

    a_pos = agent_metrics[agent_metrics['unsafe_additions'] > 0]['unsafe_additions']
    h_pos = human_metrics[human_metrics['unsafe_additions'] > 0]['unsafe_additions']

    if len(a_pos) > 0 and len(h_pos) > 0:
        bp = ax.boxplot(
            [a_pos, h_pos],
            labels=['AI Agent', 'Human'],
            patch_artist=True,
            showmeans=True,
        )
        for patch, color in zip(bp['boxes'], [COLOR_AI, COLOR_HUMAN]):
            patch.set_facecolor(color)
            patch.set_alpha(0.85)
        ax.set_yscale('log')
    else:
        # Fallback: bar of means even if one side is empty
        ax.bar(
            ['AI Agent', 'Human'],
            [agent_metrics['unsafe_additions'].mean(),
             human_metrics['unsafe_additions'].mean()],
            color=[COLOR_AI, COLOR_HUMAN], alpha=0.85,
            edgecolor='black', linewidth=1.5,
        )

    ax.set_ylabel('"unsafe" Additions per PR (log scale)', fontweight='bold')
    ax.set_title('Rust: "unsafe" Additions per PR', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    out = os.path.join(OUT_DIR, 'rq1_unsafe_additions_box.png')
    plt.tight_layout()
    plt.savefig(out, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {out}")


def plot_agent_breakdown(agent_metrics, human_metrics):
    """Per-agent unsafe additions vs removals bar chart."""
    fig, ax = plt.subplots(figsize=(11, 6))

    breakdown = agent_metrics.groupby('agent').agg(
        unsafe_additions=('unsafe_additions', 'sum'),
        unsafe_removals=('unsafe_removals', 'sum'),
    ).reset_index()

    h_row = pd.DataFrame([{
        'agent': 'Human',
        'unsafe_additions': human_metrics['unsafe_additions'].sum(),
        'unsafe_removals': human_metrics['unsafe_removals'].sum(),
    }])
    breakdown = pd.concat([breakdown, h_row], ignore_index=True)

    x = np.arange(len(breakdown))
    width = 0.35

    bars1 = ax.bar(x - width/2, breakdown['unsafe_additions'], width,
                   label='"unsafe" Additions', color='#E74C3C', alpha=0.85,
                   edgecolor='black', linewidth=1.2)
    bars2 = ax.bar(x + width/2, breakdown['unsafe_removals'], width,
                   label='"unsafe" Removals', color='#27AE60', alpha=0.85,
                   edgecolor='black', linewidth=1.2)

    ax.set_xlabel('Developer / Agent', fontweight='bold')
    ax.set_ylabel('Total "unsafe" Operations', fontweight='bold')
    ax.set_title('Rust: "unsafe" Operations by Agent', fontweight='bold')
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
                        fontsize=11, fontweight='bold')

    out = os.path.join(OUT_DIR, 'rq1_unsafe_by_agent.png')
    plt.tight_layout()
    plt.savefig(out, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {out}")
    return breakdown


def plot_secondary_escape_hatches(agent_df, human_df):
    """Compare AI vs Human on .unwrap() and `as` cast additions."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, col, title in [
        (axes[0], 'unwrap_additions', '.unwrap()/.expect() additions'),
        (axes[1], 'as_cast_additions', '`as` cast additions'),
    ]:
        if col not in agent_df.columns or col not in human_df.columns:
            ax.text(0.5, 0.5, f"Column missing: {col}",
                    ha='center', va='center', transform=ax.transAxes)
            continue
        ai_mean = pd.to_numeric(agent_df[col], errors='coerce').fillna(0).mean()
        hu_mean = pd.to_numeric(human_df[col], errors='coerce').fillna(0).mean()
        bars = ax.bar(['AI Agent', 'Human'], [ai_mean, hu_mean],
                      color=[COLOR_AI, COLOR_HUMAN], alpha=0.85,
                      edgecolor='black', linewidth=1.2)
        ax.set_title(f'Mean {title} per PR', fontweight='bold')
        ax.set_ylabel('Mean per PR', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2.0, h,
                    f'{h:.2f}', ha='center', va='bottom', fontweight='bold')

    out = os.path.join(OUT_DIR, 'rq1_secondary_escape_hatches.png')
    plt.tight_layout()
    plt.savefig(out, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {out}")


def main():
    print("=" * 70)
    print("RUST RQ1: Does AI use 'unsafe' more than humans?")
    print("=" * 70)

    agent_df, human_df = load_data()

    agent_metrics = extract_unsafe_metrics(agent_df, 'AI Agent')
    human_metrics = extract_unsafe_metrics(human_df, 'Human')

    stats_dict = run_stats(agent_metrics, human_metrics)

    plot_unsafe_distribution(agent_metrics, human_metrics)
    breakdown = plot_agent_breakdown(agent_metrics, human_metrics)
    plot_secondary_escape_hatches(agent_df, human_df)

    agent_metrics.to_csv(os.path.join(OUT_DIR, 'agent_unsafe_metrics.csv'), index=False)
    human_metrics.to_csv(os.path.join(OUT_DIR, 'human_unsafe_metrics.csv'), index=False)
    breakdown.to_csv(os.path.join(OUT_DIR, 'unsafe_by_agent_breakdown.csv'), index=False)
    with open(os.path.join(OUT_DIR, 'rq1_stats.json'), 'w') as f:
        json.dump(stats_dict, f, indent=2)

    print("\nRQ1 analysis complete.")


if __name__ == '__main__':
    main()

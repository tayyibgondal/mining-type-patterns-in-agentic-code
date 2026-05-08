"""
RQ3 (Rust): How do Agentic PRs compare to human developer PRs in acceptance rate?

Definition of "accepted": `merged_at` column is non-null.

Statistical tests: Pearson chi-square test of independence, Cramer's V effect size.
"""

import os
import json
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

warnings.filterwarnings('ignore')

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(HERE, '..', '..', 'datasets', 'rust_data'))
OUT_DIR = os.path.join(HERE, 'figures_rq3')
os.makedirs(OUT_DIR, exist_ok=True)

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 11

COLOR_AI = '#E74C3C'
COLOR_HUMAN = '#3498DB'


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


def is_merged(s):
    """A PR is accepted iff merged_at is non-null and non-empty."""
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


def run_overall_test(agent_df, human_df):
    a_merged = agent_df['merged_at'].apply(is_merged).sum()
    h_merged = human_df['merged_at'].apply(is_merged).sum()
    a_total = len(agent_df)
    h_total = len(human_df)

    contingency = np.array([
        [a_merged, a_total - a_merged],
        [h_merged, h_total - h_merged],
    ])
    chi2, p, dof, expected = stats.chi2_contingency(contingency)
    n = contingency.sum()
    v = cramers_v(chi2, n, *contingency.shape)

    a_rate = 100.0 * a_merged / a_total if a_total else 0.0
    h_rate = 100.0 * h_merged / h_total if h_total else 0.0

    print(f"\n[RQ3] Acceptance (merged) rates")
    print(f"  AI:    merged={a_merged}/{a_total} ({a_rate:.1f}%)")
    print(f"  Human: merged={h_merged}/{h_total} ({h_rate:.1f}%)")
    print(f"  Chi-square: chi2={chi2:.2f}, p={p:.4g}, dof={dof}")
    print(f"  Cramer's V: {v:.3f}")

    return {
        'ai_merged': int(a_merged), 'ai_total': int(a_total),
        'human_merged': int(h_merged), 'human_total': int(h_total),
        'ai_acceptance_rate_pct': float(a_rate),
        'human_acceptance_rate_pct': float(h_rate),
        'chi2': float(chi2), 'p_value': float(p), 'dof': int(dof),
        'cramers_v': float(v),
    }


def plot_overall(stats_dict):
    fig, ax = plt.subplots(figsize=(7, 6))
    rates = [stats_dict['ai_acceptance_rate_pct'], stats_dict['human_acceptance_rate_pct']]
    labels = ['AI Agent', 'Human']
    bars = ax.bar(labels, rates, color=[COLOR_AI, COLOR_HUMAN], alpha=0.85,
                  edgecolor='black', linewidth=1.5)
    ax.set_ylabel('Acceptance Rate (%)', fontweight='bold')
    ax.set_title('Rust: PR Acceptance Rates', fontweight='bold')
    ax.set_ylim(0, max(110, max(rates) + 15))
    ax.grid(True, alpha=0.3, axis='y')

    for bar, val in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height(),
                f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')

    out = os.path.join(OUT_DIR, 'rq3_overall_acceptance.png')
    plt.tight_layout()
    plt.savefig(out, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {out}")


def plot_by_agent(agent_df, human_df, human_rate):
    fig, ax = plt.subplots(figsize=(11, 6))

    by_agent = (
        agent_df
        .assign(_merged=agent_df['merged_at'].apply(is_merged))
        .groupby('agent')
        .agg(merged=('_merged', 'sum'),
             total=('_merged', 'size'))
        .reset_index()
    )
    by_agent['rate'] = 100.0 * by_agent['merged'] / by_agent['total']

    rows = by_agent[['agent', 'rate', 'merged', 'total']].to_dict('records')
    rows.append({
        'agent': 'Human',
        'rate': human_rate,
        'merged': int(human_df['merged_at'].apply(is_merged).sum()),
        'total': int(len(human_df)),
    })
    df = pd.DataFrame(rows)

    bars = ax.bar(df['agent'], df['rate'],
                  color=plt.cm.Set2(range(len(df))),
                  alpha=0.85, edgecolor='black', linewidth=1.5)
    ax.set_xlabel('Developer / Agent', fontweight='bold')
    ax.set_ylabel('Acceptance Rate (%)', fontweight='bold')
    ax.set_title('Rust: Acceptance by Agent', fontweight='bold')
    ax.set_ylim(0, max(110, df['rate'].max() + 15))
    ax.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=15, ha='right')
    for bar, row in zip(bars, df.itertuples()):
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height(),
                f'{row.rate:.1f}%\n(n={row.total})',
                ha='center', va='bottom', fontweight='bold', fontsize=10)

    out = os.path.join(OUT_DIR, 'rq3_by_agent.png')
    plt.tight_layout()
    plt.savefig(out, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {out}")
    return df


def main():
    print("=" * 70)
    print("RUST RQ3: PR Acceptance Rates")
    print("=" * 70)

    agent_df, human_df = load_data()
    stats_dict = run_overall_test(agent_df, human_df)

    plot_overall(stats_dict)
    by_agent = plot_by_agent(agent_df, human_df, stats_dict['human_acceptance_rate_pct'])

    by_agent.to_csv(os.path.join(OUT_DIR, 'rq3_by_agent.csv'), index=False)
    with open(os.path.join(OUT_DIR, 'rq3_stats.json'), 'w') as f:
        json.dump(stats_dict, f, indent=2)

    print("\nRQ3 analysis complete.")


if __name__ == '__main__':
    main()

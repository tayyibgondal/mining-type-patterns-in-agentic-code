"""Figures 3 and 4 - escape-hatch / unsafe-construct churn per agent.

fig3  a TypeScript "any"  b C# "dynamic"  c Rust "unsafe"   churn per agent
fig4  a unsafe   b .unwrap()   c .expect()     (Rust)

Totals over each agent's LLM-confirmed type-related PRs. Hatched bars mark
agents with fewer than 10 PRs. Per-agent PR counts live in the caption.
"""

import numpy as np

from _style import (AGENT_LABEL, AGENT_ORDER, C_ADD, C_REMOVE, FS_LABEL, FS_TICK,
                    load_lang, panel_label, pattern_ops, save, text_width_in, tidy,
                    use_paper_style)
import matplotlib.pyplot as plt
import all_languages_statistical_analysis as S

use_paper_style()

SMALL_N = 10
ROW_H = 0.30          # inches per agent row
FIG_W = 7.16


def agent_totals(df, pattern):
    """{agent: (additions, removals, n_prs)} over the FULL agent grid, so rows
    align across panels; agents absent from a language get n_prs = 0."""
    adds, rems = pattern_ops(df, pattern)
    df = df.copy()
    df['_a'], df['_r'] = adds, rems
    return {a: (int(df.loc[df.agent == a, '_a'].sum()),
                int(df.loc[df.agent == a, '_r'].sum()),
                int((df.agent == a).sum())) for a in AGENT_ORDER}


def draw_panel(ax, totals, named=True):
    agents = list(totals)
    y = np.arange(len(agents))[::-1]
    bh = 0.34
    hi = max(max(t[0] for t in totals.values()), max(t[1] for t in totals.values()), 1)

    for yy, a in zip(y, agents):
        if totals[a][2] == 0:                      # agent absent from this language
            ax.text(hi * 0.012, yy, 'no PRs', va='center', ha='left',
                    fontsize=5.4, color='#a8a8a8', style='italic')
            continue
        kw = dict(zorder=3)
        if totals[a][2] < SMALL_N:
            kw.update(hatch='////', edgecolor='white', linewidth=0)
        ax.barh(yy + bh / 2 + 0.03, totals[a][0], height=bh, color=C_ADD, **kw)
        ax.barh(yy - bh / 2 - 0.03, totals[a][1], height=bh, color=C_REMOVE, **kw)

    ax.set_yticks(y)
    ax.set_yticklabels([AGENT_LABEL[a] for a in agents] if named else [''] * len(agents),
                       fontsize=FS_TICK)
    ax.set_ylim(-0.7, len(agents) - 0.3)
    ax.set_xlim(0, hi * 1.06)
    ax.tick_params(axis='y', length=0, pad=2.5)
    tidy(ax, axis='x')
    ax.spines['left'].set_visible(False)


def build(panels, name, xlabel):
    """panels = [(letter_title, totals, named), ...]"""
    TOP, BOTTOM = 0.44, 0.64
    n_max = max(len(p[1]) for p in panels)
    fig_h = n_max * ROW_H + TOP + BOTTOM
    fig = plt.figure(figsize=(FIG_W, fig_h))

    gutters = [max(text_width_in(fig, AGENT_LABEL[a], FS_TICK) for a in p[1]) + 0.06
               if p[2] else 0.05 for p in panels]
    LEFT, RIGHT, GAP = 0.02, 0.06, 0.30
    panel_in = (FIG_W - LEFT - RIGHT - sum(gutters) - GAP * (len(panels) - 1)) / len(panels)

    x_cursor = LEFT
    for k, ((title, totals, named), g) in enumerate(zip(panels, gutters)):
        h_frac = (len(totals) * ROW_H) / fig_h
        x0 = (x_cursor + g) / FIG_W
        ax = fig.add_axes([x0, 1 - TOP / fig_h - h_frac, panel_in / FIG_W, h_frac])
        x_cursor += g + panel_in + GAP
        draw_panel(ax, totals, named)
        ax.set_xlabel(xlabel, fontsize=FS_LABEL, labelpad=3)
        panel_label(fig, x0 - g / FIG_W, 1 - 0.24 / fig_h, 'abc'[k], title)

    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=C_ADD),
               plt.Rectangle((0, 0), 1, 1, facecolor=C_REMOVE),
               plt.Rectangle((0, 0), 1, 1, facecolor='#cccccc', hatch='////',
                             edgecolor='white', linewidth=0)]
    fig.legend(handles, ['Additions', 'Removals', f'n < {SMALL_N} PRs'],
               loc='lower center', bbox_to_anchor=(0.5, 0.0), ncol=3, fontsize=FS_LABEL)
    save(fig, name)


# Figure 3 - TypeScript + C# + Rust
rust_df, _ = load_lang('Rust')
build([('TypeScript · any', agent_totals(load_lang('TypeScript')[0], S.ANY_PATTERN), True),
       ('C# · dynamic', agent_totals(load_lang('C#')[0], S.DYNAMIC_PATTERN), False),
       ('Rust · unsafe', agent_totals(rust_df, r'\bunsafe\b'), False)],
      'fig3_escape_hatch_churn_by_agent', 'Total operations')

# Figure 4 - Rust
build([('unsafe', agent_totals(rust_df, r'\bunsafe\b'), True),
       ('.unwrap()', agent_totals(rust_df, r'\.unwrap\s*\('), False),
       ('.expect()', agent_totals(rust_df, r'\.expect\s*\('), False)],
      'fig4_rust_unsafe_constructs_by_agent', 'Total operations')

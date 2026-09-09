"""Figures 3 and 4 - escape-hatch / unsafe-construct churn per agent.

fig3  a TypeScript "any"  b C# "dynamic"  c Rust "unsafe"      churn per agent
fig4  Rust        a unsafe      b .unwrap()          c .expect()
fig6  TypeScript  a any         b non-null !         c @ts-ignore / @ts-expect-error
fig7  C#          a dynamic     b null-forgiving !   c #nullable disable

Totals over each agent's LLM-confirmed type-related PRs. Hatched bars mark
agents with fewer than 10 PRs. Per-agent PR counts live in the caption.
"""

import numpy as np

from _style import (AGENT_LABEL, AGENT_ORDER, C_ADD, C_REMOVE, FS_ANNOT, FS_LABEL, FS_TICK,
                    load_lang, panel_label, pattern_ops, save, text_width_in, tidy,
                    use_paper_style)
import matplotlib.pyplot as plt
import all_languages_statistical_analysis as S

use_paper_style()

SMALL_N = 10
ROW_H = 0.30          # inches per agent row
FIG_W = 7.16


def agent_totals(df, pattern, full_grid=True):
    """{agent: (additions, removals, n_prs)}. full_grid keeps every agent (rows
    align across languages in fig3; absent agents get n_prs = 0); otherwise only
    agents with PRs in this language are listed (single-language figures)."""
    adds, rems = pattern_ops(df, pattern)
    df = df.copy()
    df['_a'], df['_r'] = adds, rems
    order = AGENT_ORDER if full_grid else [a for a in AGENT_ORDER
                                           if (df.agent == a).any()]
    return {a: (int(df.loc[df.agent == a, '_a'].sum()),
                int(df.loc[df.agent == a, '_r'].sum()),
                int((df.agent == a).sum())) for a in order}


def draw_panel(ax, totals, named=True, rate=False):
    """rate=True plots mean operations per PR instead of raw totals, so agents
    with very different PR counts stay comparable on one axis."""
    agents = list(totals)
    y = np.arange(len(agents))[::-1]
    bh = 0.34

    def vals(a):
        add, rem, n = totals[a]
        if n == 0:
            return 0.0, 0.0
        return (add / n, rem / n) if rate else (float(add), float(rem))

    hi = max(max(v for a in agents for v in vals(a)), 1e-9)

    for yy, a in zip(y, agents):
        if totals[a][2] == 0:                      # agent absent from this language
            ax.text(hi * 0.012, yy, 'no PRs', va='center', ha='left',
                    fontsize=5.4, color='#a8a8a8', style='italic')
            continue
        add, rem = vals(a)
        if add == 0 and rem == 0:                  # construct never used by this agent
            ax.text(hi * 0.012, yy, '0', va='center', ha='left',
                    fontsize=FS_ANNOT, color='#a8a8a8')
            continue
        kw = dict(zorder=3)
        if totals[a][2] < SMALL_N:
            kw.update(hatch='////', edgecolor='white', linewidth=0)
        ax.barh(yy + bh / 2 + 0.03, add, height=bh, color=C_ADD, **kw)
        ax.barh(yy - bh / 2 - 0.03, rem, height=bh, color=C_REMOVE, **kw)

    ax.set_yticks(y)
    ax.set_yticklabels([AGENT_LABEL[a] for a in agents] if named else [''] * len(agents),
                       fontsize=FS_TICK)
    ax.set_ylim(-0.7, len(agents) - 0.3)
    ax.set_xlim(0, hi * 1.06)
    ax.tick_params(axis='y', length=0, pad=2.5)
    tidy(ax, axis='x')
    ax.spines['left'].set_visible(False)


def build(panels, name, xlabel, rate=False):
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
        draw_panel(ax, totals, named, rate=rate)
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
      'fig4_rust_unsafe_constructs_by_agent', 'Operations per PR', rate=True)

# Figure 6 - TypeScript escape constructs
ts_df, _ = load_lang('TypeScript')
build([('any', agent_totals(ts_df, S.ANY_PATTERN), True),
       ('non-null !', agent_totals(ts_df, r'!\s*[\.\[\(]'), False),
       ('@ts-ignore', agent_totals(ts_df, r'@ts-(?:ignore|expect-error)'), False)],
      'fig6_typescript_escape_constructs_by_agent', 'Operations per PR', rate=True)

# Figure 7 - C# escape constructs (only the agents that have C# PRs)
cs_df, _ = load_lang('C#')
build([('dynamic', agent_totals(cs_df, S.DYNAMIC_PATTERN, full_grid=False), True),
       ('null-forgiving !', agent_totals(cs_df, r'![\.\[\(]', full_grid=False), False),
       ('#nullable disable', agent_totals(cs_df, r'#nullable\s+disable', full_grid=False), False)],
      'fig7_csharp_escape_constructs_by_agent', 'Operations per PR', rate=True)

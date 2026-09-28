"""Figures 3 and 4 - escape-hatch / unsafe-construct churn per agent.

fig3  a TypeScript "any"  b C# "dynamic"  c Rust "unsafe"      churn per agent
fig4  Rust        a unsafe      b .unwrap()          c .expect()
fig6  TypeScript  a any         b non-null !         c @ts-ignore / @ts-expect-error
fig7  C#          a dynamic     b null-forgiving !   c #nullable disable

Totals over each agent's LLM-confirmed type-related PRs. Hatched bars mark
agents with fewer than 10 PRs. Per-agent PR counts live in the caption.
"""

import numpy as np

from _style import (AGENT_LABEL, AGENT_ORDER, C_ADD, C_REMOVE, FIG_H_S,
                    FS_ANNOT, FS_LABEL, FS_TICK, HATCH_SMALL_N, INK_3, SWATCH,
                    SURFACE, TEXT_W, bottom_legend, construct_ops, load_lang,
                    panel_label, row_separators, save, text_width_in, tidy,
                    use_paper_style)
import matplotlib.pyplot as plt

use_paper_style()

SMALL_N = 10
FIG_W = TEXT_W


def agent_totals(lang, df, key, full_grid=True):
    """{agent: (additions, removals, n_prs)}. full_grid keeps every agent (rows
    align across languages in fig3; absent agents get n_prs = 0); otherwise only
    agents with PRs in this language are listed (single-language figures)."""
    adds, rems = construct_ops(lang, df, key)
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
                    fontsize=FS_ANNOT - 1.0, color=INK_3, style='italic')
            continue
        add, rem = vals(a)
        if add == 0 and rem == 0:                  # construct never used by this agent
            ax.text(hi * 0.012, yy, '0', va='center', ha='left',
                    fontsize=FS_ANNOT, color=INK_3)
            continue
        kw = dict(zorder=3)
        if totals[a][2] < SMALL_N:
            kw.update(hatch=HATCH_SMALL_N, edgecolor=SURFACE, linewidth=0)
        ax.barh(yy + bh / 2 + 0.03, add, height=bh, color=C_ADD, **kw)
        ax.barh(yy - bh / 2 - 0.03, rem, height=bh, color=C_REMOVE, **kw)

    ax.set_yticks(y)
    ax.set_yticklabels([AGENT_LABEL[a] for a in agents] if named else [''] * len(agents),
                       fontsize=FS_TICK)
    ax.set_ylim(-0.7, len(agents) - 0.3)
    ax.set_xlim(0, hi * 1.06)
    tidy(ax, orient='h')
    row_separators(ax, y)


def build(panels, name, xlabel, rate=False):
    """panels = [(letter_title, totals, named), ...]"""
    TOP, BOTTOM = 0.34, 0.66
    # Fixed height, row height derived, so these four figures share a
    # footprint with each other and with fig5.
    n_max = max(len(p[1]) for p in panels)
    fig_h = FIG_H_S
    row_h = (fig_h - TOP - BOTTOM) / n_max
    fig = plt.figure(figsize=(FIG_W, fig_h))

    gutters = [max(text_width_in(fig, AGENT_LABEL[a], FS_TICK) for a in p[1]) + 0.06
               if p[2] else 0.05 for p in panels]
    LEFT, RIGHT, GAP = 0.02, 0.06, 0.26
    panel_in = (FIG_W - LEFT - RIGHT - sum(gutters) - GAP * (len(panels) - 1)) / len(panels)

    x_cursor = LEFT
    for k, ((title, totals, named), g) in enumerate(zip(panels, gutters)):
        h_frac = (len(totals) * row_h) / fig_h
        x0 = (x_cursor + g) / FIG_W
        ax = fig.add_axes([x0, 1 - TOP / fig_h - h_frac, panel_in / FIG_W, h_frac])
        x_cursor += g + panel_in + GAP
        draw_panel(ax, totals, named, rate=rate)
        ax.set_xlabel(xlabel, fontsize=FS_LABEL, labelpad=3)
        panel_label(fig, x0 - g / FIG_W, 1 - 0.24 / fig_h, 'abc'[k], title)

    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=C_ADD),
               plt.Rectangle((0, 0), 1, 1, facecolor=C_REMOVE),
               plt.Rectangle((0, 0), 1, 1, facecolor=SWATCH,
                             hatch=HATCH_SMALL_N,
                             edgecolor=SURFACE, linewidth=0)]
    bottom_legend(fig, handles,
                  ['Additions', 'Removals', f'n < {SMALL_N} PRs'])
    save(fig, name)


# Figure 3 - TypeScript + C# + Rust
rust_df, _ = load_lang('Rust')
build([('TypeScript · any',
        agent_totals('TypeScript', load_lang('TypeScript')[0], 'any'), True),
       ('C# · null-forgiving !',
        agent_totals('C#', load_lang('C#')[0], 'null_forgiving'), False),
       ('Rust · unsafe',
        agent_totals('Rust', rust_df, 'unsafe_any'), False)],
      'fig9_escape_hatch_churn_by_agent', 'Total operations')

# Figure 4 - Rust
build([('unsafe', agent_totals('Rust', rust_df, 'unsafe_any'), True),
       ('.unwrap()/.expect()',
        agent_totals('Rust', rust_df, 'unwrap_expect'), False),
       ('as cast', agent_totals('Rust', rust_df, 'as_cast'), False)],
      'fig10_rust_unsafe_by_agent', 'Operations per PR', rate=True)

# Figure 6 - TypeScript escape constructs
ts_df, _ = load_lang('TypeScript')
build([('any', agent_totals('TypeScript', ts_df, 'any'), True),
       ('non-null !',
        agent_totals('TypeScript', ts_df, 'non_null_assertion'), False),
       ('@ts-ignore', agent_totals('TypeScript', ts_df, 'ts_ignore'), False)],
      'fig11_typescript_escape_by_agent', 'Operations per PR', rate=True)

# Figure 7 - C# escape constructs (only the agents that have C# PRs)
cs_df, _ = load_lang('C#')
build([('dynamic',
        agent_totals('C#', cs_df, 'dynamic', full_grid=False), True),
       ('null-forgiving !',
        agent_totals('C#', cs_df, 'null_forgiving', full_grid=False), False),
       ('#nullable disable',
        agent_totals('C#', cs_df, 'nullable_disable', full_grid=False), False)],
      'fig12_csharp_escape_by_agent', 'Operations per PR', rate=True)

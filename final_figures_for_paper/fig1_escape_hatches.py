"""Figure 1 - the headline escape hatch of each language, AI vs. human.

One column per headline construct. C# gets two, because the cross-language
mapping pairs `any` with `dynamic` on syntax, but `dynamic` is rare in both
arms while the null-forgiving operator is where C# actually leaks. Showing only
the mapped construct would report the quiet half of the language.

Three rows, because one normalisation cannot carry this claim:

  a-d  prevalence - share of PRs introducing the construct at least once.
  e-h  raw intensity - additions per PR, among PRs introducing it.
  i-l  size-adjusted intensity - the same PRs, per 100 changed lines.

Rows e-h and i-l disagree in direction, and that disagreement is the point.
Agent PRs are three to five times larger than human PRs by median lines added,
so a per-PR count rewards a group for writing more code. Reporting only row e-h
would say agents reach for the hatch far more often than humans. Reporting only
row i-l would say the opposite. Both are computed from the same PRs and both are
shown, so the reader can see that the denominator, not the behaviour, is what
flips the sign.

All three rows are conditional on use for e-l: these counts are zero inflated,
and an unconditional box has its median and both quartiles stacked on zero.
"""

import numpy as np
from matplotlib.colors import to_rgba
from scipy.stats import mannwhitneyu

import matplotlib.lines as mlines
import matplotlib.pyplot as plt

from _style import (C_AI, C_HUMAN, FIG_H_L, FS_ANNOT, FS_LABEL, FS_LETTER,
                    FS_TICK, FS_TITLE, INK, INK_3, SURFACE, TEXT_W, conditional_rate,
                    bottom_legend, construct_ops, fmt_p, load_lang, log_axis,
                    save, text_width_in, tidy, use_paper_style)
from analysis.stats import proportion_test
from catalogue.constructs import HEADLINE_ESCAPE, get_by_key

use_paper_style()

# The catalogue display names are written for tables and run to 18 characters.
# On a four-column figure they collide, so each headline construct gets a short
# form here: the token a reader would actually search the diff for.
SHORT = {'any': 'any', 'dynamic': 'dynamic', 'null_forgiving': '!',
         'unsafe_any': 'unsafe'}

# Flattened so C# contributes both of its headline constructs.
COLUMNS = [(lang, key) for lang in ('TypeScript', 'C#', 'Rust')
           for key in HEADLINE_ESCAPE[lang]]

FIG_W, FIG_H = TEXT_W, FIG_H_L
fig = plt.figure(figsize=(FIG_W, FIG_H))
gs = fig.add_gridspec(3, len(COLUMNS), height_ratios=[1.0, 1.32, 1.32],
                      hspace=0.28, wspace=0.16,
                      left=0.150, right=0.992, top=0.912, bottom=0.155)

data = []
for lang, key in COLUMNS:
    a_df, h_df = load_lang(lang)
    construct = get_by_key(lang, key)
    a_add = construct_ops(lang, a_df, key)[0]
    h_add = construct_ops(lang, h_df, key)[0]
    data.append({
        'lang': lang, 'name': construct.display_name,
        'short': SHORT.get(key, construct.key),
        'n_ai': len(a_df), 'n_hu': len(h_df),
        'prev_ai': (a_add > 0).mean(), 'prev_hu': (h_add > 0).mean(),
        'use_ai': int((a_add > 0).sum()), 'use_hu': int((h_add > 0).sum()),
        'raw_ai': a_add[a_add > 0], 'raw_hu': h_add[h_add > 0],
        'rate_ai': conditional_rate(lang, a_df, key),
        'rate_hu': conditional_rate(lang, h_df, key),
    })

rows = [('raw_ai', 'raw_hu', 'Additions per PR'),
        ('rate_ai', 'rate_hu', 'Additions per 100\nchanged lines')]
# One shared log scale per row, so columns are comparable by eye.
limits = []
for ai_key, hu_key, _ in rows:
    vals = np.concatenate([d[k] for d in data for k in (ai_key, hu_key)
                           if len(d[k])])
    vals = vals[vals > 0]
    limits.append((vals.min() * 0.55, vals.max() * 3.0))


def paired_boxes(ax, groups, rng):
    for i, (vals, col) in enumerate(zip(groups, (C_AI, C_HUMAN))):
        vals = np.asarray(vals, dtype=float)
        vals = vals[vals > 0]
        if len(vals) >= 5:
            ax.boxplot([vals], positions=[i], widths=0.46, patch_artist=True,
                       showfliers=True, zorder=3,
                       flierprops=dict(marker='o', markersize=1.7,
                                       markerfacecolor='none',
                                       markeredgecolor=INK_3,
                                       markeredgewidth=0.35),
                       medianprops=dict(color=INK, linewidth=1.5),
                       whiskerprops=dict(color=col, linewidth=0.9),
                       capprops=dict(color=col, linewidth=0.9),
                       boxprops=dict(facecolor=to_rgba(col, 0.30),
                                     edgecolor=col, linewidth=1.1))
        elif len(vals):
            ax.scatter(i + rng.uniform(-0.08, 0.08, len(vals)), vals, s=13,
                       color=col, linewidths=0, zorder=4)
        if len(vals):
            ax.scatter([i], [vals.mean()], marker='D', s=17, facecolor=col,
                       edgecolor=SURFACE, linewidths=0.6, zorder=6)


axes = [[], [], []]
rng = np.random.default_rng(7)
for j, d in enumerate(data):
    # ---- row 1: prevalence -----------------------------------------------
    ax = fig.add_subplot(gs[0, j], sharey=axes[0][0] if axes[0] else None)
    axes[0].append(ax)
    pa, ph = 100 * d['prev_ai'], 100 * d['prev_hu']
    ax.bar([0, 1], [pa, ph], width=0.52, color=[C_AI, C_HUMAN], zorder=3)
    for x, v in ((0, pa), (1, ph)):
        ax.text(x, v + 3.5, f'{v:.0f}%' if v >= 9.5 else f'{v:.1f}%',
                ha='center', va='bottom', fontsize=FS_ANNOT, color=INK)
    res = proportion_test(d['use_ai'], d['n_ai'], d['use_hu'], d['n_hu'], '')
    ax.text(0.5, 0.97, fmt_p(res.p), transform=ax.transAxes, ha='center',
            va='top', fontsize=FS_ANNOT, color=INK_3, style='italic')
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 50, 100])
    if j == 0:
        ax.set_ylabel('PRs introducing\nit (%)', fontsize=FS_LABEL)

    # ---- rows 2 and 3: intensity, two normalisations ---------------------
    for r, ((ai_key, hu_key, ylabel), (lo, hi)) in enumerate(
            zip(rows, limits), start=1):
        bx = fig.add_subplot(gs[r, j],
                             sharey=axes[r][0] if axes[r] else None)
        axes[r].append(bx)
        groups = [d[ai_key], d[hu_key]]
        paired_boxes(bx, groups, rng)
        if min(len(np.asarray(g)) for g in groups) >= 3:
            _, p = mannwhitneyu(groups[0], groups[1], alternative='two-sided')
            bx.text(0.5, 0.97, fmt_p(p), transform=bx.transAxes, ha='center',
                    va='top', fontsize=FS_ANNOT, color=INK_3, style='italic')
        log_axis(bx, 'y')
        bx.set_ylim(lo, hi)
        if j == 0:
            bx.set_ylabel(ylabel, fontsize=FS_LABEL)
        if r == 2:
            bx.text(0.5, -0.175,
                    f"n = {d['use_ai']:,} / {d['use_hu']:,}",
                    transform=bx.transAxes, ha='center', va='top',
                    fontsize=FS_ANNOT - 1.5, color=INK_3)

for r, row_axes in enumerate(axes):
    for j, ax in enumerate(row_axes):
        ax.set_xlim(-0.68, 1.68)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(['AI', 'Human'] if r == 2 else ['', ''])
        tidy(ax, orient='v')
        if j > 0:
            plt.setp(ax.get_yticklabels(), visible=False)

# ---- panel letters, language and construct name ----------------------------
letters = 'abcdefghijkl'
for r, row_axes in enumerate(axes):
    for j, ax in enumerate(row_axes):
        box = ax.get_position()
        y = box.y1 + 0.012
        fig.text(box.x0, y, letters[r * len(data) + j], fontsize=FS_LETTER,
                 fontweight='bold', color=INK, ha='left', va='baseline')
        if r == 0:
            d = data[j]
            x = box.x0 + (text_width_in(fig, letters[j], FS_LETTER)
                          + 0.06) / FIG_W
            fig.text(x, y, d['lang'], fontsize=FS_TITLE, color=INK, ha='left',
                     va='baseline')
            x += (text_width_in(fig, d['lang'], FS_TITLE) + 0.07) / FIG_W
            fig.text(x, y, d['short'], fontsize=FS_TITLE - 1.0, color=INK_3,
                     ha='left', va='baseline', family='monospace')

handles = [plt.Rectangle((0, 0), 1, 1, facecolor=C_AI),
           plt.Rectangle((0, 0), 1, 1, facecolor=C_HUMAN),
           mlines.Line2D([], [], marker='D', linestyle='none', markersize=4.4,
                         markerfacecolor=INK_3, markeredgecolor=SURFACE,
                         markeredgewidth=0.5)]
bottom_legend(fig, handles, ['AI agents', 'Human developers', 'Mean'], x=0.55)

save(fig, 'fig1_escape_hatch_usage')

for d in data:
    print(f"  {d['lang']:<11} {d['name']:<22} "
          f"prev {100*d['prev_ai']:5.1f}% vs {100*d['prev_hu']:5.1f}%   "
          f"per PR {np.median(d['raw_ai']):6.1f} vs {np.median(d['raw_hu']):6.1f}   "
          f"per 100 {np.median(d['rate_ai']):5.2f} vs {np.median(d['rate_hu']):5.2f}")

"""Figures 6-8 - every escape hatch, one language per figure, AI vs. human.

The headline figure (fig1) shows one construct per language. These show all of
them, which is what the RQ2 claim actually rests on.

Two panels share a construct axis:

  a  prevalence - share of PRs introducing the construct at least once,
     paired horizontal bars, chi-square P per construct.
  b  conditional intensity - additions per 100 changed lines among the PRs that
     introduce it, paired horizontal boxes on a log axis, Mann-Whitney P.

Why conditional. Escape-hatch counts are zero inflated: for most constructs
over 90% of PRs sit at zero, so an unconditional box has its median, both
quartiles and its lower whisker stacked on the same value and communicates
nothing. Splitting the question in two is not a presentational convenience, it
is the only way to see which half is moving. Prevalence answers how many PRs
reach for the hatch. Conditional intensity answers how hard they lean on it
once they have. A group can match on one and diverge sharply on the other.

Constructs are ordered by prevalence, commonest at the top. Nested children are
dropped so Rust `unsafe` is counted once as the any-form roll-up rather than
again as each of its five spellings. Constructs the catalogue marks
`reliable=False` are excluded here and reported with their measured precision in
the text instead.
"""

import numpy as np
from matplotlib.colors import to_rgba
from scipy.stats import mannwhitneyu

import matplotlib.lines as mlines
import matplotlib.pyplot as plt

from _style import (C_AI, C_HUMAN, FIG_H_L, FIG_H_M, FS_ANNOT, FS_LABEL,
                    FS_LETTER, FS_TICK, FS_TITLE, INK, INK_3, SURFACE, TEXT_W,
                    bottom_legend, conditional_rate, construct_ops, escape_keys,
                    fmt_p, load_lang, log_axis, pretty_feature, row_separators,
                    save, text_width_in, tidy, use_paper_style)
from analysis.stats import benjamini_hochberg, distribution_test, proportion_test

use_paper_style()

FIG_W = TEXT_W
CHROME = 1.30         # inches of axis labels, title row and legend
OFFSET = 0.19         # how far the AI and human rows sit from the slot centre
BAR_H = 0.32
BOX_H = 0.30

LANGS = [('TypeScript', 'fig6_typescript_escape_distributions', FIG_H_M),
         ('C#', 'fig7_csharp_escape_distributions', FIG_H_M),
         ('Rust', 'fig8_rust_escape_distributions', FIG_H_L)]


def build(lang):
    """Per-construct prevalence, conditional rates and both P values."""
    a_df, h_df = load_lang(lang)
    rows, prev_tests, int_tests = [], [], []
    for key in escape_keys(lang):
        a_add = construct_ops(lang, a_df, key)[0]
        h_add = construct_ops(lang, h_df, key)[0]
        a_use, h_use = int((a_add > 0).sum()), int((h_add > 0).sum())
        rows.append({
            'key': key,
            'label': pretty_feature(key),
            'prev_ai': a_use / len(a_df), 'prev_hu': h_use / len(h_df),
            'n_ai': a_use, 'n_hu': h_use,
            'rate_ai': conditional_rate(lang, a_df, key),
            'rate_hu': conditional_rate(lang, h_df, key),
        })
        prev_tests.append(proportion_test(a_use, len(a_df), h_use, len(h_df), key))
        int_tests.append(distribution_test(rows[-1]['rate_ai'],
                                           rows[-1]['rate_hu'], key))
    # Corrected within each panel: these are a family of tests, one per
    # construct, and the paper's methodology says a family gets BH.
    for row, pt, it in zip(rows, benjamini_hochberg(prev_tests),
                           benjamini_hochberg(int_tests)):
        row['p_prev'] = pt.p_adjusted
        row['p_int'] = it.p_adjusted
    return rows


def draw(lang, name, fig_h):
    rows = build(lang)
    n = len(rows)
    slot = (fig_h - CHROME) / n
    fig = plt.figure(figsize=(FIG_W, fig_h))

    # The construct names are y tick labels on panel a, so panel a's left
    # margin has to hold the longest of them. Rendered rather than estimated
    # from the character count: Rust's names are twice the length of
    # TypeScript's, and a per-character guess is wrong in both directions.
    label_w = max(text_width_in(fig, r['label'], FS_TICK)
                  for r in rows) + 0.14
    # Each panel's P values live in their own gutter column rather than inside
    # the axes. Panel b is a log axis, so buying annotation room by extending
    # the limit would compress four decades of data to make space for six
    # characters, and panel a's bars run into their own value labels.
    gutter = (text_width_in(fig, 'P < 0.001', FS_ANNOT - 1.0) + 0.10) / FIG_W
    gs = fig.add_gridspec(
        1, 4, width_ratios=[1.0, 0.001, 1.5, 0.001], wspace=0.05,
        left=label_w / FIG_W, right=1 - 0.01,
        top=1 - 0.34 / fig_h, bottom=0.86 / fig_h)

    y = np.arange(n)[::-1].astype(float)   # commonest construct at the top

    # ---- a: prevalence ---------------------------------------------------
    ax = fig.add_subplot(gs[0, 0])
    for r, yy in zip(rows, y):
        for value, off, col in ((r['prev_ai'], OFFSET, C_AI),
                                (r['prev_hu'], -OFFSET, C_HUMAN)):
            ax.barh(yy + off, 100 * value, height=BAR_H, color=col, zorder=3)
            ax.text(100 * value + 1.2, yy + off,
                    f'{100 * value:.0f}' if value >= 0.095
                    else f'{100 * value:.1f}',
                    va='center', ha='left', fontsize=FS_ANNOT, color=INK)
    top = max(max(r['prev_ai'], r['prev_hu']) for r in rows) * 100
    ax.set_xlim(0, top * 1.34)
    ax.set_xlabel('PRs introducing it (%)', fontsize=FS_LABEL)
    ax.set_ylim(-0.6, n - 0.4)
    tidy(ax, orient='h')

    # ---- b: conditional intensity ----------------------------------------
    bx = fig.add_subplot(gs[0, 2], sharey=ax)
    rng = np.random.default_rng(11)
    for r, yy in zip(rows, y):
        for vals, off, col in ((r['rate_ai'], OFFSET, C_AI),
                               (r['rate_hu'], -OFFSET, C_HUMAN)):
            vals = np.asarray(vals, dtype=float)
            vals = vals[vals > 0]
            if len(vals) >= 5:
                bx.boxplot(
                    [vals], positions=[yy + off], widths=BOX_H,
                    orientation='horizontal',
                    patch_artist=True, showfliers=True, zorder=3,
                    flierprops=dict(marker='o', markersize=1.7,
                                    markerfacecolor='none',
                                    markeredgecolor=INK_3, markeredgewidth=0.35),
                    medianprops=dict(color=INK, linewidth=1.5),
                    whiskerprops=dict(color=col, linewidth=0.9),
                    capprops=dict(color=col, linewidth=0.9),
                    boxprops=dict(facecolor=to_rgba(col, 0.30), edgecolor=col,
                                  linewidth=1.1))
            elif len(vals):
                bx.scatter(vals, yy + off + rng.uniform(-0.05, 0.05, len(vals)),
                           s=13, color=col, linewidths=0, zorder=4)
            if len(vals):
                bx.scatter([vals.mean()], [yy + off], marker='D', s=17,
                           facecolor=col, edgecolor=SURFACE, linewidths=0.6,
                           zorder=6)

    log_axis(bx, 'x')
    allv = np.concatenate([np.asarray(r[k], dtype=float)
                           for r in rows for k in ('rate_ai', 'rate_hu')
                           if len(r[k])])
    allv = allv[allv > 0]
    bx.set_xlim(max(allv.min() * 0.6, 1e-3), allv.max() * 1.6)
    bx.set_xlabel('Additions per 100 changed lines,\namong PRs introducing it',
                  fontsize=FS_LABEL)
    tidy(bx, orient='h')

    # ---- gutters: one P-value column per panel ---------------------------
    # Placed by hand against each panel's right edge, because a gridspec
    # column wide enough for the text would steal that width from the data.
    gutters = []
    for panel in (ax, bx):
        box = panel.get_position()
        gaxis = fig.add_axes([box.x1, box.y0, gutter, box.height], sharey=ax)
        gaxis.set_xlim(0, 1)
        gaxis.set_xticks([])
        for side in ('top', 'right', 'bottom', 'left'):
            gaxis.spines[side].set_visible(False)
        gutters.append(gaxis)
        # Give the panel itself the width the gutter took.
        panel.set_position([box.x0, box.y0, box.width - gutter, box.height])
    ga, gb = gutters
    for gaxis, panel in zip(gutters, (ax, bx)):
        box = panel.get_position()
        gaxis.set_position([box.x1, box.y0, gutter, box.height])

    # Boxplot resets the shared y locator to its own positions, so the tick
    # labels are restored here, after every artist is on the axes. Setting
    # them earlier is what silently replaced the construct names with numbers.
    ax.set_yticks(y)
    ax.set_yticklabels([r['label'] for r in rows], fontsize=FS_TICK)
    ax.set_ylim(-0.6, n - 0.4)
    for panel in (bx, ga, gb):
        plt.setp(panel.get_yticklabels(), visible=False)
        panel.tick_params(axis='y', length=0)

    for r, yy in zip(rows, y):
        for panel, field in ((ga, 'p_prev'), (gb, 'p_int')):
            p_val = r[field]
            if p_val is None:
                continue
            panel.text(0.06, yy, fmt_p(p_val),
                       transform=panel.get_yaxis_transform(),
                       ha='left', va='center', fontsize=FS_ANNOT - 1.0,
                       color=INK if p_val < 0.05 else INK_3, style='italic')

    # Faint separators between construct slots, so 8 rows stay readable.
    for panel in (ax, bx, ga, gb):
        row_separators(panel, y)

    # ---- title and panel letters on one line above the panels ------------
    base = 1 - 0.155 / fig_h
    fig.text(0.004, base, lang, fontsize=FS_TITLE, color=INK,
             ha='left', va='baseline', fontweight='bold')
    for letter, panel in (('a', ax), ('b', bx)):
        fig.text(panel.get_position().x0, base, letter, fontsize=FS_LETTER,
                 fontweight='bold', color=INK, ha='left', va='baseline')

    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=C_AI),
               plt.Rectangle((0, 0), 1, 1, facecolor=C_HUMAN),
               mlines.Line2D([], [], marker='D', linestyle='none',
                             markersize=4.4, markerfacecolor=INK_3,
                             markeredgecolor=SURFACE, markeredgewidth=0.5)]
    bottom_legend(fig, handles, ['AI agents', 'Human developers', 'Mean'])
    save(fig, name)

    print(f'  {lang}: {n} constructs, {fig_h:.2f} in tall, '
          f'{slot:.3f} in per row, '
          f'n(AI)={len(load_lang(lang)[0]):,} n(Human)={len(load_lang(lang)[1]):,}')
    for r in rows:
        print(f'    {r["label"]:<34} prev {100*r["prev_ai"]:5.1f}% vs '
              f'{100*r["prev_hu"]:5.1f}% (p={r["p_prev"]:.2g})   '
              f'cond n {r["n_ai"]:>5}/{r["n_hu"]:<5} '
              f'median {np.median(r["rate_ai"]) if r["n_ai"] else 0:6.2f} vs '
              f'{np.median(r["rate_hu"]) if r["n_hu"] else 0:6.2f} '
              f'(p={r["p_int"]:.2g})')


for lang, name, fig_h in LANGS:
    draw(lang, name, fig_h)

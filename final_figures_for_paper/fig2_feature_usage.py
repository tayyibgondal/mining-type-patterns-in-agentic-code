"""Figures 2-4 - every tracked type construct, one language per figure.

One row per construct, ordered by the AI mean of panel a. Two panels share that
row:

  a  mean occurrences added per PR
  b  mean occurrences added per 100 changed lines

Both are shown for the same reason fig1 shows both. Agent PRs carry three to
five times more added lines than human PRs at the median, so panel a rewards a
group for writing more code and panel b does not. Several constructs change
which group leads between the two panels. Reporting either one alone would be a
choice about the conclusion rather than about the presentation.

This replaces the old three-panel fig2 and its fig2b twin. Three languages side
by side left roughly a third of an inch of bar for constructs whose names run to
thirty characters, which is not a figure anyone can read. One language per
figure gives the labels the width they need.
"""

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

from _style import (C_AI, C_HUMAN, FIG_H_L, FIG_H_M, FS_ANNOT, FS_LABEL,
                    FS_LETTER, FS_TICK, FS_TITLE, INK, INK_3, TEXT_W,
                    analysed_keys, bottom_legend, feature_frame, load_lang,
                    pretty_feature, row_separators, save, text_width_in, tidy,
                    use_paper_style)

use_paper_style()

# Height class per language, chosen from the construct count so the three
# figures share a footprint with the rest of the paper rather than each other.
LANGS = [('TypeScript', 'fig2_typescript_construct_usage', FIG_H_L),
         ('C#', 'fig3_csharp_construct_usage', FIG_H_M),
         ('Rust', 'fig4_rust_construct_usage', FIG_H_L)]

FIG_W = TEXT_W
CHROME = 1.12          # inches of axis labels, title row and legend
OFFSET = 0.215
BAR_H = 0.36


def collect(lang):
    """DataFrame(feature, ai, human, ai_p100, human_p100), AI-mean order."""
    a_df, h_df = load_lang(lang)
    feats = analysed_keys(lang)
    columns = {}
    for df, key in ((a_df, 'ai'), (h_df, 'human')):
        f = feature_frame(lang, df)
        scale = df['denom_lines'].to_numpy(dtype=float)
        columns[key] = pd.Series({c: f[c].mean() for c in feats})
        # `denom_lines` is lines added in countable source files, the same
        # denominator the statistics module uses. NOT `changes`, which in the
        # rebuilt schema counts changed FILES; dividing constructs by a file
        # count silently produced a different figure from the statistics.
        columns[key + '_p100'] = pd.Series(
            {c: float(np.mean(f[c].to_numpy(dtype=float) / scale)) * 100
             for c in feats})
    d = pd.concat(columns, axis=1).reset_index().rename(
        columns={'index': 'feature'})
    return d.sort_values('ai', ascending=False).reset_index(drop=True)


def draw(lang, name, fig_h):
    d = collect(lang)
    n = len(d)
    # Row height follows from the fixed figure height rather than the reverse.
    row_h = (fig_h - CHROME) / n
    fig = plt.figure(figsize=(FIG_W, fig_h))

    label_w = max(text_width_in(fig, pretty_feature(f), FS_TICK)
                  for f in d['feature']) + 0.14
    gs = fig.add_gridspec(1, 2, wspace=0.09,
                          left=label_w / FIG_W, right=0.99,
                          top=1 - 0.40 / fig_h, bottom=0.72 / fig_h)

    y = np.arange(n)[::-1].astype(float)
    panels = []
    for k, (ai_col, hu_col, xlabel) in enumerate((
            ('ai', 'human', 'Mean added per PR'),
            ('ai_p100', 'human_p100', 'Mean added per 100 changed lines'))):
        ax = fig.add_subplot(gs[0, k], sharey=panels[0] if panels else None)
        panels.append(ax)
        ax.barh(y + OFFSET, d[ai_col], height=BAR_H, color=C_AI, zorder=3)
        ax.barh(y - OFFSET, d[hu_col], height=BAR_H, color=C_HUMAN, zorder=3)
        ax.set_xlim(0, max(d[ai_col].max(), d[hu_col].max()) * 1.04)
        ax.set_xlabel(xlabel, fontsize=FS_LABEL)
        tidy(ax, orient='h')
        row_separators(ax, y)

    ax = panels[0]
    ax.set_yticks(y)
    ax.set_yticklabels([pretty_feature(f) for f in d['feature']],
                       fontsize=FS_TICK)
    ax.set_ylim(-0.7, n - 0.3)
    plt.setp(panels[1].get_yticklabels(), visible=False)

    base = 1 - 0.155 / fig_h
    fig.text(0.004, base, lang, fontsize=FS_TITLE, color=INK, ha='left',
             va='baseline', fontweight='bold')
    for letter, panel in zip('ab', panels):
        fig.text(panel.get_position().x0, base, letter, fontsize=FS_LETTER,
                 fontweight='bold', color=INK, ha='left', va='baseline')

    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=C_AI),
               plt.Rectangle((0, 0), 1, 1, facecolor=C_HUMAN)]
    bottom_legend(fig, handles, ['AI agents', 'Human developers'], x=0.55)
    save(fig, name)
    print(f'  {lang}: {n} constructs, {fig_h:.2f} in tall, '
          f'{row_h:.3f} in per row')


for lang, name, fig_h in LANGS:
    draw(lang, name, fig_h)

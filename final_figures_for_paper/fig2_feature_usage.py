"""Figure 2 - advanced type-feature usage, AI vs. human, three languages.

a  TypeScript (20 features)   b  C# (12)   c  Rust (19)
Paired horizontal bars, features sorted by AI mean within each language.
Constant bar thickness across panels; sample sizes and counting rules go in
the caption, not on the canvas.

Variants:
  fig2_feature_usage           mean occurrences per PR
  fig2b_feature_usage_per100   mean occurrences per 100 changed lines
                               (controls for AI PRs being ~3x larger)
"""

import numpy as np
import pandas as pd

from _style import (C_AI, C_HUMAN, FS_LABEL, FS_TICK, feature_frame, load_lang,
                    panel_label, pretty_feature, save, text_width_in, tidy,
                    use_paper_style)
import matplotlib.pyplot as plt
import all_languages_statistical_analysis as S

use_paper_style()

LANGS = ['TypeScript', 'C#', 'Rust']


def collect(normalise):
    """Return {lang: DataFrame(feature, ai, human)} sorted by AI value desc."""
    out = {}
    for lang in LANGS:
        a_df, h_df = load_lang(lang)
        feats = list(S.LANGUAGES[lang]['features'])
        rows = []
        for df, key in ((a_df, 'ai'), (h_df, 'human')):
            f = feature_frame(lang, df)
            if normalise:
                chg = pd.to_numeric(df['changes'], errors='coerce').fillna(0).values
                scale = np.where(chg > 0, chg, np.nan)
                vals = {c: np.nanmean(f[c].values / scale) * 100 for c in feats}
            else:
                vals = {c: f[c].mean() for c in feats}
            rows.append(pd.Series(vals, name=key))
        d = pd.concat(rows, axis=1).reset_index().rename(columns={'index': 'feature'})
        out[lang] = d.sort_values('ai', ascending=False).reset_index(drop=True)
    return out


def render(data, name, xlabel):
    tallest = max(len(d) for d in data.values())

    ROW_H = 0.168                      # inches per feature row - constant across panels
    TOP, BOTTOM = 0.46, 0.62           # inches of chrome
    fig_h = tallest * ROW_H + TOP + BOTTOM
    fig_w = 7.16
    fig = plt.figure(figsize=(fig_w, fig_h))

    # gutters sized to the widest feature label in each panel
    gutter = [max(text_width_in(fig, pretty_feature(f), FS_TICK)
                  for f in data[lang]['feature']) + 0.06 for lang in LANGS]

    LEFT, RIGHT, GAP = 0.02, 0.06, 0.28
    panel_in = (fig_w - LEFT - RIGHT - sum(gutter) - 2 * GAP) / 3

    h_frac = (tallest * ROW_H) / fig_h   # every panel spans the same height
    x_cursor = LEFT
    for k, lang in enumerate(LANGS):
        d = data[lang]
        x0 = (x_cursor + gutter[k]) / fig_w
        ax = fig.add_axes([x0, 1 - TOP / fig_h - h_frac, panel_in / fig_w, h_frac])
        x_cursor += gutter[k] + panel_in + GAP

        y = np.arange(len(d))[::-1]
        bh = 0.36
        ax.barh(y + bh / 2 + 0.03, d['ai'], height=bh, color=C_AI, zorder=3)
        ax.barh(y - bh / 2 - 0.03, d['human'], height=bh, color=C_HUMAN, zorder=3)

        xmax = max(d['ai'].max(), d['human'].max())
        ax.set_yticks(y)
        ax.set_yticklabels([pretty_feature(f) for f in d['feature']], fontsize=FS_TICK)
        ax.set_ylim(-0.75, len(d) - 0.25)
        ax.set_xlim(0, xmax * 1.06)
        ax.tick_params(axis='y', length=0, pad=2.5)
        tidy(ax, axis='x')
        ax.spines['left'].set_visible(False)
        ax.set_xlabel(xlabel, fontsize=FS_LABEL, labelpad=3)

        panel_label(fig, x0 - gutter[k] / fig_w, 1 - 0.24 / fig_h, 'abc'[k], lang)

    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=C_AI),
               plt.Rectangle((0, 0), 1, 1, facecolor=C_HUMAN)]
    fig.legend(handles, ['AI agents', 'Human developers'], loc='lower center',
               bbox_to_anchor=(0.5, 0.0), ncol=2, fontsize=FS_LABEL)
    save(fig, name)


render(collect(False), 'fig2_feature_usage', 'Mean per PR')
render(collect(True), 'fig2b_feature_usage_per100', 'Mean per 100 changed lines')

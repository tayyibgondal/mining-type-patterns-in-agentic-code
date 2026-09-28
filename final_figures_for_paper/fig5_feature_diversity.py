"""Figure 5 - type-feature diversity per developer, three languages in one chart.

Diversity = distinct features from the language's catalogue touched per PR,
shown as a share of the catalogue (TypeScript 20, C# 12, Rust 19 features) so
languages are comparable. The shaded band marks the human reference column.
Hatched bars mark agents with fewer than 10 PRs; raw means and per-agent PR
counts live in the caption.
"""

import numpy as np

from _style import (AGENT_LABEL, AGENT_ORDER, BAND, C_LANG, FIG_H_S, FS_LABEL,
                    FS_TICK, HATCH_SMALL_N, SWATCH, SURFACE, TEXT_W, bottom_legend,
                    catalogue_size, feature_frame, load_lang, save, tidy,
                    use_paper_style)
import matplotlib.pyplot as plt

use_paper_style()

LANGS = ['TypeScript', 'C#', 'Rust']
SMALL_N = 10
DEVS = AGENT_ORDER + ['Human']

stats = {lang: {} for lang in LANGS}
catalogue = {lang: catalogue_size(lang) for lang in LANGS}
for lang in LANGS:
    a_df, h_df = load_lang(lang)
    for df in (a_df, h_df):
        f = feature_frame(lang, df)
        df = df.reset_index(drop=True)
        for dev in df['agent'].unique():
            m = (df['agent'] == dev).values
            if dev in DEVS:
                stats[lang][dev] = (float(f.loc[m, 'unique'].mean()), int(m.sum()))

FIG_W, FIG_H = TEXT_W, FIG_H_S
fig = plt.figure(figsize=(FIG_W, FIG_H))
ax = fig.add_axes([0.150, 0.250, 0.840, 0.715])

x = np.arange(len(DEVS))
w = 0.24
for i, lang in enumerate(LANGS):
    off = (i - 1) * (w + 0.02)
    for xi, dev in zip(x, DEVS):
        if dev not in stats[lang]:
            continue
        mean, n = stats[lang][dev]
        v = 100 * mean / catalogue[lang]
        kw = dict(zorder=3)
        if n < SMALL_N:
            kw.update(hatch=HATCH_SMALL_N, edgecolor=SURFACE, linewidth=0)
        ax.bar(xi + off, v, width=w, color=C_LANG[lang], **kw)

ax.axvspan(len(DEVS) - 1.55, len(DEVS) - 0.45, color=BAND, zorder=0)

ax.set_xticks(x)
ax.set_xticklabels([AGENT_LABEL[d] for d in DEVS], fontsize=FS_TICK)
# The limit follows the data instead of the old catalogue size. Fixing it at
# 60 left the top half of the canvas empty once the catalogue was rebuilt.
_top = max(100 * m / catalogue[l] for l in LANGS for m, _ in stats[l].values())
ax.set_ylim(0, _top * 1.18)
ax.set_xlim(-0.62, len(DEVS) - 0.38)
ax.set_ylabel('Distinct features per PR\n(% of catalogue)', fontsize=FS_LABEL)
tidy(ax, orient='v')

handles = [plt.Rectangle((0, 0), 1, 1, facecolor=C_LANG[l]) for l in LANGS]
handles.append(plt.Rectangle((0, 0), 1, 1, facecolor=SWATCH,
                             hatch=HATCH_SMALL_N,
                             edgecolor=SURFACE, linewidth=0))
bottom_legend(fig, handles, LANGS + [f'n < {SMALL_N} PRs'], x=0.55)

save(fig, 'fig5_feature_diversity_by_agent')

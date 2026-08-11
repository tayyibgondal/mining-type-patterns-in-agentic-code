"""Figure 5 - type-feature diversity per developer, three languages in one chart.

Diversity = distinct features from the language's catalogue touched per PR,
shown as a share of the catalogue (TypeScript 20, C# 12, Rust 19 features) so
languages are comparable. The shaded band marks the human reference column.
Hatched bars mark agents with fewer than 10 PRs; raw means and per-agent PR
counts live in the caption.
"""

import numpy as np

from _style import (AGENT_LABEL, AGENT_ORDER, C_LANG, FS_LABEL, FS_TICK,
                    feature_frame, load_lang, save, tidy, use_paper_style)
import matplotlib.pyplot as plt
import all_languages_statistical_analysis as S

use_paper_style()

LANGS = ['TypeScript', 'C#', 'Rust']
SMALL_N = 10
DEVS = AGENT_ORDER + ['Human']

stats = {lang: {} for lang in LANGS}
catalogue = {lang: len(S.LANGUAGES[lang]['features']) for lang in LANGS}
for lang in LANGS:
    a_df, h_df = load_lang(lang)
    for df in (a_df, h_df):
        f = feature_frame(lang, df)
        df = df.reset_index(drop=True)
        for dev in df['agent'].unique():
            m = (df['agent'] == dev).values
            if dev in DEVS:
                stats[lang][dev] = (float(f.loc[m, 'unique'].mean()), int(m.sum()))

FIG_W, FIG_H = 7.16, 2.7
fig = plt.figure(figsize=(FIG_W, FIG_H))
ax = fig.add_axes([0.075, 0.17, 0.915, 0.75])

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
            kw.update(hatch='////', edgecolor='white', linewidth=0)
        ax.bar(xi + off, v, width=w, color=C_LANG[lang], **kw)

ax.axvspan(len(DEVS) - 1.55, len(DEVS) - 0.45, color='#f2f2f2', zorder=0)

ax.set_xticks(x)
ax.set_xticklabels([AGENT_LABEL[d] for d in DEVS], fontsize=FS_TICK)
ax.set_ylim(0, 60)
ax.set_yticks([0, 20, 40, 60])
ax.set_xlim(-0.62, len(DEVS) - 0.38)
ax.set_ylabel('Distinct features per PR\n(% of catalogue)', fontsize=FS_LABEL)
tidy(ax)
ax.tick_params(axis='x', length=0, pad=3)

handles = [plt.Rectangle((0, 0), 1, 1, facecolor=C_LANG[l]) for l in LANGS]
handles.append(plt.Rectangle((0, 0), 1, 1, facecolor='#cccccc', hatch='////',
                             edgecolor='white', linewidth=0))
fig.legend(handles, LANGS + [f'n < {SMALL_N} PRs'], loc='lower center',
           bbox_to_anchor=(0.53, 0.0), ncol=4, fontsize=FS_LABEL)

save(fig, 'fig5_feature_diversity_by_agent')

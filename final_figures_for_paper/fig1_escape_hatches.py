"""Figure 1 - escape-hatch use, AI agents vs. human developers, three languages.

a-c  prevalence: share of type-related PRs introducing >=1 escape hatch
     (one shared 0-100% axis).
d-f  intensity: additions per PR among PRs introducing any
     (one shared log axis; boxes need >=5 PRs, otherwise raw points).

Typography: exact P values (no star soup), language keywords in monospace,
sample sizes as quiet grey annotations, one job per text element.
"""

import numpy as np
from matplotlib.colors import to_rgba
from scipy.stats import mannwhitneyu

from _style import (C_AI, C_HUMAN, FS_ANNOT, FS_LABEL, FS_LETTER, FS_TICK, FS_TITLE,
                    INK, INK_3, escape_series, load_lang, save, text_width_in, tidy,
                    use_paper_style)
import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import all_languages_statistical_analysis as S

use_paper_style()

LANGS = [('TypeScript', 'any'), ('C#', 'dynamic'), ('Rust', 'unsafe')]


def fmt_p(p):
    if p < 0.001:
        return 'P < 0.001'
    return f'P = {p:.2f}'


FIG_W, FIG_H = 7.16, 4.35
fig = plt.figure(figsize=(FIG_W, FIG_H))
gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.55], hspace=0.52, wspace=0.12,
                      left=0.082, right=0.988, top=0.88, bottom=0.155)

data = []
for lang, esc in LANGS:
    a_df, h_df = load_lang(lang)
    data.append((lang, esc, escape_series(lang, a_df), escape_series(lang, h_df)))

log_top = max(max(ai.max(), hu.max() if len(hu) else 1) for _, _, ai, hu in data)

axes_top, axes_bot = [], []
for j, (lang, esc, ai, hu) in enumerate(data):
    # ---- prevalence (a-c): one shared 0-100 axis ----------------------------
    ax = fig.add_subplot(gs[0, j], sharey=axes_top[0] if axes_top else None)
    axes_top.append(ax)
    p_ai, p_hu = 100 * (ai > 0).mean(), 100 * (hu > 0).mean()
    ax.bar([0, 1], [p_ai, p_hu], width=0.52, color=[C_AI, C_HUMAN], zorder=3)
    for x, v in ((0, p_ai), (1, p_hu)):
        ax.text(x, v + 3.5, f'{v:.0f}%' if v >= 10 else f'{v:.1f}%', ha='center',
                va='bottom', fontsize=FS_ANNOT, color=INK)
    prev = S.proportion_test(int((ai > 0).sum()), len(ai), int((hu > 0).sum()), len(hu))
    ax.text(0.97, 0.94, fmt_p(prev['p']), transform=ax.transAxes, ha='right',
            va='top', fontsize=FS_ANNOT, color=INK_3, style='italic')
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 50, 100])
    ax.set_xlim(-0.65, 1.65)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['AI', 'Human'])
    tidy(ax)
    ax.tick_params(axis='x', length=0)
    if j == 0:
        ax.set_ylabel('PRs with escape\nhatch (%)', fontsize=FS_LABEL)
    else:
        plt.setp(ax.get_yticklabels(), visible=False)

    # ---- intensity (d-f): one shared log axis --------------------------------
    ax = fig.add_subplot(gs[1, j], sharey=axes_bot[0] if axes_bot else None)
    axes_bot.append(ax)
    groups = [ai[ai > 0], hu[hu > 0]]
    rng = np.random.default_rng(7)

    for i, (vals, col) in enumerate(zip(groups, (C_AI, C_HUMAN))):
        if len(vals) >= 5:
            ax.boxplot([vals], positions=[i], widths=0.46, patch_artist=True,
                       showfliers=True, zorder=3,
                       flierprops=dict(marker='o', markersize=1.8,
                                       markerfacecolor='none',
                                       markeredgecolor=INK_3, markeredgewidth=0.4),
                       medianprops=dict(color=col, linewidth=1.3),
                       whiskerprops=dict(color=col, linewidth=0.8),
                       capprops=dict(color=col, linewidth=0.8),
                       boxprops=dict(facecolor=to_rgba(col, 0.22), edgecolor=col,
                                     linewidth=1.0))
        else:
            ax.scatter(i + rng.uniform(-0.08, 0.08, len(vals)), vals, s=9,
                       color=col, linewidths=0, zorder=4)
        if len(vals):
            ax.scatter([i], [vals.mean()], marker='D', s=14, facecolor=col,
                       edgecolor='white', linewidths=0.5, zorder=6)
        # sample size, quiet and grey, under the tick label
        ax.text(i, -0.145, f'n = {len(vals)}', transform=ax.get_xaxis_transform(),
                ha='center', va='top', fontsize=FS_ANNOT, color=INK_3)

    if min(len(g) for g in groups) >= 3:
        _, p = mannwhitneyu(groups[0], groups[1], alternative='two-sided')
        y = log_top * 1.7
        ax.plot([0, 0, 1, 1], [y / 1.35, y, y, y / 1.35], lw=0.5, color=INK)
        ax.text(0.5, y * 1.15, fmt_p(p), ha='center', va='bottom',
                fontsize=FS_ANNOT, color=INK_3, style='italic')

    ax.set_yscale('log')
    ax.set_ylim(0.7, log_top * 6)
    ax.set_xlim(-0.65, 1.65)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['AI', 'Human'])
    tidy(ax)
    ax.tick_params(axis='x', length=0)
    if j == 0:
        ax.set_ylabel('Additions per PR', fontsize=FS_LABEL)
    else:
        plt.setp(ax.get_yticklabels(), visible=False)

# ---- panel letters + titles: bold letter, plain language, monospace keyword ---
for j, (lang, esc, *_rest) in enumerate(data):
    for letter, ax, y in (('abc'[j], axes_top[j], 0.95),
                          ('def'[j], axes_bot[j], 0.505)):
        x0 = ax.get_position().x0
        fig.text(x0, y, letter, fontsize=FS_LETTER, fontweight='bold', color=INK,
                 ha='left', va='baseline')
        if y > 0.6:  # language + keyword only on the top row
            x = x0 + 0.145 / FIG_W
            fig.text(x, y, lang, fontsize=FS_TITLE, color=INK, ha='left',
                     va='baseline')
            x += (text_width_in(fig, lang, FS_TITLE) + 0.075) / FIG_W
            fig.text(x, y, esc, fontsize=FS_TITLE - 0.5, color=INK, ha='left',
                     va='baseline', family='monospace')

handles = [plt.Rectangle((0, 0), 1, 1, facecolor=C_AI),
           plt.Rectangle((0, 0), 1, 1, facecolor=C_HUMAN),
           mlines.Line2D([], [], marker='D', linestyle='none', markersize=3.8,
                         markerfacecolor=INK_3, markeredgecolor='white',
                         markeredgewidth=0.4)]
fig.legend(handles, ['AI agents', 'Human developers', 'Mean'],
           loc='lower center', bbox_to_anchor=(0.53, 0.0), ncol=3,
           fontsize=FS_LABEL)

save(fig, 'fig1_escape_hatch_usage')

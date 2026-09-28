"""Shared plotting style + data loading for the paper figures.

Journal-style conventions (Nature / IEEE): one typeface, 6-7 pt text, thin black
axes, no in-figure methodology notes (that text belongs in the caption), panel
letters (a, b, c), shared scales within a row wherever the data allow it.

Figures read construct counts from the columns `scripts/stage1_extract.py`
wrote, via `catalogue`. They no longer recount from `patch_text` with a private
copy of the regexes, which is how the old figure scripts drifted away from the
statistics module and from each other.
"""

import os
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, REPO)

import pandas as pd  # noqa: E402

from catalogue.constructs import (  # noqa: E402
    HEADLINE_ESCAPE, NESTED_KEYS, by_family, constructs_for, display_names,
    get_by_key)

DATA_DIR = {
    'TypeScript': os.path.join(REPO, 'datasets', 'typescript_data'),
    'C#': os.path.join(REPO, 'datasets', 'csharp_data'),
    'Rust': os.path.join(REPO, 'datasets', 'rust_data'),
}
_NESTED = {c for kids in NESTED_KEYS.values() for c in kids}

OUT = HERE

# --- palette ----------------------------------------------------------------
#
# Okabe-Ito, the standard colour-vision-deficient safe qualitative palette.
# Chosen over a hand-picked set because it is the one a reviewer can look up.
# Hues are separable under deuteranopia, protanopia and tritanopia.
OI_ORANGE = '#E69F00'
OI_SKY = '#56B4E9'
OI_GREEN = '#009E73'
OI_YELLOW = '#F0E442'
OI_BLUE = '#0072B2'
OI_VERMILLION = '#D55E00'
OI_PURPLE = '#CC79A7'

# Role assignments. Every figure in the paper draws from these names, never
# from a literal hex value, so a palette change is one edit rather than twelve.
C_AI = OI_VERMILLION      # AI agents, warm
C_HUMAN = OI_BLUE         # human developers, cool
C_ADD = OI_VERMILLION     # escape-hatch additions
C_REMOVE = OI_GREEN       # escape-hatch removals
C_LANG = {'TypeScript': OI_BLUE, 'C#': OI_VERMILLION, 'Rust': OI_GREEN}

# Group colour is never the only channel carrying the AI/human distinction.
# Paired marks are always ordered AI first, and both are labelled, so the
# figures survive greyscale printing where vermillion and blue sit closer in
# luminance than one would like.

FILL_ALPHA = 0.30         # box and area fills; edges stay at full strength
HATCH_SMALL_N = '////'    # marks an estimate drawn from fewer than SMALL_N PRs
SWATCH = '#c9c9c9'        # neutral fill for a legend key that stands for a
                          # property rather than a group, e.g. the small-n hatch

# Neutrals. Four steps, used consistently: INK for anything the reader must
# read, INK_2 for secondary marks, INK_3 for annotations that should recede,
# GRID for structure that should barely register.
INK = '#000000'
INK_2 = '#404040'
INK_3 = '#737373'
GRID = '#dcdcdc'
BAND = '#f4f4f4'          # the shaded "Human" band in the by-agent figures
SURFACE = '#ffffff'

# Back-compat aliases for scripts that still name colours by hue.
BLUE, ORANGE, AQUA = OI_BLUE, OI_VERMILLION, OI_GREEN

AGENT_ORDER = ['Claude_Code', 'Copilot', 'Cursor', 'Devin', 'OpenAI_Codex']
AGENT_LABEL = {
    'Claude_Code': 'Claude Code',
    'OpenAI_Codex': 'Codex',
    'Copilot': 'Copilot',
    'Cursor': 'Cursor',
    'Devin': 'Devin',
    'Human': 'Human',
}

# --- canvas geometry ---------------------------------------------------------
#
# The paper is acmsmall, a single-column journal class, whose \textwidth is
# 395.82 pt = 5.4975 in and whose \textheight is 574 pt = 7.97 in.
#
# Every figure is drawn at exactly TEXT_W and included at width=\textwidth, so
# the scale factor on the page is 1.0. This matters more than it sounds. The
# figures used to be drawn on a 7.16 in canvas and included at 0.8\textwidth,
# a scale of 0.61, which turned an 8 pt tick label into 4.9 pt on paper. Any
# font size chosen here is now the size the reader actually gets.
TEXT_W = 5.4975
TEXT_H = 7.97

# Three standard heights. Every figure is built to hit one of them exactly.
# Before this, figure heights on the page ran from 2.0 in to 5.5 in with no
# pattern, which reads as carelessness however good each figure is on its own.
#
# L is capped at two thirds of \textheight on purpose. At 6.00 in a large
# figure filled 75% of the text block, which meant LaTeX could not place it
# next to any meaningful amount of prose and every one of them queued up into
# a float backlog. The results section rendered as four pages of solid text
# followed by a wall of figures.
FIG_H_S = 2.50   # <=5 rows, or a single panel
FIG_H_M = 3.85   # 5 to 10 rows
FIG_H_L = 5.30   # 10 or more rows, and the multi-panel headline figure

# Typography scale (pt) - keep every figure on exactly these five sizes.
# Body text in acmsmall is 10 pt and the scale factor is 1.0, so these are
# large for figure text, which is the intent.
FS_TICK = 8.5
FS_LABEL = 9.0
FS_ANNOT = 8.0
FS_TITLE = 9.5
FS_LETTER = 11.0


def use_paper_style():
    mpl.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Helvetica', 'Arial', 'DejaVu Sans'],
        'font.size': FS_LABEL,
        'axes.labelsize': FS_LABEL,
        'xtick.labelsize': FS_TICK,
        'ytick.labelsize': FS_TICK,
        'legend.fontsize': FS_LABEL,
        # keep math (p, r, chi^2) in the same face as the rest of the labels
        'mathtext.fontset': 'custom',
        'mathtext.rm': 'Helvetica',
        'mathtext.it': 'Helvetica:italic',
        'mathtext.bf': 'Helvetica:bold',
        'axes.edgecolor': INK,
        'axes.linewidth': 0.5,
        'axes.labelcolor': INK,
        'text.color': INK,
        'xtick.color': INK,
        'ytick.color': INK,
        'xtick.major.width': 0.5,
        'ytick.major.width': 0.5,
        'xtick.major.size': 2.2,
        'ytick.major.size': 2.2,
        'xtick.major.pad': 2.5,
        'ytick.major.pad': 2.5,
        'legend.frameon': False,
        'legend.handlelength': 1.0,
        'legend.handletextpad': 0.45,
        'legend.columnspacing': 1.2,
        'figure.facecolor': SURFACE,
        'axes.facecolor': SURFACE,
        'savefig.facecolor': SURFACE,
        'pdf.fonttype': 42,   # TrueType: embeddable text for camera-ready
        'ps.fonttype': 42,
        'savefig.bbox': None,  # exact canvas -> all figures scale identically in LaTeX
    })


def tidy(ax, orient='v', grid=True, category_spine=False):
    """The single styling contract every axes in the paper goes through.

    `orient` says which way the data runs, not which axis to grid. 'v' is for
    vertical bars and box plots, where the value axis is y. 'h' is for the
    horizontal bar and box charts, where it is x. Getting this from one
    argument is why the grid, the spines and the tick marks can no longer
    disagree between figures, which is what happened when each script passed
    its own axis= string and hid its own spines.

    The category axis loses its spine and its tick marks. Nothing is being
    measured along it, so a rule and ticks there are decoration that competes
    with the data. Pass `category_spine=True` for the rare axes that needs it.
    """
    value_axis = 'y' if orient == 'v' else 'x'
    category_axis = 'x' if orient == 'v' else 'y'

    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    if not category_spine:
        ax.spines['bottom' if orient == 'h' else 'left'].set_visible(
            True)           # the value axis keeps its rule
        ax.spines['left' if orient == 'h' else 'bottom'].set_visible(
            orient == 'v')  # horizontal charts drop the category rule
    ax.tick_params(axis=category_axis, length=0, pad=2.5)

    if grid:
        ax.grid(True, axis=value_axis, color=GRID, linewidth=0.5, zorder=0)
        ax.grid(False, axis=category_axis)
        ax.set_axisbelow(True)


def row_separators(ax, positions):
    """Hairlines between category slots on a multi-row chart.

    Applied to every row-based figure or none of them. Two of the three used
    to draw these and the third did not, which made the set look like it came
    from different papers.
    """
    for y in positions[:-1]:
        ax.axhline(y - 0.5, color=GRID, linewidth=0.4, zorder=0)


def log_axis(ax, which='x'):
    """Log scale with decade ticks only.

    Matplotlib's default log locator draws a minor tick for every one of the
    eight intermediate values in each decade. At this figure size that renders
    as a grey smear along the spine, and it differed between figures depending
    on the span of the data.
    """
    ax.set_xscale('log') if which == 'x' else ax.set_yscale('log')
    axis = ax.xaxis if which == 'x' else ax.yaxis
    axis.set_minor_locator(mticker.NullLocator())


def bottom_legend(fig, handles, labels, ncol=None, x=0.5):
    """The one legend position in the paper: centred under the panels."""
    fig.legend(handles, labels, loc='lower center',
               bbox_to_anchor=(x, -0.004), ncol=ncol or len(labels),
               fontsize=FS_LABEL)


def panel_label(fig, x, y, letter, title=''):
    """Nature-style panel marker: bold lowercase letter + plain title."""
    fig.text(x, y, letter, fontsize=FS_LETTER, fontweight='bold', color=INK,
             ha='left', va='baseline')
    if title:
        # Gap scales with the letter, which is now 14.5 pt rather than 10 pt.
        # The old fixed 0.13 in left "a" and the title touching.
        gap = text_width_in(fig, letter, FS_LETTER) + 0.075
        fig.text(x + gap / fig.get_figwidth(), y, title, fontsize=FS_TITLE,
                 color=INK, ha='left', va='baseline')


def text_width_in(fig, text, fontsize):
    """Rendered width of a single-line string, in inches."""
    t = fig.text(0, 0, text, fontsize=fontsize)
    w = t.get_window_extent(renderer=fig.canvas.get_renderer()).width / fig.dpi
    t.remove()
    return w


def save(fig, name):
    for ext in ('pdf', 'png'):
        fig.savefig(os.path.join(OUT, f'{name}.{ext}'), dpi=400)
    plt.close(fig)
    print(f'  wrote {name}.pdf / {name}.png')


# --- data --------------------------------------------------------------------

_CACHE = {}


def load_lang(lang):
    """Return (agent_df, human_df) of LLM-confirmed construct-related PRs."""
    if lang in _CACHE:
        return _CACHE[lang]
    path = os.path.join(DATA_DIR[lang], 'stage2_corpus.parquet')
    frame = pd.read_parquet(path)
    assert len(frame) == frame.pr_key.nunique(), f'{lang}: pr_key not unique'
    frame['denom_lines'] = frame['lines_added'].clip(lower=1)
    a = frame[frame.group == 'AI'].copy()
    h = frame[frame.group == 'Human'].copy()
    a['agent'] = a['agent'].fillna('Unknown')
    h['agent'] = 'Human'
    _CACHE[lang] = (a, h)
    return a, h


def headline_key(lang):
    """The construct that carries RQ2 for this language."""
    return HEADLINE_ESCAPE[lang][0]


def construct_ops(lang, df, key):
    """Per-PR (additions, removals) for one catalogue construct.

    Read straight from the extractor's columns. The old `pattern_ops` re-ran a
    regex over `patch_text` at figure time, using patterns that matched neither
    the extractor nor the statistics module.
    """
    c = get_by_key(lang, key)
    adds = df[c.add_col].to_numpy() if c.add_col in df.columns else np.zeros(len(df))
    rems = df[c.rem_col].to_numpy() if c.rem_col in df.columns else np.zeros(len(df))
    return adds, rems


def escape_series(lang, df):
    """Per-PR additions of the language's headline escape hatch."""
    return construct_ops(lang, df, headline_key(lang))[0]


def analysed_keys(lang, families=('expressiveness', 'safety')):
    """Catalogue keys plotted as the construct panel, nested ones removed."""
    keys = []
    for family in families:
        for c in by_family(lang, family):
            if c.key not in _NESTED and c.scope == 'line':
                keys.append(c.key)
    return keys


def feature_frame(lang, df):
    """Per-PR volume, diversity and per-100-line rate over the plotted keys."""
    keys = analysed_keys(lang)
    cols = [get_by_key(lang, k).add_col for k in keys]
    cols = [c for c in cols if c in df.columns]
    out = pd.DataFrame(index=df.index)
    for k, col in zip(keys, cols):
        out[k] = df[col]
    out['total'] = df[cols].sum(axis=1) if cols else 0
    out['unique'] = (df[cols] > 0).sum(axis=1) if cols else 0
    out['per100'] = 100 * out['total'] / df['denom_lines']
    return out


def catalogue_size(lang):
    """Number of constructs plotted, drives fig5's percentage axis."""
    return len(analysed_keys(lang))


_LABELS = {}


def pretty_feature(name):
    """Figure label for a construct key, taken from the catalogue."""
    if not _LABELS:
        for lang in DATA_DIR:
            _LABELS.update(display_names(lang))
    return _LABELS.get(name, name.replace('_', ' ').capitalize())


def stars(p):
    """Significance marker. Kept here so figure scripts need one import."""
    return ('***' if p < 0.001 else '**' if p < 0.01
            else '*' if p < 0.05 else 'ns')


def fmt_p(p):
    """Exact P value for an annotation, no star soup."""
    return 'P < 0.001' if p < 0.001 else f'P = {p:.3f}'.rstrip('0').rstrip('.')


def conditional_rate(lang, df, key, per100=True):
    """Per-100-line rate of one construct among the PRs that use it.

    Escape-hatch counts are zero inflated. An unconditional box plot of them
    collapses onto zero and shows the reader nothing at all. Conditioning on
    use separates the two things that actually differ between the groups: how
    many PRs reach for the hatch (prevalence, plotted as a bar) and how hard
    they lean on it once they do (this, plotted as a box).
    """
    adds, _ = construct_ops(lang, df, key)
    used = adds > 0
    if not per100:
        return adds[used]
    denom = df['denom_lines'].to_numpy()[used]
    return 100.0 * adds[used] / denom


def escape_keys(lang, min_prevalence=0.01, reliable_only=True):
    """Escape-family constructs worth a panel, commonest first.

    Nested children are dropped so `unsafe` is not counted once as a block and
    again as the any-form roll-up. Constructs below `min_prevalence` in BOTH
    arms are dropped, because a box drawn over four PRs is noise with a frame
    around it.
    """
    a, h = load_lang(lang)
    keep = []
    for c in by_family(lang, 'escape'):
        if c.key in _NESTED or c.scope != 'line':
            continue
        if reliable_only and not c.reliable:
            continue
        pa = (construct_ops(lang, a, c.key)[0] > 0).mean()
        ph = (construct_ops(lang, h, c.key)[0] > 0).mean()
        if max(pa, ph) < min_prevalence:
            continue
        keep.append((max(pa, ph), c.key))
    keep.sort(reverse=True)
    return [k for _, k in keep]

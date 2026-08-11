"""Shared plotting style + data loading for the paper figures.

Journal-style conventions (Nature / IEEE): one typeface, 6-7 pt text, thin black
axes, no in-figure methodology notes (that text belongs in the caption), panel
letters (a, b, c), shared scales within a row wherever the data allow it.

All numbers are computed with the SAME loaders, regexes and counting rules as
`data_analysis/statistical_analysis/all_languages_statistical_analysis.py`, so
figures and reported statistics cannot drift apart.
"""

import os
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(REPO, 'data_analysis', 'statistical_analysis'))

import all_languages_statistical_analysis as S  # noqa: E402

OUT = HERE

# --- palette -----------------------------------------------------------------
# Validated with the dataviz palette validator (light surface, --pairs all).
BLUE = '#2a78d6'   # categorical slot 1
ORANGE = '#eb6834'  # categorical slot 2
AQUA = '#1baf7a'   # categorical slot 3

C_AI = ORANGE
C_HUMAN = BLUE
C_ADD = ORANGE     # escape-hatch additions
C_REMOVE = AQUA    # escape-hatch removals
C_LANG = {'TypeScript': BLUE, 'C#': ORANGE, 'Rust': AQUA}

INK = '#000000'
INK_2 = '#404040'
INK_3 = '#737373'
GRID = '#e2e2e2'
SURFACE = '#ffffff'

AGENT_ORDER = ['Claude_Code', 'Copilot', 'Cursor', 'Devin', 'OpenAI_Codex']
AGENT_LABEL = {
    'Claude_Code': 'Claude Code',
    'OpenAI_Codex': 'Codex',
    'Copilot': 'Copilot',
    'Cursor': 'Cursor',
    'Devin': 'Devin',
    'Human': 'Human',
}

# Typography scale (pt) - keep every figure on exactly these five sizes.
FS_TICK = 8.0
FS_LABEL = 8.5
FS_ANNOT = 7.5
FS_TITLE = 9.0
FS_LETTER = 10.0


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


def tidy(ax, axis='y', grid=True):
    """No top/right spines; a single recessive grid on the value axis."""
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    if grid:
        ax.grid(True, axis=axis, color=GRID, linewidth=0.5)
        ax.set_axisbelow(True)


def panel_label(fig, x, y, letter, title=''):
    """Nature-style panel marker: bold lowercase letter + plain title."""
    fig.text(x, y, letter, fontsize=FS_LETTER, fontweight='bold', color=INK,
             ha='left', va='baseline')
    if title:
        fig.text(x + 0.13 / fig.get_figwidth(), y, title, fontsize=FS_TITLE,
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
    """Return (agent_df, human_df) of LLM-confirmed type-related PRs."""
    if lang in _CACHE:
        return _CACHE[lang]
    cfg = S.LANGUAGES[lang]
    a = S.load(cfg['agent'])
    h = S.load(cfg['human'])
    a['agent'] = a['agent'].fillna('Unknown')
    h['agent'] = 'Human'
    _CACHE[lang] = (a, h)
    return a, h


def escape_series(lang, df):
    """Per-PR count of escape-hatch additions, matching the statistics script."""
    esc = S.LANGUAGES[lang]['escape_name']
    if esc == 'any':
        return S.escape_additions(df, S.ANY_PATTERN)
    if esc == 'dynamic':
        return S.escape_additions(df, S.DYNAMIC_PATTERN, ignorecase=True)
    return S.unsafe_additions(df)


def pattern_ops(df, pattern):
    """Per-PR (additions, removals) for a regex over +/- patch lines."""
    import re
    pat = re.compile(pattern)
    adds, rems = [], []
    for text in df['patch_text'].fillna(''):
        a = r = 0
        for line in str(text).split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                a += len(pat.findall(line[1:]))
            elif line.startswith('-') and not line.startswith('---'):
                r += len(pat.findall(line[1:]))
        adds.append(a)
        rems.append(r)
    return np.array(adds), np.array(rems)


def feature_frame(lang, df):
    return S.feature_frame(df, S.LANGUAGES[lang]['features'])


def pretty_feature(name):
    special = {
        'as_const': 'as const', 'non_null_assertion': 'Non-null assertion',
        'keyof_typeof': 'keyof / typeof', 'infer_keyword': 'infer',
        'satisfies': 'satisfies', 'linq': 'LINQ', 'var_keyword': 'var',
        'dynamic_keyword': 'dynamic', 'init': 'init-only',
        'null_forgiving': 'Null-forgiving', 'nullable': 'Nullable types',
        'async_await': 'async / await', 'if_let': 'if let / while let',
        'box_dyn': 'Box<dyn T>', 'dyn_trait': 'dyn Trait', 'impl_trait': 'impl Trait',
        'option_result': 'Option / Result', 'unsafe_impl': 'unsafe impl',
        'any_trait': 'dyn Any', 'transmute': 'transmute',
        'phantom_data': 'PhantomData', 'match_expr': 'match', 'enum_def': 'enum',
        'struct_def': 'struct', 'trait_def': 'trait', 'type_alias': 'Type alias',
        'trait_bound': 'Trait bound', 'where_clause': 'where clause',
        'smart_pointer': 'Smart pointers', 'derive': '#[derive]',
        'nullish_coalescing': 'Nullish coalescing', 'optional_chaining': 'Optional chaining',
        'switch_expression': 'Switch expression', 'pattern_matching': 'Pattern matching',
    }
    if name in special:
        return special[name]
    return name.replace('_', ' ').capitalize()


def stars(p):
    return S.stars(p)

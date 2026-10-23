"""Figure 1 - the two-stage filtering pipeline.

Replaces a hand-drawn PNG that had no source. The bottom box previously read
"two annotators, consensus-based gold standard", which the evaluation
workbooks contradict: only one annotator's column is filled in all six of
them, and no agreement statistic was ever computed. The figure now says what
was actually done.

Writes FSE2027/fse-figures/data-processing-pipeline.png.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

INK = '#141414'
BLUE, BLUE_BG = '#1f4eb8', '#f4f7ff'
GREEN, GREEN_BG = '#2d6a2d', '#f3faf3'
ORANGE, ORANGE_BG = '#b5651d', '#fffcf4'
GREY, GREY_BG = '#141414', '#f0f0f0'

W, H = 11.0, 3.45
fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis('off')

TITLE_FS, SUB_FS = 16.5, 14.0


def box(x, y, w, h, edge, face, title, sub=None, lw=2.1):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle='round,pad=0,rounding_size=0.16',
        linewidth=lw, edgecolor=edge, facecolor=face, zorder=2))
    cx = x + w / 2
    if sub is None:
        ax.text(cx, y + h / 2, title, ha='center', va='center',
                fontsize=TITLE_FS, fontweight='bold', color=INK, zorder=3)
    else:
        ax.text(cx, y + h * 0.63, title, ha='center', va='center',
                fontsize=TITLE_FS, fontweight='bold', color=INK, zorder=3)
        ax.text(cx, y + h * 0.28, sub, ha='center', va='center',
                fontsize=SUB_FS, color=INK, zorder=3)


# ---- top row: the four pipeline steps -------------------------------------
TOP_Y, TOP_H = 2.42, 0.86
xs = [0.10, 2.86, 5.62, 8.38]
BW = 2.52
steps = [
    (GREY, GREY_BG, 'Data Sources', '(AIDev, GitHub)'),
    (BLUE, BLUE_BG, 'Stage 1: Regex', '(Recall-focused)'),
    (GREEN, GREEN_BG, 'Stage 2: LLM', '(Precision-focused)'),
    (GREY, GREY_BG, 'Final Corpus', None),
]
for x, (edge, face, title, sub) in zip(xs, steps):
    box(x, TOP_Y, BW, TOP_H, edge, face, title, sub)

for x in xs[:-1]:
    ax.add_patch(FancyArrowPatch(
        (x + BW + 0.03, TOP_Y + TOP_H / 2), (x + BW + 0.21, TOP_Y + TOP_H / 2),
        arrowstyle='-|>,head_width=4.2,head_length=6.5',
        mutation_scale=1, linewidth=2.0, color=INK, zorder=3))

# ---- detail row, dotted droppers from the two stages -----------------------
DET_Y, DET_H = 1.28, 0.78
# Each detail box is anchored to its stage: the Stage 1 box grows leftwards
# from Stage 1's right edge, the Stage 2 box grows rightwards from its left
# edge, so the two never meet in the middle.
details = [
    (0.10, (xs[1] + BW) - 0.10, xs[1] + BW / 2, BLUE, BLUE_BG,
     '<Stage 1 detail>', 'Build the rule-based custom regex parser'),
    (xs[2], (xs[3] + BW) - xs[2], xs[2] + BW / 2, GREEN, GREEN_BG,
     '<Stage 2 detail>', r'Multi-agent: Classifier $\rightarrow$ Validator'),
]
for x, w, drop_x, edge, face, title, sub in details:
    box(x, DET_Y, w, DET_H, edge, face, title, sub)
    ax.plot([drop_x, drop_x], [DET_Y + DET_H + 0.02, TOP_Y - 0.02],
            linestyle=(0, (1.6, 1.9)), linewidth=1.7, color=INK, zorder=1)

# ---- the manual validation banner -----------------------------------------
box(0.10, 0.18, W - 0.20, 0.78, ORANGE, ORANGE_BG, '<Manual validation>',
    'One author labelled 50 PRs per language per stage, blind to the filter decision')

out = Path(__file__).resolve().parents[1] / 'FSE2027' / 'fse-figures' / 'data-processing-pipeline.png'
fig.savefig(out, dpi=200, facecolor='white')
print('wrote', out)

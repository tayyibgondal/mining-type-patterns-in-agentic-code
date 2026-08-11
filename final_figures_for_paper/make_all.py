"""Regenerate every paper figure in this folder.

    python3 make_all.py

Each figure is written as a vector PDF (for LaTeX) and a 400 dpi PNG (for preview).
"""

import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

SCRIPTS = [
    'fig1_escape_hatches.py',
    'fig2_feature_usage.py',
    'fig3_4_by_agent.py',
    'fig5_feature_diversity.py',
]

for script in SCRIPTS:
    print(f'\n{script}')
    runpy.run_path(script, run_name='__main__')

print('\nAll figures regenerated.')

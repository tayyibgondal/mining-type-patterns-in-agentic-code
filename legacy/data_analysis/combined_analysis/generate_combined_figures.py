"""
Generate 3 Critical Combined Figures for High-Impact Paper
Run this to create TypeScript+C# merged visualizations
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.size'] = 16
plt.rcParams['axes.titlesize'] = 20
plt.rcParams['axes.labelsize'] = 18

# Load data with full paths
print("Loading data...")
ts_agent = pd.read_csv('/Users/tayyibgondal/Desktop/typescript-type-analysis/data/agent_type_prs_filtered_by_open_ai.csv')
ts_agent = ts_agent[ts_agent['final_is_type_related'] == True]

ts_human = pd.read_csv('/Users/tayyibgondal/Desktop/typescript-type-analysis/human_type_prs_filtered_by_open_ai.csv')
ts_human = ts_human[ts_human['final_is_type_related'] == True]

cs_agent = pd.read_csv('/Users/tayyibgondal/Desktop/typescript-type-analysis/csharp_data/agent_type_prs_filtered_by_open_ai.csv')
cs_agent = cs_agent[cs_agent['final_is_type_related'] == True]

cs_human = pd.read_csv('/Users/tayyibgondal/Desktop/typescript-type-analysis/csharp_data/human_type_prs_filtered_by_open_ai.csv')
cs_human = cs_human[cs_human['final_is_type_related'] == True]

print(f"TypeScript: {len(ts_agent)} AI, {len(ts_human)} Human")
print(f"C#: {len(cs_agent)} AI, {len(cs_human)} Human")

# FIGURE 1: Dataset Overview
fig, ax = plt.subplots(figsize=(9, 6))

categories = ['TypeScript', 'C#']
ai_counts = [len(ts_agent), len(cs_agent)]
human_counts = [len(ts_human), len(cs_human)]

x = np.arange(2)
width = 0.35

bars1 = ax.bar(x - width/2, ai_counts, width, label='AI Agent',
               color='#E74C3C', alpha=0.85, edgecolor='black', linewidth=2)
bars2 = ax.bar(x + width/2, human_counts, width, label='Human',
               color='#3498DB', alpha=0.85, edgecolor='black', linewidth=2)

ax.set_ylabel('Number of Type-Related PRs', fontweight='bold')
ax.set_xlabel('Language', fontweight='bold')
ax.set_title('Dataset Overview: Sample Sizes Across Languages', fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontweight='bold')
ax.legend(loc='upper left', frameon=True, shadow=True)
ax.grid(True, alpha=0.3, axis='y')

for bars in [bars1, bars2]:
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h,
               f'n={int(h)}', ha='center', va='bottom',
               fontsize=14, fontweight='bold', color='black')

# Add ratio annotations
ax.text(0, 0.92, 'Ratio:\n2.0:1', transform=ax.transAxes,
        fontsize=13, ha='center', fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7, edgecolor='black', linewidth=1.5))
ax.text(1, 0.92, 'Ratio:\n16.1:1', transform=ax.transAxes,
        fontsize=13, ha='center', fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='#FFE5E5', alpha=0.7, edgecolor='black', linewidth=1.5))

ax.text(1, 0.02, '⚠ Imbalanced', transform=ax.transAxes,
        fontsize=12, ha='center', style='italic', color='red')

plt.tight_layout()
plt.savefig('/Users/tayyibgondal/Desktop/typescript-type-analysis/final_paper_figures/fig1_dataset_overview.png',
            bbox_inches='tight', dpi=300)
plt.close()
print("✓ Figure 1: Dataset Overview")

# FIGURE 2: RQ1 Escape Type Usage
fig, ax = plt.subplots(figsize=(9, 6))

# From previous analysis
ts_ai_escape = 41.3
ts_human_escape = 23.4
cs_ai_escape = 4.1
cs_human_escape = 2.3

categories = ['TypeScript\n("any")', 'C#\n("dynamic")']
ai_vals = [ts_ai_escape, cs_ai_escape]
human_vals = [ts_human_escape, cs_human_escape]

x = np.arange(2)
width = 0.35

bars1 = ax.bar(x - width/2, ai_vals, width, label='AI Agent',
               color='#E74C3C', alpha=0.85, edgecolor='black', linewidth=2)
bars2 = ax.bar(x + width/2, human_vals, width, label='Human',
               color='#3498DB', alpha=0.85, edgecolor='black', linewidth=2)

ax.set_ylabel('% of PRs Modifying Escape Type', fontweight='bold')
ax.set_xlabel('Language (Escape Type Mechanism)', fontweight='bold')
ax.set_title('RQ1: Type Escape Mechanism Usage - Culture Matters', fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontweight='bold')
ax.legend(loc='upper right', frameon=True, shadow=True)
ax.grid(True, alpha=0.3, axis='y')
ax.set_ylim(0, 50)

for bars in [bars1, bars2]:
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h,
               f'{h:.1f}%', ha='center', va='bottom',
               fontsize=15, fontweight='bold', color='black')

ax.text(0.5, 0.92, '10× Difference: Language Culture Effect',
        transform=ax.transAxes, ha='center', fontsize=14, fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7, edgecolor='black', linewidth=2))

plt.tight_layout()
plt.savefig('/Users/tayyibgondal/Desktop/typescript-type-analysis/final_paper_figures/fig2_rq1_escape_types.png',
            bbox_inches='tight', dpi=300)
plt.close()
print("✓ Figure 2: RQ1 Escape Type Comparison")

# FIGURE 3: RQ3 Acceptance Paradox - THE MONEY SHOT
fig, ax = plt.subplots(figsize=(9, 7))

ts_ai_acc = 53.8
ts_human_acc = 25.3
cs_ai_acc = 56.7
cs_human_acc = 100.0

categories = ['TypeScript', 'C#']
ai_vals = [ts_ai_acc, cs_ai_acc]
human_vals = [ts_human_acc, cs_human_acc]

x = np.arange(2)
width = 0.35

bars1 = ax.bar(x - width/2, ai_vals, width, label='AI Agent',
               color='#E74C3C', alpha=0.85, edgecolor='black', linewidth=2)
bars2 = ax.bar(x + width/2, human_vals, width, label='Human',
               color='#3498DB', alpha=0.85, edgecolor='black', linewidth=2)

ax.set_ylabel('Acceptance Rate (%)', fontweight='bold')
ax.set_xlabel('Language', fontweight='bold')
ax.set_title('RQ3: The Acceptance Rate Paradox', fontweight='bold', pad=20, fontsize=22)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontweight='bold')
ax.legend(loc='upper left', frameon=True, shadow=True)
ax.grid(True, alpha=0.3, axis='y')
ax.set_ylim(0, 110)

for bars in [bars1, bars2]:
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 1,
               f'{h:.1f}%', ha='center', va='bottom',
               fontsize=16, fontweight='bold', color='black')

# Winner annotations
ax.text(0, 60, 'AI Wins\n(+28.5pp)', fontsize=15, fontweight='bold',
        ha='center', color='#C0392B',
        bbox=dict(boxstyle='round', facecolor='#FFE5E5', alpha=0.9, edgecolor='#E74C3C', linewidth=2))

ax.text(1, 90, 'Human Wins\n(+43.3pp)', fontsize=15, fontweight='bold',
        ha='center', color='#1F618D',
        bbox=dict(boxstyle='round', facecolor='#E8F6F3', alpha=0.9, edgecolor='#3498DB', linewidth=2))

# Sample info
ax.text(0.02, 0.02,
        'TypeScript: n=545 AI, n=269 Human (balanced)\n' +
        'C#: n=709 AI, n=44 Human (C# human 100% suggests bias)',
        transform=ax.transAxes, fontsize=11, style='italic',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.95, edgecolor='gray', linewidth=1.5))

plt.tight_layout()
plt.savefig('/Users/tayyibgondal/Desktop/typescript-type-analysis/final_paper_figures/fig3_rq3_acceptance_paradox.png',
            bbox_inches='tight', dpi=300)
plt.close()
print("✓ Figure 3: RQ3 Acceptance Paradox - THE MONEY SHOT!")

print("\n" + "=" * 60)
print("SUCCESS! 3 Combined Figures Generated")
print("=" * 60)
print("\nSaved in: final_paper_figures/")
print("  1. fig1_dataset_overview.png")
print("  2. fig2_rq1_escape_types.png")
print("  3. fig3_rq3_acceptance_paradox.png")
print("\nUse these plus your existing individual figures!")


# Final Figures for Research Paper

This document maps the requested figure components to the generated publication-ready figures.

## Generated Figures

### RQ1: Type Problem Resolution

**Figure 1: `any` Type Additions**
- **File**: `final_figures/fig1_rq1_any_additions.png`
- **Source**: Corresponds to `figures_rq1/fig1_any_usage_comparison.png` (part a only)
- **Shows**: Boxplot comparison of `any` type additions between AI agents and humans
- **Key Stats**: Mann-Whitney U test p < 0.001 (highly significant)
- **Clean**: No stats annotations on graph, legend top right

**Figure 2: `any` Operations by AI Agent**
- **File**: `final_figures/fig2_rq1_agent_breakdown.png`
- **Source**: Corresponds to `figures_rq1/fig2_any_behaviour_patterns.png` (part d only)
- **Shows**: Total `any` additions vs removals for each AI agent
- **Key Insight**: Devin has highest `any` operations, all agents add more than remove
- **Clean**: Legend top right, no annotations

---

### RQ2: Advanced Type Features

**Figure 3: Feature Diversity by Agent**
- **File**: `final_figures/fig3_rq2_feature_diversity.png`
- **Source**: Corresponds to `figures_rq2/fig3_agent_comparison.png` (part b only)
- **Shows**: Mean unique advanced features used by each AI agent vs humans
- **Key Insight**: Claude_Code (9.89) > Cursor (7.22) > Devin (6.93) > OpenAI_Codex (5.67) > Human (4.61)
- **Clean**: No annotations, legend removed (not needed)

**Figure 4: Feature Usage Frequency**
- **File**: `final_figures/fig4_rq2_feature_usage.png`
- **Source**: Corresponds to `figures_rq2/fig2_individual_features.png` (part a only)
- **Shows**: Horizontal bar chart of mean usage per PR for 12 key features
- **Key Insight**: AI uses MORE of every feature (generics ~14, type_assertions ~10, etc.)
- **Clean**: Legend top right, clear labels

**Figure 5: Type Safety Feature Adoption**
- **File**: `final_figures/fig5_rq2_safety_features.png`
- **Source**: Corresponds to `figures_rq2/fig4_pattern_analysis.png` (part a only)
- **Shows**: Adoption rate (% of PRs) for type safety features
- **Key Insight**: AI uses 4× more non-null assertions (dangerous pattern)
- **Clean**: Warning text removed, legend top right

---

### RQ3: Acceptance Rates

**Figure 6a: Overall Acceptance Rates**
- **File**: `final_figures/fig6a_rq3_acceptance_overall.png`
- **Source**: Corresponds to `figures_rq3/fig1_acceptance_rates.png` (part a)
- **Shows**: PR status distribution (Merged, Closed, Open)
- **Key Insight**: AI 53.8% accepted vs Human 25.3% (2.13× higher)
- **Clean**: Chi-square annotation removed, legend top right

**Figure 6b: Acceptance by Agent**
- **File**: `final_figures/fig6b_rq3_acceptance_by_agent.png`
- **Source**: Corresponds to `figures_rq3/fig1_acceptance_rates.png` (part b)
- **Shows**: Acceptance rate for each AI agent compared to humans
- **Key Insight**: All AI agents outperform humans (50-56% vs 25%)
- **Clean**: No annotations, human bar highlighted with thicker edge

---

## Figure Mapping Summary

| Paper Figure | File | Research Question | What It Shows |
|--------------|------|-------------------|---------------|
| Figure 1 | `fig1_rq1_any_additions.png` | RQ1 | AI adds more `any` than humans |
| Figure 2 | `fig2_rq1_agent_breakdown.png` | RQ1 | Agent-specific `any` behavior |
| Figure 3 | `fig3_rq2_feature_diversity.png` | RQ2 | Feature diversity by agent |
| Figure 4 | `fig4_rq2_feature_usage.png` | RQ2 | Individual feature usage |
| Figure 5 | `fig5_rq2_safety_features.png` | RQ2 | Type safety pattern adoption |
| Figure 6a | `fig6a_rq3_acceptance_overall.png` | RQ3 | Overall acceptance rates |
| Figure 6b | `fig6b_rq3_acceptance_by_agent.png` | RQ3 | Agent-specific acceptance |

**Total**: 7 publication-ready figures

---

## Style Specifications

All figures use:
- **DPI**: 300 (publication quality)
- **Color Scheme**: 
  - AI Agent: Vibrant Red (#E74C3C)
  - Human: Vibrant Blue (#3498DB)
  - Improvements: Green (#27AE60)
  - Reductions: Red (#E74C3C)
- **Legends**: Top right, with frame, shadow, and fancybox
- **Grid**: Light dashed lines (alpha=0.3)
- **Edge**: Black borders on bars (linewidth=1.5)
- **Labels**: Bold, clear fonts (Arial/Helvetica)
- **Clean**: No statistical annotations, no warning text

---

## Statistical Values (for text, not on graphs)

### RQ1:
- Mann-Whitney U test (any additions): U=80152.5, p<0.001, Cohen's d=0.316

### RQ2:
- Mann-Whitney U test (total features): p<0.000001
- All effect sizes positive (AI > Human)

### RQ3:
- Chi-square test (acceptance): χ²=27.52, p<0.0001
- AI acceptance: 53.8% (293/545)
- Human acceptance: 25.3% (68/269)

Use these values in the paper text and table captions, not on the figures themselves.


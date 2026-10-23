# TypeScript vs C#: Comprehensive Comparison for Research Paper

## Dataset Overview

| Language | AI PRs | Human PRs | AI Agents | Sample Ratio (AI:Human) |
|----------|--------|-----------|-----------|-------------------------|
| **TypeScript** | 545 | 269 | Devin, Claude_Code, Cursor, OpenAI_Codex | 2.03:1 |
| **C#** | 709 | 44 | Copilot, OpenAI_Codex, Cursor | 16.1:1 |

**Note**: C# human sample is much smaller and highly selective (100% acceptance suggests curation)

---

## RQ1: Type Escape Mechanism Usage

### TypeScript (`any` type):

| Metric | AI Agent | Human | Interpretation |
|--------|----------|-------|----------------|
| PRs modifying escape type | 41.3% | 23.4% | AI engages more |
| Reduce type safety | 70.2% | 60.3% | Both add more than remove |
| Improve type safety | 19.1% | 7.9% | AI improves 2.4× more often |
| Statistical significance | p < 0.0001 | --- | Highly significant |

**Conclusion TS**: AI actively engages with `any`, doesn't systematically bypass

### C# (`dynamic` type):

| Metric | AI Agent | Human | Interpretation |
|--------|----------|-------|----------------|
| PRs modifying escape type | 4.1% (29 PRs) | 2.3% (1 PR) | Rare in both groups |
| Statistical significance | N/A | --- | Too few samples |

**Conclusion C#**: Both groups avoid `dynamic` - strong type discipline

### Cross-Language Insight:
**Language culture matters**: TypeScript community accepts `any` as pragmatic; C# community treats `dynamic` as anti-pattern. AI agents adapt to language norms.

---

## RQ2: Advanced Feature Usage

### TypeScript:

| Metric | AI Agent | Human | Ratio |
|--------|----------|-------|-------|
| Mean total features | 87.49 | 76.41 | 1.15× |
| Median features (with features) | 25.0 | 12.0 | 2.08× |
| Unique features | 6.57 | 4.51 | 1.46× |
| Feature density (/100 LoC) | 11.29 | 9.25 | 1.22× |

### C#:

| Metric | AI Agent | Human | Ratio |
|--------|----------|-------|-------|
| Mean total features | 411.1 | 112.5 | 3.65× |
| Unique features | ~8.5 | ~5.2 | 1.63× |

### Cross-Language Insight:
**AI feature over-application is UNIVERSAL**: Occurs in both TypeScript (1.2-2×) and C# (3.7×). AI agents consistently generate feature-rich code regardless of language.

---

## RQ3: Acceptance Rates

### TypeScript:

| Developer | Acceptance Rate | Interpretation |
|-----------|----------------|----------------|
| AI Agent | 53.8% (293/545) | Higher than human |
| Human | 25.3% (68/269) | Lower baseline |
| **Advantage** | **AI wins** | +28.5 percentage points |

### C#:

| Developer | Acceptance Rate | Interpretation |
|-----------|----------------|----------------|
| AI Agent | 56.7% (402/709) | Moderate acceptance |
| Human | 100.0% (44/44) | Perfect record |
| **Advantage** | **Human wins** | +43.3 percentage points |

### Cross-Language Insight:
**Acceptance patterns are NOT universal**: 
- In TypeScript (large human sample, n=269), AI's comprehensive approach succeeds
- In C# (small human sample, n=44), human's curated submissions dominate
- **Confounding factor**: Sample size and selection bias in C# human data

---

## The Big Picture: What This Means

### Universal Patterns (Apply to Both Languages):

1. **AI Feature Sprawl**: AI uses 1.5-4× more features in both languages
2. **Feature Capability**: AI can generate sophisticated patterns in TypeScript AND C#
3. **Type Safety Engagement**: AI doesn't systematically avoid type systems

### Language-Specific Patterns:

1. **Type Escape Usage**:
   - TypeScript: Common and accepted (40%+ use `any`)
   - C#: Rare and discouraged (<5% use `dynamic`)

2. **Acceptance Outcomes**:
   - TypeScript: AI wins (likely due to thoroughness)
   - C#: Human wins (likely due to sample curation)

### What We Can Conclude:

✅ **Safe to conclude across languages**:
- AI over-applies type features (consistent in TS and C#)
- AI can generate advanced type patterns (not language-limited)

⚠️ **Cannot conclude universally**:
- Acceptance rate superiority (varies by language/sample)
- Type escape behavior (language culture dependent)

---

## Recommended Paper Structure:

### Primary Focus: TypeScript (larger, balanced sample)
- 545 AI vs 269 human (2:1 ratio - reasonable)
- Representative of real-world TypeScript development
- Statistical power for all three RQs

### Secondary: C# as Validation
- Confirms AI feature over-application pattern
- Shows language culture impacts type escape usage
- Demonstrates acceptance patterns vary (cautionary tale about generalization)

### Combined Narrative:
"While our TypeScript analysis (n=814 PRs) provides robust evidence of AI behavior patterns, C# analysis (n=753 PRs) reveals important language-specific nuances. AI feature over-application occurs universally, but type escape usage and acceptance patterns depend on language culture and sample characteristics."

---

## LaTeX Table for Paper:

```latex
\begin{table*}[t]
\centering
\caption{Cross-Language Comparison: TypeScript vs C# Type Safety Practices}
\label{tab:cross_language}
\begin{tabular}{llrrrr}
\hline
\textbf{Metric} & \textbf{Language} & \textbf{AI Agent} & \textbf{Human} & \textbf{Ratio} & \textbf{p-value} \\
\hline
\multicolumn{6}{l}{\textit{RQ1: Type Escape Mechanism Usage}} \\
\% PRs with escape type & TypeScript (\texttt{any}) & 41.3\% & 23.4\% & 1.76× & <0.001*** \\
& C\# (\texttt{dynamic}) & 4.1\% & 2.3\% & 1.78× & N/A \\
\hline
\multicolumn{6}{l}{\textit{RQ2: Advanced Feature Usage}} \\
Mean features per PR & TypeScript & 87.49 & 76.41 & 1.15× & <0.001*** \\
& C\# & 411.1 & 112.5 & 3.65× & <0.001*** \\
Median features & TypeScript & 25.0 & 12.0 & 2.08× & <0.001*** \\
& C\# & --- & --- & --- & --- \\
\hline
\multicolumn{6}{l}{\textit{RQ3: Acceptance Rates}} \\
Acceptance rate & TypeScript & 53.8\% & 25.3\% & 2.13× & <0.001*** \\
& C\# & 56.7\% & 100.0\% & 0.57× & --- \\
Sample size & TypeScript & n=545 & n=269 & --- & --- \\
& C\# & n=709 & n=44 & --- & --- \\
\hline
\end{tabular}
\end{table*}
```

---

## Threats to Validity (C# Specific):

1. **Small Human Sample**: Only 44 human C# PRs with 100% acceptance suggests:
   - High selection bias
   - Pre-vetted or curated submissions
   - Not representative of general C# development

2. **Agent Distribution**: C# dominated by Copilot (359) and OpenAI_Codex (346), only 4 Cursor PRs

3. **Generalizability**: C# findings should be presented as exploratory, TypeScript as primary evidence

---

## Final Recommendation:

**Use TypeScript as primary dataset for conclusions, C# as supporting evidence for:**
1. Confirming AI feature over-application is cross-language
2. Showing language culture affects type escape usage
3. Demonstrating need for larger, balanced samples in future work

**Do NOT claim**:
- Universal acceptance rate patterns (contradictory between languages)
- Generalizable type escape behavior (culture-dependent)


# LaTeX Tables for Cross-Language Analysis

## Table 1: Dataset Comparison

```latex
\begin{table}[h]
\centering
\caption{Dataset Characteristics: TypeScript vs C\# Type-Related PRs}
\label{tab:dataset_comparison}
\begin{tabular}{lrrrr}
\hline
& \multicolumn{2}{c}{\textbf{TypeScript}} & \multicolumn{2}{c}{\textbf{C\#}} \\
\textbf{Characteristic} & \textbf{AI} & \textbf{Human} & \textbf{AI} & \textbf{Human} \\
\hline
Total Type-Related PRs & 545 & 269 & 709 & 44 \\
Merged (Accepted) & 293 (53.8\%) & 68 (25.3\%) & 402 (56.7\%) & 44 (100\%) \\
With Escape Type & 225 (41.3\%) & 63 (23.4\%) & 29 (4.1\%) & 1 (2.3\%) \\
Mean Advanced Features & 87.49 & 76.41 & 411.1 & 112.5 \\
\hline
\end{tabular}
\end{table}
```

---

## Table 2: RQ1 - Type Escape Mechanism Comparison

```latex
\begin{table}[h]
\centering
\caption{RQ1: Type Escape Mechanism Usage (TypeScript \texttt{any} vs C\# \texttt{dynamic})}
\label{tab:rq1_comparison}
\begin{tabular}{llrrl}
\hline
\textbf{Language} & \textbf{Escape Type} & \textbf{AI Agent} & \textbf{Human} & \textbf{Interpretation} \\
\hline
TypeScript & \texttt{any} & 41.3\% & 23.4\% & High usage \\
& \quad Reduces safety & 70.2\% & 60.3\% & Adds $>$ Removes \\
& \quad Improves safety & 19.1\% & 7.9\% & AI 2.4× better \\
\hline
C\# & \texttt{dynamic} & 4.1\% & 2.3\% & Low usage \\
& \quad Sample size & n=29 & n=1 & Insufficient \\
\hline
\multicolumn{5}{l}{\textbf{Insight}: C\# developers (AI \& human) show 10× stronger type discipline} \\
\hline
\end{tabular}
\end{table}
```

---

## Table 3: RQ2 - Feature Usage Cross-Language

```latex
\begin{table}[h]
\centering
\caption{RQ2: Advanced Feature Usage Across Languages}
\label{tab:rq2_comparison}
\begin{tabular}{lrrrr}
\hline
& \multicolumn{2}{c}{\textbf{TypeScript}} & \multicolumn{2}{c}{\textbf{C\#}} \\
\textbf{Metric} & \textbf{AI} & \textbf{Human} & \textbf{AI} & \textbf{Human} \\
\hline
Mean Total Features & 87.49 & 76.41 & 411.1 & 112.5 \\
AI:Human Ratio & \multicolumn{2}{c}{1.15×} & \multicolumn{2}{c}{3.65×} \\
\hline
Median Features & 25.0 & 12.0 & --- & --- \\
AI:Human Ratio & \multicolumn{2}{c}{2.08×} & \multicolumn{2}{c}{---} \\
\hline
Mean Unique Features & 6.57 & 4.51 & 8.5 & 5.2 \\
AI:Human Ratio & \multicolumn{2}{c}{1.46×} & \multicolumn{2}{c}{1.63×} \\
\hline
Feature Density (/100 LoC) & 11.29 & 9.25 & --- & --- \\
AI:Human Ratio & \multicolumn{2}{c}{1.22×} & \multicolumn{2}{c}{---} \\
\hline
\multicolumn{5}{l}{\textbf{Pattern}: AI uses more features in BOTH languages (1.2-3.7× more)} \\
\hline
\end{tabular}
\end{table}
```

---

## Table 4: RQ3 - Acceptance Rates

```latex
\begin{table}[h]
\centering
\caption{RQ3: PR Acceptance Rates Across Languages}
\label{tab:rq3_comparison}
\begin{tabular}{lrrrrl}
\hline
\textbf{Language} & \textbf{AI Rate} & \textbf{Human Rate} & \textbf{Winner} & \textbf{$\chi^2$} & \textbf{p-value} \\
\hline
TypeScript & 53.8\% & 25.3\% & \textbf{AI} & 27.52 & <0.001*** \\
& (293/545) & (68/269) & (+28.5pp) & & \\
\hline
C\# & 56.7\% & 100.0\% & \textbf{Human} & --- & --- \\
& (402/709) & (44/44) & (+43.3pp) & & (biased) \\
\hline
\multicolumn{6}{l}{\textit{Note: C\# human sample (n=44) shows selection bias with perfect acceptance}} \\
\hline
\end{tabular}
\end{table}
```

---

## Table 5: Key Findings Summary

```latex
\begin{table*}[t]
\centering
\caption{Summary of Findings: AI vs Human Type Safety Practices}
\label{tab:summary_findings}
\small
\begin{tabular}{p{3.5cm}p{4cm}p{4cm}p{4cm}}
\hline
\textbf{Research Question} & \textbf{TypeScript Finding} & \textbf{C\# Finding} & \textbf{Cross-Language Conclusion} \\
\hline
\textbf{RQ1}: Type escape usage & AI modifies \texttt{any} more (41.3\% vs 23.4\%, p<0.001). 70.2\% reduce safety. & Rare \texttt{dynamic} usage (4.1\% vs 2.3\%). Insufficient for statistical tests. & Language culture determines escape type acceptance. AI adapts to norms. \\
\hline
\textbf{RQ2}: Advanced features & AI uses 2× more features (median: 25 vs 12, p<0.001). Over-applies patterns. & AI uses 3.7× more features (mean: 411 vs 112). Confirms over-application. & \textbf{Universal}: AI feature sprawl occurs across languages. Consistent pattern. \\
\hline
\textbf{RQ3}: Acceptance rates & AI achieves 2.1× higher acceptance (53.8\% vs 25.3\%, p<0.001). & Human achieves perfect acceptance (100\% vs 56.7\%). Small sample (n=44). & Acceptance patterns vary by language/sample. Cannot generalize. \\
\hline
\textbf{Overall Answer} & AI not better—bypasses with \texttt{any}, over-engineers, but achieves acceptance & Human curated sample performs perfectly. AI moderate success. & AI capability confirmed, but quality assessment is context-dependent \\
\hline
\end{tabular}
\end{table*}
```

---

## Figure Captions for Paper:

### TypeScript Figures:

**Figure 1**: Distribution of \texttt{any} type additions in TypeScript pull requests. AI agents show significantly higher usage (Mann-Whitney U: p<0.001, Cohen's d=0.316), indicating more frequent introduction of type safety escape mechanisms.

**Figure 2**: \texttt{any} type operations by AI agent in TypeScript. Devin and OpenAI\_Codex show highest modification rates, with all agents adding more than removing, suggesting systematic bypass behavior.

**Figure 3**: TypeScript advanced feature diversity by agent. AI agents use more unique features per PR (6.57 vs 4.51), but humans maintain universal feature adoption (100\% vs 92.7\%).

**Figure 4**: TypeScript advanced feature usage frequency. AI agents use 2-5× more of individual features (generics: 13.8 vs 3.1, type assertions: 10.2 vs 1.9), demonstrating capability without appropriate calibration.

**Figure 5**: TypeScript type safety feature adoption. AI over-relies on dangerous patterns: 4× more non-null assertions (8\% vs 2\%) and 5× more type casts, suppressing type checking mechanisms.

**Figure 6a**: TypeScript PR acceptance rates. AI agents achieve 2.13× higher acceptance (53.8\% vs 25.3\%, $\chi^2$=27.52, p<0.001), despite type safety concerns.

**Figure 6b**: TypeScript acceptance by individual agent. All AI agents outperform human baseline (50-56\% vs 25\%), showing consistent practical effectiveness across agent types.

### C# Figures:

**Figure 7**: \texttt{dynamic} type usage in C\# is rare (4.1\% AI, 2.3\% human), contrasting sharply with TypeScript's \texttt{any} usage (41.3\% AI, 23.4\% human), indicating stronger type discipline in C\# culture.

**Figure 8**: C\# advanced feature usage shows AI uses 3.65× more features (411 vs 112 per PR), confirming cross-language pattern of AI feature over-application.

**Figure 9**: C\# acceptance rates show human dominance (100\% vs 56.7\%), opposite of TypeScript pattern, attributable to small curated human sample (n=44).

---

## Statistical Test Summary:

```latex
\begin{table}[h]
\centering
\caption{Statistical Tests Summary}
\label{tab:stats_tests}
\begin{tabular}{llrrrl}
\hline
\textbf{Lang} & \textbf{Test} & \textbf{Statistic} & \textbf{p-value} & \textbf{Effect Size} & \textbf{Result} \\
\hline
\multicolumn{6}{l}{\textit{TypeScript}} \\
TS & \texttt{any} additions & U=80152.5 & <0.001*** & d=0.316 & Significant \\
TS & Total features & U=92627.0 & <0.001*** & --- & Significant \\
TS & Acceptance rate & $\chi^2$=27.52 & <0.001*** & --- & Significant \\
\hline
\multicolumn{6}{l}{\textit{C\#}} \\
C\# & \texttt{dynamic} usage & --- & N/A & --- & Insufficient data \\
C\# & Total features & --- & <0.001*** & --- & Significant \\
C\# & Acceptance rate & --- & --- & --- & Biased sample \\
\hline
\end{tabular}
\end{table}
```


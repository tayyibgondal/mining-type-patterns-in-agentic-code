"""
COMPREHENSIVE STATISTICAL ANALYSIS - ALL LANGUAGES
===================================================

Rigorous, publication-ready statistical testing for every research question
across all three languages studied: TypeScript, C#, and Rust.

For each language and RQ the script reports the appropriate test, the effect
size, and a plain-language conclusion, then writes:

  * console output (full narrative),
  * ALL_LANGUAGES_STATISTICAL_RESULTS.csv  (tidy summary table),
  * ALL_LANGUAGES_STATISTICAL_ANALYSIS.md  (formatted report for the paper).

Test choices
------------
RQ1 (escape-hatch intensity: any / dynamic / unsafe)
    - Prevalence  : Chi-square (or Fisher) on "PR has >=1 escape addition".
    - Intensity   : Mann-Whitney U on the non-zero additions per PR
                    (non-parametric: count data, heavy right tail / outliers).
RQ2 (advanced-feature usage)
    - Diversity   : Mann-Whitney U on unique features per PR.
    - Volume      : Mann-Whitney U on total features per PR.
    - Safety pat. : Chi-square (or Fisher) on adoption of the key anti-pattern.
RQ3 (PR acceptance)
    - Chi-square (or Fisher for small samples) on merged vs. not-merged.

Effect sizes
------------
    - Cohen's d              (mean-difference magnitude, continuous metrics)
    - Rank-biserial r        (Mann-Whitney companion, robust to non-normality)
    - Cramer's V / odds ratio (2x2 categorical comparisons)

Paths are resolved relative to the repository so the script runs from anywhere.
"""

import os
import re
import json
import warnings

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, chi2_contingency, fisher_exact

warnings.filterwarnings('ignore')

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
DATA = os.path.join(REPO, 'datasets')


# ----------------------------------------------------------------------------
# Metric extraction patterns (aligned with each language's figure scripts)
# ----------------------------------------------------------------------------

ANY_PATTERN = (r':\s*any[\s,;>\)\|&]|<any>|as\s+any|\|\s*any|&\s*any|'
               r'Array<any>|Promise<any>|Record<\w+,\s*any>|Record<any')
DYNAMIC_PATTERN = r'\bdynamic\s+\w+|\bdynamic\>|:\s*dynamic\b|<dynamic>'
UNSAFE_PATTERN = re.compile(r'\bunsafe\b')

TS_FEATURES = {
    'generics': r'<[A-Z]\w*(?:\s+extends\s+[^>]+)?(?:,\s*[A-Z]\w*(?:\s+extends\s+[^>]+)?)*>',
    'conditional_types': r'\s+extends\s+.*\s+\?\s+.*\s+:\s+',
    'mapped_types': r'\[\s*(?:K|P|T)\s+in\s+(?:keyof\s+)?[^\]]+\]',
    'template_literals': r'`[^`]*\$\{[^}]+\}[^`]*`',
    'utility_types': r'\b(?:Partial|Required|Readonly|Record|Pick|Omit|Exclude|Extract|NonNullable|Parameters|ConstructorParameters|ReturnType|InstanceType)\s*<',
    'type_guards': r'\b(?:is|asserts)\s+\w+',
    'satisfies': r'\bsatisfies\s+',
    'as_const': r'\bas\s+const\b',
    'non_null_assertion': r'!\.',
    'keyof_typeof': r'\b(?:keyof|typeof)\s+',
    'indexed_access': r'\[\s*(?:number|string|symbol)\s*\]',
    'intersection_types': r'&\s*\w+',
    'union_types': r'\|\s*\w+',
    'infer_keyword': r'\binfer\s+\w+',
    'enum_types': r'\benum\s+\w+\s*\{',
    'abstract_classes': r'\babstract\s+class\s+',
    'decorators': r'@\w+(?:\([^)]*\))?',
    'type_assertions': r'\bas\s+\w+',
    'optional_chaining': r'\?\.',
    'nullish_coalescing': r'\?\?',
}

CSHARP_FEATURES = {
    'generics': r'<[^<>]+>',
    'nullable': r'\w+\?(?!\?)',
    'null_forgiving': r'![\.\[\(]',
    'var_keyword': r'\bvar\s+\w+',
    'dynamic_keyword': r'\bdynamic\s+\w+',
    'record': r'\brecord\s+(?:class|struct)?\s*\w+',
    'init': r'\binit\s*;',
    'pattern_matching': r'\bis\s+(?:not\s+)?(?:\w+|\{)',
    'switch_expression': r'=>',
    'tuple': r'\([^)]*,\s*[^)]*\)',
    'async_await': r'\b(?:async|await)\b',
    'linq': r'\b(?:from|where|select|join|group)\s+\w+',
}

RUST_FEATURES = {
    'generics': r'<[^<>]+>',
    'lifetimes': r"'[a-zA-Z_]\w*\b",
    'trait_bound': r'<[^<>]*\b\w+\s*:\s*[A-Z]\w*[^<>]*>',
    'where_clause': r'\bwhere\s+\w+\s*:',
    'impl_trait': r'\bimpl\s+[A-Z]\w*',
    'dyn_trait': r'\bdyn\s+[A-Z]\w*',
    'box_dyn': r'\bBox\s*<\s*dyn\s+',
    'type_alias': r'\btype\s+[A-Z]\w*\s*(<[^>]*>)?\s*=',
    'derive': r'#\[derive\([^\)]+\)\]',
    'match_expr': r'\bmatch\s+\w',
    'if_let': r'\b(?:if|while)\s+let\b',
    'enum_def': r'\benum\s+[A-Z]\w*',
    'struct_def': r'\bstruct\s+[A-Z]\w*',
    'trait_def': r'\btrait\s+[A-Z]\w*',
    'smart_pointer': r'\b(?:Arc|Rc|Mutex|RwLock|RefCell|Cell)\s*<',
    'option_result': r'\b(?:Option|Result)\s*<',
    'unsafe_impl': r'\bunsafe\s+impl\b',
    'transmute': r'\bmem::transmute\b|\btransmute\s*::\s*<',
    'any_trait': r'\b(?:std::)?any::Any\b|\bdyn\s+Any\b',
}


def added_lines(patch):
    return '\n'.join(l[1:] for l in str(patch).split('\n')
                     if l.startswith('+') and not l.startswith('+++'))


def escape_additions(df, pattern, ignorecase=False):
    """Per-PR count of escape-hatch additions (any / dynamic)."""
    flags = re.IGNORECASE if ignorecase else 0
    out = []
    for _, r in df.iterrows():
        text = added_lines(r.get('patch_text', ''))
        out.append(len(re.findall(pattern, text, flags)))
    return np.array(out)


def unsafe_additions(df):
    """Per-PR count of `unsafe` additions (uses precomputed column if present)."""
    if 'unsafe_additions' in df.columns:
        return pd.to_numeric(df['unsafe_additions'], errors='coerce').fillna(0).astype(int).values
    out = []
    for _, r in df.iterrows():
        adds = 0
        for line in str(r.get('patch_text', '')).split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                adds += len(UNSAFE_PATTERN.findall(line))
        out.append(adds)
    return np.array(out)


def feature_frame(df, feature_map):
    rows = []
    for _, r in df.iterrows():
        text = added_lines(r.get('patch_text', ''))
        counts = {name: len(re.findall(pat, text, re.IGNORECASE))
                  for name, pat in feature_map.items()}
        counts['total'] = sum(counts[k] for k in feature_map)
        counts['unique'] = sum(1 for k in feature_map if counts[k] > 0)
        rows.append(counts)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Statistics helpers
# ----------------------------------------------------------------------------

def cohens_d(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return 0.0
    v1, v2 = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled = np.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    return float((np.mean(a) - np.mean(b)) / pooled) if pooled > 0 else 0.0


def rank_biserial(u, n1, n2):
    """Rank-biserial correlation from Mann-Whitney U (effect size in [-1, 1]).

    `u` is scipy's U for group 1 (AI). Sign convention here matches Cohen's d:
    positive => group 1 (AI) tends to have the larger values.
    """
    if n1 == 0 or n2 == 0:
        return 0.0
    return float((2.0 * u) / (n1 * n2) - 1.0)


def cramers_v(chi2, n, r, c):
    denom = n * (min(r, c) - 1)
    return float(np.sqrt(chi2 / denom)) if denom > 0 else 0.0


def interp_d(d):
    d = abs(d)
    return ("negligible" if d < 0.2 else "small" if d < 0.5
            else "medium" if d < 0.8 else "large")


def interp_v(v):
    v = abs(v)
    return ("negligible" if v < 0.1 else "small" if v < 0.3
            else "medium" if v < 0.5 else "large")


def stars(p):
    return ("***" if p < 0.001 else "**" if p < 0.01
            else "*" if p < 0.05 else "ns")


def mw(a, b):
    """Mann-Whitney U with rank-biserial + Cohen's d. Returns dict."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 1 or len(b) < 1:
        return None
    u, p = mannwhitneyu(a, b, alternative='two-sided')
    return {
        'n1': len(a), 'n2': len(b),
        'median1': float(np.median(a)), 'median2': float(np.median(b)),
        'mean1': float(np.mean(a)), 'mean2': float(np.mean(b)),
        'U': float(u), 'p': float(p),
        'rank_biserial': rank_biserial(u, len(a), len(b)),
        'cohens_d': cohens_d(a, b),
    }


def proportion_test(succ1, n1, succ2, n2):
    """2x2 categorical test. Fisher if any group small, else chi-square."""
    table = np.array([[succ1, n1 - succ1], [succ2, n2 - succ2]])
    if min(n1, n2) < 50 or (table < 5).any():
        odds, p = fisher_exact(table)
        return {'test': "Fisher's exact", 'stat': float(odds), 'stat_name': 'odds ratio',
                'p': float(p), 'cramers_v': None,
                'p1': succ1 / n1 if n1 else 0, 'p2': succ2 / n2 if n2 else 0,
                'succ1': succ1, 'n1': n1, 'succ2': succ2, 'n2': n2}
    chi2, p, dof, _ = chi2_contingency(table)
    return {'test': 'Chi-square', 'stat': float(chi2), 'stat_name': 'chi2',
            'p': float(p), 'cramers_v': cramers_v(chi2, table.sum(), *table.shape),
            'p1': succ1 / n1, 'p2': succ2 / n2,
            'succ1': succ1, 'n1': n1, 'succ2': succ2, 'n2': n2}


# ----------------------------------------------------------------------------
# Per-language configuration
# ----------------------------------------------------------------------------

LANGUAGES = {
    'TypeScript': {
        'agent': 'typescript_data/agent_type_prs_filtered_by_open_ai.csv',
        'human': 'typescript_data/human_type_prs_filtered_by_open_ai.csv',
        'escape_name': 'any',
        'features': TS_FEATURES,
        'safety_feature': ('non_null_assertion', 'Non-null assertion (!.) adoption'),
    },
    'C#': {
        'agent': 'csharp_data/csharp_classified_type_prs.csv',
        'human': 'csharp_data/human_csharp_classified_type_prs.csv',
        'escape_name': 'dynamic',
        'features': CSHARP_FEATURES,
        'safety_feature': ('null_forgiving', 'Null-forgiving operator (!) adoption'),
    },
    'Rust': {
        'agent': 'rust_data/rust_classified_type_prs.csv',
        'human': 'rust_data/human_rust_classified_type_prs.csv',
        'escape_name': 'unsafe',
        'features': RUST_FEATURES,
        'safety_feature': ('unsafe_impl', 'unsafe impl adoption'),
    },
}


def load(rel):
    df = pd.read_csv(os.path.join(DATA, rel))
    if 'final_is_type_related' in df.columns:
        df = df[df['final_is_type_related'] == True]
    return df


def analyze_language(lang, cfg):
    agent = load(cfg['agent'])
    human = load(cfg['human'])
    esc = cfg['escape_name']
    rows = []

    section = []
    section.append(f"\n{'=' * 80}\n{lang.upper()}  (AI n={len(agent)}, Human n={len(human)})\n{'=' * 80}")

    # ---- escape additions ----
    if esc == 'any':
        a_esc = escape_additions(agent, ANY_PATTERN)
        h_esc = escape_additions(human, ANY_PATTERN)
    elif esc == 'dynamic':
        a_esc = escape_additions(agent, DYNAMIC_PATTERN, ignorecase=True)
        h_esc = escape_additions(human, DYNAMIC_PATTERN, ignorecase=True)
    else:  # unsafe
        a_esc = unsafe_additions(agent)
        h_esc = unsafe_additions(human)

    # RQ1a: prevalence (proportion of PRs with >=1 escape addition)
    prev = proportion_test(int((a_esc > 0).sum()), len(a_esc),
                           int((h_esc > 0).sum()), len(h_esc))
    section.append(f"\n[RQ1a] '{esc}' prevalence (PRs with >=1 addition)")
    section.append(f"  Test: {prev['test']}")
    section.append(f"  AI  : {prev['succ1']}/{prev['n1']} ({prev['p1']*100:.1f}%)")
    section.append(f"  Hum : {prev['succ2']}/{prev['n2']} ({prev['p2']*100:.1f}%)")
    vtxt = f", Cramer's V={prev['cramers_v']:.3f} ({interp_v(prev['cramers_v'])})" if prev['cramers_v'] is not None else f", odds ratio={prev['stat']:.3f}"
    section.append(f"  {prev['stat_name']}={prev['stat']:.3f}, p={prev['p']:.4g} {stars(prev['p'])}{vtxt}")
    rows.append(dict(Language=lang, RQ='RQ1', Metric=f"'{esc}' prevalence",
                     Test=prev['test'], AI=f"{prev['p1']*100:.1f}%", Human=f"{prev['p2']*100:.1f}%",
                     p=prev['p'], Sig=stars(prev['p']),
                     Effect=(f"V={prev['cramers_v']:.3f}" if prev['cramers_v'] is not None else f"OR={prev['stat']:.2f}")))

    # RQ1b: intensity on non-zero additions (matches boxplot)
    m = mw(a_esc[a_esc > 0], h_esc[h_esc > 0])
    section.append(f"\n[RQ1b] '{esc}' intensity | additions per PR (non-zero only)")
    if m:
        section.append(f"  Test: Mann-Whitney U (non-parametric)")
        section.append(f"  n: AI={m['n1']}, Human={m['n2']}")
        section.append(f"  median: AI={m['median1']:.2f}, Human={m['median2']:.2f} | mean: AI={m['mean1']:.2f}, Human={m['mean2']:.2f}")
        section.append(f"  U={m['U']:.1f}, p={m['p']:.4g} {stars(m['p'])} | rank-biserial r={m['rank_biserial']:.3f}, Cohen's d={m['cohens_d']:.3f} ({interp_d(m['cohens_d'])})")
        rows.append(dict(Language=lang, RQ='RQ1', Metric=f"'{esc}' intensity (per PR)",
                         Test='Mann-Whitney U', AI=f"{m['median1']:.2f} (med)", Human=f"{m['median2']:.2f} (med)",
                         p=m['p'], Sig=stars(m['p']), Effect=f"d={m['cohens_d']:.2f}, r={m['rank_biserial']:.2f}"))
    else:
        section.append("  Insufficient non-zero data.")

    # ---- features ----
    af = feature_frame(agent, cfg['features'])
    hf = feature_frame(human, cfg['features'])

    md = mw(af['unique'], hf['unique'])
    section.append(f"\n[RQ2a] Feature diversity | unique advanced features per PR")
    section.append(f"  Test: Mann-Whitney U")
    section.append(f"  median: AI={md['median1']:.2f}, Human={md['median2']:.2f} | mean: AI={md['mean1']:.2f}, Human={md['mean2']:.2f}")
    section.append(f"  U={md['U']:.1f}, p={md['p']:.4g} {stars(md['p'])} | rank-biserial r={md['rank_biserial']:.3f}, Cohen's d={md['cohens_d']:.3f} ({interp_d(md['cohens_d'])})")
    rows.append(dict(Language=lang, RQ='RQ2', Metric='Feature diversity (unique/PR)',
                     Test='Mann-Whitney U', AI=f"{md['mean1']:.2f}", Human=f"{md['mean2']:.2f}",
                     p=md['p'], Sig=stars(md['p']), Effect=f"d={md['cohens_d']:.2f}, r={md['rank_biserial']:.2f}"))

    mt = mw(af['total'], hf['total'])
    section.append(f"\n[RQ2b] Feature volume | total advanced features per PR")
    section.append(f"  Test: Mann-Whitney U")
    section.append(f"  median: AI={mt['median1']:.2f}, Human={mt['median2']:.2f} | mean: AI={mt['mean1']:.2f}, Human={mt['mean2']:.2f}")
    section.append(f"  U={mt['U']:.1f}, p={mt['p']:.4g} {stars(mt['p'])} | rank-biserial r={mt['rank_biserial']:.3f}, Cohen's d={mt['cohens_d']:.3f} ({interp_d(mt['cohens_d'])})")
    rows.append(dict(Language=lang, RQ='RQ2', Metric='Feature volume (total/PR)',
                     Test='Mann-Whitney U', AI=f"{mt['mean1']:.2f}", Human=f"{mt['mean2']:.2f}",
                     p=mt['p'], Sig=stars(mt['p']), Effect=f"d={mt['cohens_d']:.2f}, r={mt['rank_biserial']:.2f}"))

    # safety anti-pattern adoption
    sf_col, sf_label = cfg['safety_feature']
    if sf_col in af.columns:
        sp = proportion_test(int((af[sf_col] > 0).sum()), len(af),
                             int((hf[sf_col] > 0).sum()), len(hf))
        section.append(f"\n[RQ2c] Safety anti-pattern | {sf_label}")
        section.append(f"  Test: {sp['test']}")
        section.append(f"  AI={sp['p1']*100:.1f}% ({sp['succ1']}/{sp['n1']}), Human={sp['p2']*100:.1f}% ({sp['succ2']}/{sp['n2']})")
        vtxt = f", Cramer's V={sp['cramers_v']:.3f} ({interp_v(sp['cramers_v'])})" if sp['cramers_v'] is not None else f", odds ratio={sp['stat']:.3f}"
        section.append(f"  {sp['stat_name']}={sp['stat']:.3f}, p={sp['p']:.4g} {stars(sp['p'])}{vtxt}")
        rows.append(dict(Language=lang, RQ='RQ2', Metric=sf_label,
                         Test=sp['test'], AI=f"{sp['p1']*100:.1f}%", Human=f"{sp['p2']*100:.1f}%",
                         p=sp['p'], Sig=stars(sp['p']),
                         Effect=(f"V={sp['cramers_v']:.3f}" if sp['cramers_v'] is not None else f"OR={sp['stat']:.2f}")))

    # ---- acceptance ----
    a_merged = int(agent['merged_at'].notna().sum())
    h_merged = int(human['merged_at'].notna().sum())
    acc = proportion_test(a_merged, len(agent), h_merged, len(human))
    section.append(f"\n[RQ3] PR acceptance (merged)")
    section.append(f"  Test: {acc['test']}")
    section.append(f"  AI={acc['p1']*100:.1f}% ({a_merged}/{len(agent)}), Human={acc['p2']*100:.1f}% ({h_merged}/{len(human)})")
    vtxt = f", Cramer's V={acc['cramers_v']:.3f} ({interp_v(acc['cramers_v'])})" if acc['cramers_v'] is not None else f", odds ratio={acc['stat']:.3f}"
    section.append(f"  {acc['stat_name']}={acc['stat']:.3f}, p={acc['p']:.4g} {stars(acc['p'])}{vtxt}")
    rows.append(dict(Language=lang, RQ='RQ3', Metric='PR acceptance rate',
                     Test=acc['test'], AI=f"{acc['p1']*100:.1f}%", Human=f"{acc['p2']*100:.1f}%",
                     p=acc['p'], Sig=stars(acc['p']),
                     Effect=(f"V={acc['cramers_v']:.3f}" if acc['cramers_v'] is not None else f"OR={acc['stat']:.2f}")))

    return "\n".join(section), rows


def to_markdown(all_rows):
    lines = []
    lines.append("# Comprehensive Statistical Analysis — All Languages\n")
    lines.append("Statistical comparison of AI-agent vs. human developers on type-related "
                 "pull requests across **TypeScript**, **C#**, and **Rust**.\n")
    lines.append("**Significance:** `*` p<0.05, `**` p<0.01, `***` p<0.001, `ns` not significant.  \n"
                 "**Effect sizes:** Cohen's *d* / rank-biserial *r* (continuous, Mann-Whitney), "
                 "Cramer's *V* / odds ratio (categorical).\n")
    for rq, title in [('RQ1', 'RQ1 — Escape-Hatch Type Usage (`any` / `dynamic` / `unsafe`)'),
                      ('RQ2', 'RQ2 — Advanced Feature Usage'),
                      ('RQ3', 'RQ3 — PR Acceptance')]:
        lines.append(f"\n## {title}\n")
        lines.append("| Language | Metric | Test | AI | Human | p-value | Sig | Effect size |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in all_rows:
            if r['RQ'] != rq:
                continue
            lines.append(f"| {r['Language']} | {r['Metric']} | {r['Test']} | {r['AI']} | "
                         f"{r['Human']} | {r['p']:.4g} | {r['Sig']} | {r['Effect']} |")
    lines.append("\n## Notes\n")
    lines.append("- **Mann-Whitney U** is used for per-PR count metrics because they are "
                 "right-skewed with heavy outliers (normality violated); it compares "
                 "distributions/medians rather than means.\n")
    lines.append("- **Fisher's exact test** replaces chi-square whenever a group is small "
                 "(n<50) or an expected cell count is <5, which applies to the smaller "
                 "human samples (notably C# and Rust).\n")
    lines.append("- Intensity rows (RQ1b) are computed on PRs with at least one escape "
                 "addition, matching the box-plots; prevalence rows (RQ1a) use all PRs.\n")
    return "\n".join(lines)


def main():
    print("=" * 80)
    print("COMPREHENSIVE STATISTICAL ANALYSIS — TypeScript, C#, Rust")
    print("=" * 80)

    all_rows = []
    for lang, cfg in LANGUAGES.items():
        text, rows = analyze_language(lang, cfg)
        print(text)
        all_rows.extend(rows)

    # tidy summary
    summary = pd.DataFrame(all_rows)[
        ['Language', 'RQ', 'Metric', 'Test', 'AI', 'Human', 'p', 'Sig', 'Effect']]
    csv_path = os.path.join(HERE, 'ALL_LANGUAGES_STATISTICAL_RESULTS.csv')
    summary.to_csv(csv_path, index=False)

    md_path = os.path.join(HERE, 'ALL_LANGUAGES_STATISTICAL_ANALYSIS.md')
    with open(md_path, 'w') as f:
        f.write(to_markdown(all_rows))

    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print(summary.to_string(index=False))
    print(f"\nSaved: {csv_path}")
    print(f"Saved: {md_path}")


if __name__ == '__main__':
    main()

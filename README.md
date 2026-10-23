# Do AI Agents Bypass the Type Checker More Than Humans?

Mining type-system constructs and escape hatches in TypeScript, C#, and Rust
pull requests, comparing AI coding agents against human developers.

Paper source lives in `FSE2027/` (a submodule, targeted at MSR 2027).

---

## Reproducing the numbers in the paper

This is the short answer for anyone who just wants to re-run the analysis.

### 1. Get the data

Download the shared bundle:

**https://drive.google.com/drive/u/0/folders/1BfO5JT9PcROU3ZqTZqgbgW-KfMtN7V-A**

You only need one folder from it, `02_pipeline_output/`. Copy the three
`stage2_corpus.parquet` files into this repository so that they land here:

| From the Drive bundle | Put it here |
|---|---|
| `02_pipeline_output/typescript/stage2_corpus.parquet` | `datasets/typescript_data/stage2_corpus.parquet` |
| `02_pipeline_output/csharp/stage2_corpus.parquet` | `datasets/csharp_data/stage2_corpus.parquet` |
| `02_pipeline_output/rust/stage2_corpus.parquet` | `datasets/rust_data/stage2_corpus.parquet` |

That is about 41 MB in total. `stage2_corpus.parquet` is the final corpus, one
row per pull request, after both filtering stages. It already carries every
construct count as its own column, so nothing is recounted at analysis time.

The same three files are also in `03_final_corpus_csv/` as CSV if you would
rather read them in something other than pandas. The analysis scripts read the
Parquet files, not the CSVs.

`datasets/` is in `.gitignore`, so no data ships with this repository and you
will not accidentally commit it back.

### 2. Install

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run

Three commands, in this order. None of them needs an API key, a network
connection, or a GPU, and together they take well under a minute.

```bash
# Every statistical test in the paper -> analysis/results/
python3 analysis/run_analysis.py

# Tables 1 and 4 as LaTeX -> final_figures_for_paper/
python3 scripts/make_tables.py

# All 12 figures as PDF and PNG -> final_figures_for_paper/
cd final_figures_for_paper && python3 make_all.py && cd ..
```

### 4. Where the results land

| Script | Writes | Contains |
|---|---|---|
| `analysis/run_analysis.py` | `analysis/results/STATISTICAL_REPORT.md` | All 153 tests as Markdown tables, grouped by language and research question. This is the file to read. |
| | `analysis/results/statistical_results.csv` | The same 153 tests as one row each, for sorting and filtering. |
| `scripts/make_tables.py` | `final_figures_for_paper/table_corpus.tex` | Corpus sizes at each pipeline stage (Table 1). |
| | `final_figures_for_paper/table_acceptance.tex` | Merge rates by language and group (Table 4). |
| | `final_figures_for_paper/table_numbers.json` | Every number in those two tables, machine-readable. |
| `final_figures_for_paper/make_all.py` | `final_figures_for_paper/fig*.pdf` and `fig*.png` | The figures. The paper uses `fig1`, `fig2`, `fig6`, `fig7`, and `fig8`. |

To check a specific claim against the paper, open `STATISTICAL_REPORT.md` and
find the language heading, then the research question. For example, the C#
null-forgiving operator result is under `## C#` and `### RQ2 escape hatches`.

### Useful flags

```bash
# One language at a time
python3 analysis/run_analysis.py --language Rust

# Analyse the Stage 1 corpus instead of the final one. Reports are labelled
# with which stage they came from, so the two cannot be confused.
python3 analysis/run_analysis.py --stage stage1
```

Both flags write to the same two output files, so a `--language Rust` run
replaces the full report with a Rust-only one. Re-run without the flag to get
everything back.

For `--stage stage1` you also need `stage1_agent.parquet` and
`stage1_human.parquet` from the same Drive folder.

---

## Rebuilding the corpus from scratch

Only needed if you want to change the construct catalogue or the filtering. It
costs money (Stage 2 calls an LLM) and takes hours.

```bash
# 0. Cache the AIDev dataset locally, 1.33 GB, so the extractors stop
#    re-downloading it from HuggingFace on every run.
python3 scripts/cache_aidev.py

# 1. Map the GitHub human scrape into the canonical schema.
python3 scripts/normalise_human_corpus.py

# 2. Stage 1, the recall-oriented regex filter.
python3 scripts/stage1_extract.py --language TypeScript --group agent

# 3. Stage 2, the precision-oriented LLM filter. Needs OPENAI_API_KEY in .env.
#    Responses are cached, so a killed run resumes for free.
python3 scripts/stage2_run.py --stage classify --language TypeScript
python3 scripts/stage2_run.py --stage validate --language TypeScript
```

Both stage scripts take `--language` and `--group` repeatedly, and `--limit`
for a smoke test. Check `python3 scripts/probe_model.py` first if you change
models, since it records which of `temperature`, `seed`, and `json_schema` the
model accepts.

---

## Layout

| Path | What it is |
|---|---|
| `catalogue/` | The single source of truth for what a construct is. One record per catalogue ID, plus the shared diff preprocessing, counting, and Stage 1 retention rule. Every other module imports from here. |
| `analysis/` | `run_analysis.py` runs the research questions, `stats.py` holds the tests themselves, `results/` holds the output. |
| `scripts/` | The pipeline, one stage per file, plus the table and annotation-workbook generators. |
| `final_figures_for_paper/` | Figure scripts, the figures they produce, and the generated tables. |
| `tests/` | Pattern tests for the catalogue. At least 10 positive and 10 negative lines per construct. Run with `pytest tests/`. |
| `docs/` | The construct taxonomy, the statistical methodology, and a log of every paper number that changed. |
| `FSE2027/` | The paper, as a git submodule. Work on the `revision` branch. |
| `legacy/` | Superseded code, kept for provenance. Nothing here is imported by anything live. |

### What is in `legacy/`

The per-language extractors and classifiers that the current pipeline replaced.
Six extractors became `scripts/stage1_extract.py`, three LLM classifiers became
`llm_stage2.py` and `scripts/stage2_run.py`, and `data_analysis/` became
`analysis/`. They are kept because the pre-rerun numbers came from them, not
because they still work against the current schema.

---

## Things worth knowing

- **The figures are deterministic but their PDFs are not byte-identical.**
  Matplotlib stamps a creation date into each PDF, so `git status` shows every
  `fig*.pdf` as modified after a rerun even when nothing changed. The PNGs are
  byte-stable, so compare those if you want to confirm a figure is unchanged.

- **The paper keeps its own copies of the figures and tables.** Regenerating
  them in `final_figures_for_paper/` does not update the paper. Copy them into
  `FSE2027/fse-figures/` and `FSE2027/fse-tables/` and rebuild.

- **`FSE2027/fse-tables/table_corpus.tex` has a hand-edited header** that wraps
  "After Regex" and "After LLM" onto two lines. Regenerating the table
  overwrites that, so re-apply it or the column headers get wide. The numbers
  are identical either way.

- **Construct counts are read, never recounted.** The extractor writes one
  column per construct and the analysis reads those columns. Earlier versions
  recomputed counts from `patch_text` at report time with a second set of
  regexes, and the two sets disagreed. If you add a construct, it has to go
  through `catalogue/` and the corpus has to be re-extracted.

- **`pr_key` is the primary key everywhere** and every stage asserts it is
  unique before doing anything. It joins the language, the repository, and the
  PR number.

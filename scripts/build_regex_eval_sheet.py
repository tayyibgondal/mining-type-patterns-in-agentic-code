"""Build the Stage 1 (regex parser) evaluation workbook.

One workbook per language. 50 PRs per language, drawn as 25 the parser retained
and 25 it rejected, with a fixed seed so the sample is reproducible.

Layout, following the sheet used for the earlier evaluation:

  Instructions  what to judge and how, plus the confusion-matrix legend
  Evaluation    one row per PR, with the full detail needed to decide:
                title, body, the parser's own construct counts, which signal
                fired, and a long diff excerpt. Then:
                  - Tayyib (y/n)       pre-filled from an automated read
                  - Tayyib_reasoning   why that pre-filled answer was given
                  - Imgyeong (y/n)     blank, for independent annotation
                  - Agreement          formula, filled once both are present
  Metrics       accuracy, precision, recall, specificity, F1 per annotator,
                plus raw percent agreement between them

IMPORTANT, and it must be described honestly in the paper: the Tayyib column
arrives PRE-FILLED by an automated heuristic read of each PR, with its
reasoning shown. It is a starting point to review and correct, not an
independent human judgement. Two independent annotators with Cohen's kappa is
a different claim from one reviewed automatic pass plus one human pass, and
the paper must say which it did. Nothing here computes kappa, because kappa on
a pre-filled column would overstate agreement.
"""
from __future__ import annotations

import argparse
import random
import re
import sys
import textwrap
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from catalogue.constructs import LANGUAGES, constructs_for  # noqa: E402

DATA_DIR = {
    "TypeScript": REPO / "datasets" / "typescript_data",
    "C#": REPO / "datasets" / "csharp_data",
    "Rust": REPO / "datasets" / "rust_data",
}
OUTDIR = REPO / "datasets" / "evaluation"

# Diffs contain ANSI colour escapes and other control bytes (tree output,
# terminal captures pasted into PR bodies). openpyxl refuses those outright,
# so every string is scrubbed before it reaches a cell.
_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def clean(value, limit: int | None = None) -> object:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    text = str(value)
    text = _ANSI.sub("", text)
    text = _ILLEGAL.sub(" ", text)
    if limit is not None:
        text = text[:limit]
    # Excel's own hard ceiling on a cell.
    return text[:32_000]


SEED = 42
N_PER_CLASS = 25
ANNOTATORS = ("Tayyib", "Imgyeong")

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(color="FFFFFF", bold=True)
PREFILL_FILL = PatternFill("solid", fgColor="FFF2CC")
BLANK_FILL = PatternFill("solid", fgColor="E2EFDA")


# --------------------------------------------------------------------------
# Population
# --------------------------------------------------------------------------

def build_population(language: str) -> pd.DataFrame:
    """Retained and rejected PRs, re-deriving rejects by re-running Stage 1.

    `stage1_extract.py` writes only retained rows, so the rejected half of the
    sample is recomputed here rather than stored, keeping the extractor output
    small.
    """
    from catalogue.count import count_prepared
    from catalogue.preprocess import prepare, prepare_files
    from catalogue.retain import decide
    from catalogue import aidev

    retained = []
    for group in ("agent", "human"):
        path = DATA_DIR[language] / f"stage1_{group}.parquet"
        if path.exists():
            frame = pd.read_parquet(path)
            frame["parser_prediction"] = "construct_related"
            retained.append(frame)
    retained_frame = pd.concat(retained, ignore_index=True)
    retained_keys = set(retained_frame.pr_key)

    # Rejected side: sample candidates from the human corpus (cheap to read)
    # and keep the ones Stage 1 turned down.
    human_path = DATA_DIR[language] / "human_corpus.parquet"
    rejected_rows = []
    if human_path.exists():
        human = pd.read_parquet(human_path)
        human = human[~human.pr_key.isin(retained_keys)]
        rng = random.Random(SEED)
        index = list(human.index)
        rng.shuffle(index)
        for idx in index[:400]:
            row = human.loc[idx].to_dict()
            prepared = prepare(row.get("patch_text"), language)
            counts = count_prepared(prepared, language)
            decision = decide(prepared, counts, row.get("title"),
                              row.get("body"), language)
            if decision.retained:
                continue
            row.update(counts)
            row.update(files_counted=prepared.files_counted,
                       lines_added=prepared.lines_added,
                       lines_removed=prepared.lines_removed,
                       construct_total=decision.construct_total,
                       detection_method="rejected",
                       parser_prediction="not_construct_related",
                       patch_excerpt=(row.get("patch_text") or "")[:6000])
            row.pop("patch_text", None)
            rejected_rows.append(row)
            if len(rejected_rows) >= 200:
                break

    rejected_frame = pd.DataFrame(rejected_rows)
    return retained_frame, rejected_frame


def sample(retained: pd.DataFrame, rejected: pd.DataFrame) -> pd.DataFrame:
    rng = random.Random(SEED)
    pos = retained.sample(n=min(N_PER_CLASS, len(retained)),
                          random_state=SEED)
    neg = (rejected.sample(n=min(N_PER_CLASS, len(rejected)),
                           random_state=SEED)
           if len(rejected) else rejected)
    out = pd.concat([pos, neg], ignore_index=True)
    order = list(out.index)
    rng.shuffle(order)
    return out.loc[order].reset_index(drop=True)


# --------------------------------------------------------------------------
# Pre-filled judgement
# --------------------------------------------------------------------------

def counts_detail(row, language: str) -> str:
    parts = []
    for c in constructs_for(language):
        added = int(row.get(c.add_col, 0) or 0)
        removed = int(row.get(c.rem_col, 0) or 0)
        if added or removed:
            parts.append(f"{c.display_name} [{c.id}] +{added}/-{removed}")
    return "; ".join(parts) if parts else "no catalogue construct detected"


def prefill(row, language: str) -> tuple[str, str]:
    """A reasoned starting answer, with the reasoning written out.

    Deliberately conservative and rule-stated, so a reviewer can see exactly
    what it keyed on and overrule it. This is not an independent judgement.
    """
    escape = sum(int(row.get(c.add_col, 0) or 0) + int(row.get(c.rem_col, 0) or 0)
                 for c in constructs_for(language)
                 if c.family in ("escape", "suppression"))
    expressive = sum(int(row.get(c.add_col, 0) or 0)
                     for c in constructs_for(language)
                     if c.family in ("expressiveness", "safety"))
    files = int(row.get("files_counted", 0) or 0)
    method = str(row.get("detection_method", ""))
    title = str(row.get("title") or "")

    if files == 0:
        return "n", ("No hand-written source file of the target language was "
                     "changed, so there is nothing for the parser to be right "
                     "about.")
    if method == "rejected":
        return "n", (f"Stage 1 rejected this PR. It touches {files} source "
                     f"file(s) but matched no catalogue construct and carried "
                     f"no construct-related cue in the title or body. "
                     f"Detected: {counts_detail(row, language)}.")
    if method == "cue":
        return "n", (f"Retained on a title/body cue alone, the weakest signal, "
                     f"with no construct pattern in the diff. Title: "
                     f"\"{title[:110]}\". Verify whether the prose promise is "
                     f"borne out by the change; if not this is a false "
                     f"positive.")
    if escape > 0:
        return "y", (f"The diff adds or removes escape-hatch or suppression "
                     f"constructs, which is the core of RQ2. "
                     f"{counts_detail(row, language)}. Signal: {method}.")
    if expressive >= 3:
        return "y", (f"Multiple type-level constructs changed across {files} "
                     f"file(s): {counts_detail(row, language)}. Signal: "
                     f"{method}. Treated as genuine type work rather than "
                     f"incidental token overlap.")
    return "?", (f"Borderline. Only {expressive} expressiveness construct(s) "
                 f"and no escape hatch: {counts_detail(row, language)}. The "
                 f"match may be incidental to a change made for another "
                 f"reason. Needs a human read of the full diff.")


# --------------------------------------------------------------------------
# Workbook
# --------------------------------------------------------------------------

COLUMNS = [
    ("#", 5), ("pr_key", 34), ("group", 8), ("agent", 13),
    ("title", 46), ("html_url", 34),
    ("files", 7), ("lines_added", 8), ("signal", 13),
    ("parser_prediction", 20),
    ("construct_counts", 52), ("body_excerpt", 52), ("diff_excerpt", 80),
]


def write_workbook(language: str, frame: pd.DataFrame, dest: Path) -> None:
    wb = Workbook()

    # ---- Instructions -------------------------------------------------
    ws = wb.active
    ws.title = "Instructions"
    text = textwrap.dedent(f"""
    Stage 1 regex parser evaluation - {language}

    WHAT YOU ARE JUDGING
    For each pull request, decide whether it GENUINELY involves {language}
    type-system or type-safety work. Answer in your own column: y or n.

    Answer y if the PR adds, removes or meaningfully changes type annotations,
    generics, trait bounds, lifetimes, escape hatches (any / dynamic / unsafe /
    non-null assertions / casts / unwrap), suppression directives, or
    safety-enhancing constructs, in hand-written source.

    Answer n if the type-like tokens are incidental: a rename, a dependency
    bump, generated code, reformatting, or a construct that merely appears in a
    line touched for an unrelated reason.

    The column "parser_prediction" is what the regex parser decided. Do not let
    it lead you; your label is the ground truth it is scored against.

    HOW THE TWO COLUMNS WORK
    - Tayyib (y/n) arrives PRE-FILLED by an automated read of each PR, and
      Tayyib_reasoning says why. Review every row and correct it where you
      disagree. A "?" means the automated read could not decide and a human
      must.
    - Imgyeong (y/n) is blank and must be filled independently, WITHOUT
      reading the Tayyib columns first, or the agreement figure is meaningless.

    HONEST REPORTING NOTE
    Because one column starts pre-filled, this is not two independent human
    annotations. The paper must describe it as one reviewed automatic pass plus
    one independent human pass, and must not report Cohen's kappa as if both
    columns were independent.

    CONFUSION MATRIX (positive class = genuinely construct-related)
      TP  parser said construct_related      and you said y
      FP  parser said construct_related      and you said n
      TN  parser said not_construct_related  and you said n
      FN  parser said not_construct_related  and you said y

    Sample: {N_PER_CLASS} retained + {N_PER_CLASS} rejected PRs, seed {SEED}.
    """).strip()
    for i, line in enumerate(text.split("\n"), start=1):
        ws.cell(row=i, column=1, value=clean(line))
    ws.column_dimensions["A"].width = 100

    # ---- Evaluation ---------------------------------------------------
    ev = wb.create_sheet("Evaluation")
    headers = [c for c, _ in COLUMNS]
    headers += ["Tayyib (y/n)", "Tayyib_reasoning", "Imgyeong (y/n)",
                "Agreement"]
    for col, name in enumerate(headers, start=1):
        cell = ev.cell(row=1, column=col, value=name)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for col, (_, width) in enumerate(COLUMNS, start=1):
        ev.column_dimensions[get_column_letter(col)].width = width
    base = len(COLUMNS)
    for offset, width in enumerate((13, 76, 15, 12), start=1):
        ev.column_dimensions[get_column_letter(base + offset)].width = width
    ev.freeze_panes = "A2"

    valid = DataValidation(type="list", formula1='"y,n,?"', allow_blank=True)
    ev.add_data_validation(valid)

    for i, row in enumerate(frame.to_dict("records"), start=2):
        answer, reason = prefill(row, language)
        values = [
            i - 1, row.get("pr_key"), row.get("group"), row.get("agent"),
            str(row.get("title") or "")[:300], row.get("html_url"),
            row.get("files_counted"), row.get("lines_added"),
            row.get("detection_method"), row.get("parser_prediction"),
            counts_detail(row, language),
            str(row.get("body") or "")[:1500],
            str(row.get("patch_excerpt") or "")[:6000],
            answer, reason, None, None,
        ]
        for col, value in enumerate(values, start=1):
            cell = ev.cell(row=i, column=col, value=clean(value))
            cell.alignment = Alignment(vertical="top", wrap_text=col > 10)
        ev.cell(row=i, column=base + 1).fill = PREFILL_FILL
        ev.cell(row=i, column=base + 3).fill = BLANK_FILL
        valid.add(ev.cell(row=i, column=base + 1))
        valid.add(ev.cell(row=i, column=base + 3))
        t = get_column_letter(base + 1)
        g = get_column_letter(base + 3)
        ev.cell(row=i, column=base + 4,
                value=(f'=IF(OR(${t}{i}="",${g}{i}=""),"",'
                       f'IF(LOWER(${t}{i})=LOWER(${g}{i}),1,0))'))

    # ---- Metrics ------------------------------------------------------
    mt = wb.create_sheet("Metrics")
    last = len(frame) + 1
    pred = f"Evaluation!${get_column_letter(10)}$2:${get_column_letter(10)}${last}"
    mt.cell(row=1, column=1, value="Stage 1 parser performance").font = Font(bold=True)
    mt.cell(row=2, column=1,
            value="Positive class = PR genuinely involves construct work.")
    labels = ["TP", "FP", "TN", "FN", "Total", "Accuracy", "Precision",
              "Recall", "Specificity", "F1"]
    mt.cell(row=4, column=1, value="Metric").font = Font(bold=True)
    for col, name in enumerate(ANNOTATORS, start=2):
        mt.cell(row=4, column=col, value=name).font = Font(bold=True)
    for r, label in enumerate(labels, start=5):
        mt.cell(row=r, column=1, value=label)

    for col, annotator in enumerate(ANNOTATORS, start=2):
        letter = get_column_letter(base + (1 if col == 2 else 3))
        ans = f"Evaluation!${letter}$2:${letter}${last}"
        c = get_column_letter(col)
        mt.cell(row=5, column=col, value=(
            f'=COUNTIFS({pred},"construct_related",{ans},"y")'))
        mt.cell(row=6, column=col, value=(
            f'=COUNTIFS({pred},"construct_related",{ans},"n")'))
        mt.cell(row=7, column=col, value=(
            f'=COUNTIFS({pred},"not_construct_related",{ans},"n")'))
        mt.cell(row=8, column=col, value=(
            f'=COUNTIFS({pred},"not_construct_related",{ans},"y")'))
        mt.cell(row=9, column=col, value=f"=SUM({c}5:{c}8)")
        mt.cell(row=10, column=col, value=f"=IFERROR(({c}5+{c}7)/{c}9,\"\")")
        mt.cell(row=11, column=col, value=f"=IFERROR({c}5/({c}5+{c}6),\"\")")
        mt.cell(row=12, column=col, value=f"=IFERROR({c}5/({c}5+{c}8),\"\")")
        mt.cell(row=13, column=col, value=f"=IFERROR({c}7/({c}7+{c}6),\"\")")
        mt.cell(row=14, column=col, value=(
            f"=IFERROR(2*{c}11*{c}12/({c}11+{c}12),\"\")"))
        for r in range(10, 15):
            mt.cell(row=r, column=col).number_format = "0.0%"

    agree = get_column_letter(base + 4)
    mt.cell(row=16, column=1, value="Raw agreement (both filled)")
    mt.cell(row=16, column=2, value=(
        f'=IFERROR(AVERAGE(Evaluation!${agree}$2:${agree}${last}),"")'))
    mt.cell(row=16, column=2).number_format = "0.0%"
    mt.cell(row=17, column=1, value=(
        "Cohen's kappa is deliberately NOT computed: one column is pre-filled, "
        "so kappa would overstate independent agreement."))
    mt.column_dimensions["A"].width = 46
    for col in range(2, 2 + len(ANNOTATORS)):
        mt.column_dimensions[get_column_letter(col)].width = 15

    dest.parent.mkdir(parents=True, exist_ok=True)
    wb.save(dest)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--language", choices=list(LANGUAGES), action="append")
    args = ap.parse_args()

    for language in (args.language or list(LANGUAGES)):
        retained, rejected = build_population(language)
        frame = sample(retained, rejected)
        tag = {"TypeScript": "typescript", "C#": "csharp", "Rust": "rust"}[language]
        dest = OUTDIR / f"{tag}_regex_eval.xlsx"
        write_workbook(language, frame, dest)
        counts = frame.parser_prediction.value_counts().to_dict()
        print(f"[{language}] {len(frame)} PRs ({counts}) -> "
              f"{dest.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

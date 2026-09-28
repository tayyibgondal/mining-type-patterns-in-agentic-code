"""Build the annotation workbooks for both filtering stages.

    --stage regex   scores Stage 1: did the parser keep the right PRs?
                    population = everything Stage 1 saw
                    prediction  = retained / rejected

    --stage llm     scores Stage 2: did the LLM keep the right PRs?
                    population = the PRs Stage 1 RETAINED, which is the
                                 correct denominator for judging Stage 2 in
                                 isolation
                    prediction  = accepted / rejected by classifier AND
                                  validator

50 PRs per language per stage, 25 from each predicted class, fixed seed.

One design change from the first version of the regex workbook. Section 4.4.2
of the paper states that annotators labelled "without access to the pipeline's
verdict or rationale". The first sheet put `parser_prediction` right next to the
annotation column, which contradicts that claim and invites anchoring. Here the
prediction and the model's reasoning live on a separate `Predictions` sheet, so
the Evaluation sheet is blind by construction and the Metrics sheet still has
everything it needs to compute the confusion matrix.

The Tayyib column arrives pre-filled with reasoning. That is a starting point
to review, not an independent judgement. Every row carries a definite y or n;
there is no "unsure" option.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from catalogue.constructs import LANGUAGES, constructs_for  # noqa: E402
from catalogue.count import count_prepared  # noqa: E402
from catalogue.preprocess import prepare  # noqa: E402
from catalogue.retain import decide  # noqa: E402
from scripts.stage2_run import load_cache, majority_classifications  # noqa: E402

DATA = {
    "TypeScript": REPO / "datasets" / "typescript_data",
    "C#": REPO / "datasets" / "csharp_data",
    "Rust": REPO / "datasets" / "rust_data",
}
OUTDIR = REPO / "datasets" / "evaluation"
TAG = {"TypeScript": "typescript", "C#": "csharp", "Rust": "rust"}

SEED = 42
N_PER_CLASS = 25
ANNOTATORS = ("Tayyib", "Imgyeong")

_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(color="FFFFFF", bold=True)
PREFILL_FILL = PatternFill("solid", fgColor="FFF2CC")
BLANK_FILL = PatternFill("solid", fgColor="E2EFDA")


def clean(value, limit: int | None = None):
    if value is None or isinstance(value, (int, float, bool)):
        return value
    text = _ILLEGAL.sub(" ", _ANSI.sub("", str(value)))
    if limit is not None:
        text = text[:limit]
    return text[:32_000]


# --------------------------------------------------------------------------
# Populations
# --------------------------------------------------------------------------

def stage1_retained(language: str) -> pd.DataFrame:
    frames = []
    for group in ("agent", "human"):
        path = DATA[language] / f"stage1_{group}.parquet"
        if path.exists():
            frames.append(pd.read_parquet(path))
    return pd.concat(frames, ignore_index=True)


def regex_population(language: str) -> pd.DataFrame:
    """Retained PRs, plus rejected PRs recomputed from the source corpus."""
    kept = stage1_retained(language)
    kept["prediction"] = "keep"
    kept_keys = set(kept.pr_key)

    rejected = []
    human = DATA[language] / "human_corpus.parquet"
    if human.exists():
        pool = pd.read_parquet(human)
        pool = pool[~pool.pr_key.isin(kept_keys)]
        rng = random.Random(SEED)
        index = list(pool.index)
        rng.shuffle(index)
        for idx in index[:600]:
            row = pool.loc[idx].to_dict()
            prepared = prepare(row.get("patch_text"), language)
            counts = count_prepared(prepared, language)
            d = decide(prepared, counts, row.get("title"), row.get("body"),
                       language)
            if d.retained:
                continue
            row.update(counts)
            row.update(files_counted=prepared.files_counted,
                       lines_added=prepared.lines_added,
                       lines_removed=prepared.lines_removed,
                       detection_method="rejected", prediction="drop",
                       patch_excerpt=(row.get("patch_text") or "")[:6000])
            row.pop("patch_text", None)
            rejected.append(row)
            if len(rejected) >= 250:
                break
    return pd.concat([kept, pd.DataFrame(rejected)], ignore_index=True)


def llm_population(language: str) -> pd.DataFrame:
    """Stage-1 retained PRs, labelled with the Stage 2 decision and rationale."""
    frame = stage1_retained(language)
    majority = majority_classifications(language)
    vcache = load_cache("validate")
    verdicts = {}
    for rec in vcache.values():
        if rec.get("language") != language or not rec.get("payloads"):
            continue
        try:
            verdicts[rec["pr_key"]] = json.loads(rec["payloads"][0])
        except Exception:
            pass

    rows = []
    for row in frame.to_dict("records"):
        m = majority.get(row["pr_key"])
        if m is None:
            continue
        v = verdicts.get(row["pr_key"], {})
        accepted = bool(m["decision"]) and v.get("verdict") == "APPROVED"
        row.update(
            prediction="keep" if accepted else "drop",
            cls_decision=m["decision"],
            cls_confidence=float(m["payload"].get("confidence") or 0),
            cls_reasoning=m["payload"].get("reasoning") or "",
            cls_evidence="; ".join(m["payload"].get("evidence") or []),
            runs_agree=f"{m['n_true']}/{m['n_runs']} said yes",
            unanimous=bool(m["unanimous"]),
            val_verdict=v.get("verdict") or "MISSING",
            val_reasoning=v.get("reasoning") or "",
        )
        rows.append(row)
    return pd.DataFrame(rows)


def sample(frame: pd.DataFrame) -> pd.DataFrame:
    keep = frame[frame.prediction == "keep"]
    drop = frame[frame.prediction == "drop"]
    parts = [p.sample(n=min(N_PER_CLASS, len(p)), random_state=SEED)
             for p in (keep, drop) if len(p)]
    out = pd.concat(parts, ignore_index=True)
    order = list(out.index)
    random.Random(SEED).shuffle(order)
    return out.loc[order].reset_index(drop=True)


# --------------------------------------------------------------------------
# Pre-filled judgement (independent of the pipeline's verdict)
# --------------------------------------------------------------------------

def counts_detail(row, language: str) -> str:
    parts = []
    for c in constructs_for(language):
        a = int(row.get(c.add_col, 0) or 0)
        r = int(row.get(c.rem_col, 0) or 0)
        if a or r:
            parts.append(f"{c.display_name} [{c.id}] +{a}/-{r}")
    return "; ".join(parts) if parts else "no catalogue construct detected"


def prefill(row, language: str) -> tuple[str, str]:
    """A reasoned starting answer from the PR itself.

    Deliberately reads only the PR content and the parser's counts, never the
    pipeline's decision or rationale. Using those would make the evaluation
    circular.
    """
    escape = sum(int(row.get(c.add_col, 0) or 0) + int(row.get(c.rem_col, 0) or 0)
                 for c in constructs_for(language)
                 if c.family in ("escape", "suppression"))
    expressive = sum(int(row.get(c.add_col, 0) or 0)
                     for c in constructs_for(language)
                     if c.family in ("expressiveness", "safety"))
    files = int(row.get("files_counted", 0) or 0)
    title = str(row.get("title") or "")

    if files == 0:
        return "n", ("No hand-written source file of the target language was "
                     "changed, so there is no construct work to judge.")
    if escape > 0:
        return "y", (f"Escape-hatch or suppression constructs change in the "
                     f"diff, which is the core of RQ2. "
                     f"{counts_detail(row, language)}.")
    if expressive >= 3:
        return "y", (f"Several type-level constructs change across {files} "
                     f"file(s): {counts_detail(row, language)}. Read as "
                     f"genuine type work rather than incidental overlap.")
    if expressive == 0:
        return "n", (f"Touches {files} source file(s) but changes no catalogue "
                     f"construct. Title: \"{title[:110]}\". Reads as an "
                     f"unrelated change.")
    # Every row gets a definite call; there is no "unsure" option. One or two
    # expressiveness constructs and no escape hatch is treated as incidental,
    # because at that density the match is usually the ordinary syntax of a
    # change made for some other reason. Stated so a reviewer can disagree.
    return "n", (f"Only {expressive} expressiveness construct(s) and no escape "
                 f"hatch: {counts_detail(row, language)}. At this density the "
                 f"match reads as incidental to a change made for another "
                 f"reason rather than deliberate type work.")


# --------------------------------------------------------------------------
# Workbook
# --------------------------------------------------------------------------

# One layout for both stages, so the two workbooks are directly comparable.
BLIND_COLUMNS = [
    ("#", 5), ("pr_key", 34), ("group", 8), ("agent", 13),
    ("title", 46), ("html_url", 34),
    ("files", 7), ("lines_added", 8),
    ("construct_counts", 52), ("body_excerpt", 52), ("diff_excerpt", 80),
]


def write_workbook(language: str, stage: str, frame: pd.DataFrame,
                   dest: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Instructions"
    ws.cell(row=1, column=1, value=language).font = Font(bold=True, size=16)
    ws.cell(row=2, column=1,
            value=f"Stage: {'regex parser' if stage == 'regex' else 'LLM filter'}")
    ws.cell(row=3, column=1, value=(
        "Label in your own column, y or n only: y if the PR genuinely involves "
        f"{language} type-system or type-safety work, n if the type-like "
        "tokens are incidental. The pipeline's decision is on the Predictions "
        "sheet; do not read it before labelling."))
    ws.column_dimensions["A"].width = 110
    ws.cell(row=3, column=1).alignment = Alignment(wrap_text=True,
                                                   vertical="top")

    ev = wb.create_sheet("Evaluation")
    # The pipeline's decision is NOT on this sheet; it lives on Metrics as a
    # helper column, so annotators are not anchored by it.
    headers = [c for c, _ in BLIND_COLUMNS] + [
        "Tayyib (y/n)", "Tayyib_reasoning", "Imgyeong (y/n)",
        "Imgyeong_reasoning", "Agreement"]
    for col, name in enumerate(headers, start=1):
        cell = ev.cell(row=1, column=col, value=name)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for col, (_, width) in enumerate(BLIND_COLUMNS, start=1):
        ev.column_dimensions[get_column_letter(col)].width = width
    base = len(BLIND_COLUMNS)
    for offset, width in enumerate((13, 76, 15, 76, 12), start=1):
        ev.column_dimensions[get_column_letter(base + offset)].width = width
    ev.freeze_panes = "A2"

    valid = DataValidation(type="list", formula1='"y,n"', allow_blank=True)
    ev.add_data_validation(valid)

    records = frame.to_dict("records")
    for i, row in enumerate(records, start=2):
        answer, reason = prefill(row, language)
        values = [
            i - 1, row.get("pr_key"), row.get("group"), row.get("agent"),
            str(row.get("title") or "")[:300], row.get("html_url"),
            row.get("files_counted"), row.get("lines_added"),
            counts_detail(row, language),
            str(row.get("body") or "")[:1500],
            str(row.get("patch_excerpt") or "")[:6000],
            answer, reason, None, None, None,
        ]
        for col, value in enumerate(values, start=1):
            c = ev.cell(row=i, column=col, value=clean(value))
            c.alignment = Alignment(vertical="top", wrap_text=col > 8)
        ev.cell(row=i, column=base + 1).fill = PREFILL_FILL
        ev.cell(row=i, column=base + 3).fill = BLANK_FILL
        valid.add(ev.cell(row=i, column=base + 1))
        valid.add(ev.cell(row=i, column=base + 3))
        t, g = get_column_letter(base + 1), get_column_letter(base + 3)
        ev.cell(row=i, column=base + 4,
                value=(f'=IF(OR(${t}{i}="",${g}{i}=""),"",'
                       f'IF(LOWER(${t}{i})=LOWER(${g}{i}),1,0))'))

    # ---- Predictions, kept off the annotation sheet ------------------
    pr = wb.create_sheet("Predictions")
    if stage == "llm":
        pcols = ["#", "pr_key", "prediction", "runs_agree", "unanimous",
                 "cls_decision", "cls_confidence", "cls_reasoning",
                 "cls_evidence", "val_verdict", "val_reasoning"]
    else:
        pcols = ["#", "pr_key", "prediction", "detection_method",
                 "construct_total"]
    for col, name in enumerate(pcols, start=1):
        cell = pr.cell(row=1, column=col, value=name)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
    for i, row in enumerate(records, start=2):
        for col, name in enumerate(pcols, start=1):
            v = (i - 1) if name == "#" else row.get(name)
            pr.cell(row=i, column=col, value=clean(v))
    for col, width in enumerate((5, 34, 12, 16, 11, 13, 13, 70, 70, 13, 70),
                                start=1):
        if col <= len(pcols):
            pr.column_dimensions[get_column_letter(col)].width = width

    # ---- Metrics -----------------------------------------------------
    mt = wb.create_sheet("Metrics")
    last = len(records) + 1
    pred = f"Predictions!$C$2:$C${last}"
    label = "regex parser" if stage == "regex" else "LLM filter"
    mt.cell(row=1, column=1,
            value=f"{label} performance - {language}").font = Font(bold=True)
    mt.cell(row=2, column=1, value=(
        "Positive class = PR genuinely involves construct work. "
        "Prediction 'keep' = the stage retained it."))
    rows = ["TP", "FP", "TN", "FN", "Total", "Accuracy", "Precision",
            "Recall", "Specificity", "F1"]
    mt.cell(row=4, column=1, value="Metric").font = Font(bold=True)
    for col, name in enumerate(ANNOTATORS, start=2):
        mt.cell(row=4, column=col, value=name).font = Font(bold=True)
    for r, name in enumerate(rows, start=5):
        mt.cell(row=r, column=1, value=name)
    for col, _ in enumerate(ANNOTATORS, start=2):
        letter = get_column_letter(base + (1 if col == 2 else 3))
        ans = f"Evaluation!${letter}$2:${letter}${last}"
        c = get_column_letter(col)
        mt.cell(row=5, column=col, value=f'=COUNTIFS({pred},"keep",{ans},"y")')
        mt.cell(row=6, column=col, value=f'=COUNTIFS({pred},"keep",{ans},"n")')
        mt.cell(row=7, column=col, value=f'=COUNTIFS({pred},"drop",{ans},"n")')
        mt.cell(row=8, column=col, value=f'=COUNTIFS({pred},"drop",{ans},"y")')
        mt.cell(row=9, column=col, value=f"=SUM({c}5:{c}8)")
        mt.cell(row=10, column=col, value=f'=IFERROR(({c}5+{c}7)/{c}9,"")')
        mt.cell(row=11, column=col, value=f'=IFERROR({c}5/({c}5+{c}6),"")')
        mt.cell(row=12, column=col, value=f'=IFERROR({c}5/({c}5+{c}8),"")')
        mt.cell(row=13, column=col, value=f'=IFERROR({c}7/({c}7+{c}6),"")')
        mt.cell(row=14, column=col,
                value=f'=IFERROR(2*{c}11*{c}12/({c}11+{c}12),"")')
        for r in range(10, 15):
            mt.cell(row=r, column=col).number_format = "0.0%"
    agree = get_column_letter(base + 4)
    mt.cell(row=16, column=1, value="Raw agreement (both filled)")
    mt.cell(row=16, column=2,
            value=f'=IFERROR(AVERAGE(Evaluation!${agree}$2:${agree}${last}),"")')
    mt.cell(row=16, column=2).number_format = "0.0%"
    mt.column_dimensions["A"].width = 46

    dest.parent.mkdir(parents=True, exist_ok=True)
    wb.save(dest)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=["regex", "llm"], action="append")
    ap.add_argument("--language", choices=list(LANGUAGES), action="append")
    args = ap.parse_args()

    for stage in (args.stage or ["regex", "llm"]):
        builder = regex_population if stage == "regex" else llm_population
        for language in (args.language or list(LANGUAGES)):
            frame = sample(builder(language))
            dest = OUTDIR / f"{TAG[language]}_{stage}_eval.xlsx"
            write_workbook(language, stage, frame, dest)
            counts = frame.prediction.value_counts().to_dict()
            print(f"[{stage}/{language}] {len(frame)} PRs {counts} -> "
                  f"{dest.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

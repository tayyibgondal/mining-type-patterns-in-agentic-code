"""Stage 2: multi-agent LLM filtering, rebuilt.

Replaces `llm_type_classifier.py`, `llm_type_classifier_csharp.py` and
`llm_type_classifier_rust.py`. Three near-identical 700-line files is how the
C# prompt acquired a `BE LINIENT AND MOSTLY SAY YES` instruction that the other
two lacked, and how Rust came to be classified by Gemini while the other two
used GPT-4o-mini.

What is fixed relative to the old pipeline:

  * one model for all three languages, so no cross-language model confound;
  * one prompt template, with the construct definition generated from
    `catalogue.constructs`, so the filter and the counters cannot describe
    different things and no per-language leniency drift is possible;
  * structured outputs with a json_schema, so a malformed response is
    impossible rather than an unguarded `json.loads` crash;
  * three runs per PR with a majority vote, and the per-run verdicts persisted
    so run-to-run agreement can be reported;
  * retries, a resumable cache, and a timeout path that retries instead of
    silently becoming a negative.

Note on determinism: gpt-5.6-luna rejects `temperature` (see
`scripts/probe_model.py`), so sampling cannot be pinned low the way the old
pipeline pinned it to 0.1. `seed` is accepted but is best-effort. This is why
the three-run majority vote is load-bearing here rather than a nicety.

Architecture, unchanged from the paper because it is sound: a classifier agent
decides, a validator agent audits the decision without re-reading the diff.
Acceptance is conjunctive, Accept(p) = Retain(p) and Cls(p) and Val(p), and an
UNCERTAIN verdict counts as a rejection.

Usage:
    python3 llm_stage2.py prepare --runs 3
    python3 llm_stage2.py submit --stage classify
    python3 llm_stage2.py poll
    python3 llm_stage2.py collect --stage classify
    python3 llm_stage2.py prepare --stage validate --runs 3
    python3 llm_stage2.py submit --stage validate
    python3 llm_stage2.py collect --stage validate
    python3 llm_stage2.py finalize
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalogue.constructs import LANGUAGES, by_family, constructs_for  # noqa: E402

REPO = Path(__file__).resolve().parent
CACHE = REPO / "datasets" / "llm_cache"
STATE = CACHE / "batches.json"
MODEL = "gpt-4o-mini"   # cheapest per PR in practice; see docs/paper_updates.md

DATA_DIR = {
    "TypeScript": REPO / "datasets" / "typescript_data",
    "C#": REPO / "datasets" / "csharp_data",
    "Rust": REPO / "datasets" / "rust_data",
}

# Two independent limits bind here.
#   * Per file: 50,000 requests and 200 MB.
#   * Per organisation: 5,000,000 *enqueued* tokens for this model, counting
#     input plus reserved output (max_completion_tokens x n). A single
#     36,929-request submission is roughly ten times that and is rejected
#     outright with token_limit_exceeded.
# So batches are drip-fed: one chunk at a time, the next submitted only once
# the previous has completed. At ~1,430 input tokens and 3 x 700 reserved
# output per request, ~3,530 tokens each, 1,200 requests sits near 4.2M.
MAX_REQUESTS_PER_FILE = 1_200
MAX_COMPLETION_TOKENS = 700

TITLE_CHARS, BODY_CHARS, PATCH_CHARS = 500, 1200, 2500


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

CLASSIFIER_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "construct_classification",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "is_construct_related": {"type": "boolean"},
                "confidence": {"type": "number"},
                "reasoning": {"type": "string"},
                "evidence": {"type": "array", "items": {"type": "string"}},
                "channels": {
                    "type": "array",
                    "items": {"type": "string",
                              "enum": ["title", "body", "patch"]},
                },
            },
            "required": ["is_construct_related", "confidence", "reasoning",
                         "evidence", "channels"],
            "additionalProperties": False,
        },
    },
}

VALIDATOR_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "classification_validation",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string",
                            "enum": ["APPROVED", "REJECTED", "UNCERTAIN"]},
                "confidence": {"type": "number"},
                "reasoning": {"type": "string"},
            },
            "required": ["verdict", "confidence", "reasoning"],
            "additionalProperties": False,
        },
    },
}


# --------------------------------------------------------------------------
# Prompts, generated from the catalogue
# --------------------------------------------------------------------------

def construct_definition(language: str) -> str:
    """The operational definition, derived from the catalogue itself.

    Generating this means the prompt and the parser answer the same question
    about the same constructs. The old prompts were hand-written per language
    and drifted apart.
    """
    lines = []
    for family, heading in (
        ("escape", "Escape hatches (waive or relocate a compile-time guarantee)"),
        ("suppression", "Suppression directives (silence the checker)"),
        ("safety", "Safety-enhancing constructs (restore a guarantee)"),
        ("expressiveness", "Expressiveness constructs (declare or refine types)"),
    ):
        items = by_family(language, family)
        if not items:
            continue
        names = ", ".join(c.display_name for c in items)
        lines.append(f"- {heading}: {names}.")
    return "\n".join(lines)


def _clip(value, limit: int) -> str:
    text = "" if value is None else str(value)
    return text[:limit]


def _counts_summary(row, language: str, top: int = 12) -> str:
    pairs = []
    for c in constructs_for(language):
        added = int(row.get(c.add_col, 0) or 0)
        removed = int(row.get(c.rem_col, 0) or 0)
        if added or removed:
            pairs.append((added + removed, f"{c.display_name} +{added}/-{removed}"))
    pairs.sort(reverse=True)
    if not pairs:
        return "none detected by the parser"
    return "; ".join(text for _, text in pairs[:top])


def classifier_messages(row, language: str) -> list[dict]:
    system = (f"You are an expert {language} software engineering analyst. "
              "Answer only with JSON matching the provided schema.")
    user = f"""Decide whether this pull request involves {language} type-system
or type-safety work.

## Definition
A PR is CONSTRUCT-RELATED if it adds, removes, or meaningfully changes any of
the following in hand-written {language} source:

{construct_definition(language)}

It is NOT construct-related if the type-like tokens are incidental: a rename, a
dependency bump, generated code, formatting, or a change where a construct
merely appears in a line that was touched for an unrelated reason.

## Pull request
Title: {_clip(row.get('title'), TITLE_CHARS)}

Description: {_clip(row.get('body'), BODY_CHARS)}

Changed {language} files: {row.get('files_counted', 0)}
Lines added/removed in those files: +{row.get('lines_added', 0)}/-{row.get('lines_removed', 0)}

Parser-detected construct changes: {_counts_summary(row, language)}

Diff excerpt:
{_clip(row.get('patch_excerpt'), PATCH_CHARS)}

## Instructions
Judge intent, not token presence. The parser counts are a hint, not an answer;
a PR can match many patterns incidentally and still not be construct-related.
Quote concrete evidence from the input for your decision, and name which
channels (title, body, patch) carried it. Classify as construct-related only
when the evidence is clear."""
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]


def validator_messages(row, classification: dict, language: str) -> list[dict]:
    system = (f"You are a senior {language} reviewer auditing another agent's "
              "classification. Answer only with JSON matching the schema.")
    decision = ("CONSTRUCT-RELATED" if classification.get("is_construct_related")
                else "NOT CONSTRUCT-RELATED")
    evidence = "; ".join(classification.get("evidence") or [])[:800]
    user = f"""Audit this classification. You are given the classifier's stated
reasoning and evidence, not the diff. Your job is to judge whether the
justification supports the decision, not to re-derive it.

## Pull request
Title: {_clip(row.get('title'), 250)}
Description: {_clip(row.get('body'), 600)}
Changed {language} files: {row.get('files_counted', 0)}
Lines added/removed: +{row.get('lines_added', 0)}/-{row.get('lines_removed', 0)}

## Classifier decision
Decision: {decision}
Confidence: {float(classification.get('confidence') or 0):.2f}
Reasoning: {_clip(classification.get('reasoning'), 800)}
Evidence: {evidence}
Channels cited: {', '.join(classification.get('channels') or []) or 'none'}

## Questions
1. Does the stated evidence actually support the decision?
2. Is this a false positive, where type-like tokens are incidental?
3. Is this a false negative, where real type work was missed?
4. Is the confidence appropriate given the strength of the evidence?

Return APPROVED only if the decision is well supported. Return REJECTED if it is
not. Return UNCERTAIN if the justification is too thin to judge; UNCERTAIN is
treated as a rejection downstream, so use it when you genuinely cannot tell."""
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]


# --------------------------------------------------------------------------
# Batch request construction
# --------------------------------------------------------------------------

def load_capabilities() -> dict:
    path = CACHE / "model_capabilities.json"
    if not path.exists():
        raise SystemExit(
            "Run scripts/probe_model.py first: Stage 2 needs to know which "
            "request parameters this model accepts.")
    return json.loads(path.read_text())


def request_body(messages: list[dict], schema: dict, run: int,
                 caps: dict, n: int = 1) -> dict:
    body = {"model": caps.get("model", MODEL), "messages": messages}
    if n > 1:
        # The three runs differ only by sampling, so one request with n=3
        # bills the prompt once instead of three times. Same independent
        # samples, a third of the input cost.
        body["n"] = n
    if caps.get("json_schema"):
        body["response_format"] = schema
    elif caps.get("json_object"):
        body["response_format"] = {"type": "json_object"}
    if caps.get("temperature"):
        body["temperature"] = 0.1
    if caps.get("seed"):
        # Distinct per run: the point of three runs is to observe variation,
        # not to request the same sample three times.
        body["seed"] = 1000 + run
    if caps.get("max_completion_tokens"):
        body["max_completion_tokens"] = MAX_COMPLETION_TOKENS
    return body


def custom_id(stage: str, language: str, run: int, pr_key: str) -> str:
    # Batch custom_id must be unique and round-trip to (stage, lang, run, PR).
    lang_tag = {"TypeScript": "ts", "C#": "cs", "Rust": "rs"}[language]
    return f"{stage}|{lang_tag}|{run}|{pr_key}"


def parse_custom_id(cid: str) -> tuple[str, str, int, str]:
    stage, lang_tag, run, pr_key = cid.split("|", 3)
    language = {"ts": "TypeScript", "cs": "C#", "rs": "Rust"}[lang_tag]
    return stage, language, int(run), pr_key


def stage1_frame(language: str) -> pd.DataFrame:
    frames = []
    for group in ("agent", "human"):
        path = DATA_DIR[language] / f"stage1_{group}.parquet"
        if path.exists():
            frames.append(pd.read_parquet(path))
    if not frames:
        raise FileNotFoundError(
            f"no stage1 parquet for {language}; run scripts/stage1_extract.py")
    frame = pd.concat(frames, ignore_index=True)
    assert len(frame) == frame.pr_key.nunique(), f"{language}: pr_key not unique"
    return frame


def cmd_prepare(args) -> int:
    caps = load_capabilities()
    CACHE.mkdir(parents=True, exist_ok=True)
    outdir = CACHE / "requests"
    outdir.mkdir(exist_ok=True)

    classifications = {}
    if args.stage == "validate":
        path = CACHE / "classify_results.parquet"
        if not path.exists():
            raise SystemExit("collect the classify stage before preparing "
                             "validate")
        cls = pd.read_parquet(path)
        for rec in cls.to_dict("records"):
            classifications[(rec["language"], rec["run"], rec["pr_key"])] = rec

    requests, total = [], 0
    for language in (args.language or list(LANGUAGES)):
        frame = stage1_frame(language)
        if args.limit:
            frame = frame.head(args.limit)
        if args.stage == "classify":
            for row in frame.to_dict("records"):
                body = request_body(classifier_messages(row, language),
                                    CLASSIFIER_SCHEMA, 1, caps, n=args.runs)
                requests.append({
                    "custom_id": custom_id("classify", language, 0,
                                           row["pr_key"]),
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": body,
                })
                total += 1
        else:
            for run in range(1, args.runs + 1):
                for row in frame.to_dict("records"):
                    prior = classifications.get(
                        (language, run, row["pr_key"]))
                    if prior is None:
                        continue
                    body = request_body(
                        validator_messages(row, json.loads(prior["payload"]),
                                           language),
                        VALIDATOR_SCHEMA, run, caps)
                    requests.append({
                        "custom_id": custom_id("validate", language, run,
                                               row["pr_key"]),
                        "method": "POST",
                        "url": "/v1/chat/completions",
                        "body": body,
                    })
                    total += 1

    written = []
    for index in range(0, len(requests), MAX_REQUESTS_PER_FILE):
        chunk = requests[index:index + MAX_REQUESTS_PER_FILE]
        path = outdir / f"{args.stage}_{index // MAX_REQUESTS_PER_FILE:03d}.jsonl"
        with path.open("w") as fh:
            for req in chunk:
                fh.write(json.dumps(req) + "\n")
        written.append(path)
        print(f"  wrote {path.relative_to(REPO)}  {len(chunk):,} requests  "
              f"{path.stat().st_size / 1e6:.1f} MB")

    approx_in = sum(len(json.dumps(r["body"])) for r in requests[:200])
    per_req = approx_in / max(min(len(requests), 200), 1) / 4
    est = (total * per_req / 1e6 * 0.20) + (total * 400 / 1e6 * 1.20)
    print(f"\n{args.stage}: {total:,} requests in {len(written)} file(s)")
    print(f"estimated cost ~${est:,.0f} standard, ~${est / 2:,.0f} on Batch")
    return 0


def _client():
    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv(REPO / ".env")
    return OpenAI()


def _state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"batches": []}


def _save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))


def cmd_submit(args) -> int:
    client = _client()
    state = _state()
    done = {b["file"] for b in state["batches"]}
    for path in sorted((CACHE / "requests").glob(f"{args.stage}_*.jsonl")):
        if path.name in done and not args.force:
            print(f"  [skip] {path.name} already submitted")
            continue
        with path.open("rb") as fh:
            uploaded = client.files.create(file=fh, purpose="batch")
        batch = client.batches.create(
            input_file_id=uploaded.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={"stage": args.stage, "file": path.name})
        state["batches"].append({"file": path.name, "stage": args.stage,
                                 "batch_id": batch.id, "status": batch.status})
        print(f"  [sent] {path.name} -> {batch.id}")
        _save_state(state)
    return 0


def cmd_poll(args) -> int:
    client = _client()
    state = _state()
    counts: dict[str, int] = {}
    for entry in state["batches"]:
        batch = client.batches.retrieve(entry["batch_id"])
        entry["status"] = batch.status
        entry["output_file_id"] = getattr(batch, "output_file_id", None)
        rc = getattr(batch, "request_counts", None)
        done = getattr(rc, "completed", 0) if rc else 0
        total = getattr(rc, "total", 0) if rc else 0
        failed = getattr(rc, "failed", 0) if rc else 0
        counts[batch.status] = counts.get(batch.status, 0) + 1
        print(f"  {entry['file']:<22}{batch.status:<12}"
              f"{done:,}/{total:,} done, {failed:,} failed")
    _save_state(state)
    print(f"\n{counts}")
    return 0


def cmd_collect(args) -> int:
    client = _client()
    state = _state()
    rows = []
    for entry in state["batches"]:
        if entry.get("stage") != args.stage:
            continue
        batch = client.batches.retrieve(entry["batch_id"])
        if batch.status != "completed":
            print(f"  [wait] {entry['file']} is {batch.status}")
            continue
        content = client.files.content(batch.output_file_id).text
        for line in content.splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            stage, language, run, pr_key = parse_custom_id(item["custom_id"])
            response = item.get("response") or {}
            if response.get("status_code") != 200:
                continue
            choices = response["body"]["choices"]
            if stage == "classify":
                # n=runs, so each choice is one independent run.
                for index, choice in enumerate(choices, start=1):
                    rows.append({"pr_key": pr_key, "language": language,
                                 "run": index,
                                 "payload": choice["message"]["content"]})
            else:
                rows.append({"pr_key": pr_key, "language": language, "run": run,
                             "payload": choices[0]["message"]["content"]})
        print(f"  [read] {entry['file']}")
    if not rows:
        print("nothing collected")
        return 1
    frame = pd.DataFrame(rows)
    dest = CACHE / f"{args.stage}_results.parquet"
    frame.to_parquet(dest, index=False, compression="zstd")
    print(f"\ncollected {len(frame):,} results -> {dest.relative_to(REPO)}")
    return 0


def cmd_drip(args) -> int:
    """Submit request files one at a time, respecting the enqueued-token cap.

    The organisation limit is on tokens enqueued at once, not on total spend,
    so the whole corpus goes through by keeping at most one batch in flight.
    Progress is written to the state file after every step, so an interrupted
    run resumes without re-submitting or re-paying for completed chunks.
    """
    import time

    client = _client()
    files = sorted((CACHE / "requests").glob(f"{args.stage}_*.jsonl"))
    if not files:
        raise SystemExit(f"no prepared {args.stage} request files")

    state = _state()
    by_file = {b["file"]: b for b in state["batches"]}
    collected = 0

    for index, path in enumerate(files, start=1):
        entry = by_file.get(path.name)
        if entry and entry.get("status") == "completed":
            print(f"[{index}/{len(files)}] {path.name} already completed")
            continue

        if entry and entry.get("status") in ("failed", "expired", "cancelled"):
            print(f"[{index}/{len(files)}] {path.name} previously "
                  f"{entry['status']}, resubmitting")
            entry = None

        if entry is None:
            with path.open("rb") as fh:
                uploaded = client.files.create(file=fh, purpose="batch")
            batch = client.batches.create(
                input_file_id=uploaded.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={"stage": args.stage, "file": path.name})
            entry = {"file": path.name, "stage": args.stage,
                     "batch_id": batch.id, "status": batch.status}
            state["batches"] = [b for b in state["batches"]
                                if b["file"] != path.name] + [entry]
            _save_state(state)
            print(f"[{index}/{len(files)}] submitted {path.name} -> "
                  f"{batch.id}")

        while True:
            batch = client.batches.retrieve(entry["batch_id"])
            entry["status"] = batch.status
            entry["output_file_id"] = getattr(batch, "output_file_id", None)
            _save_state(state)
            if batch.status in ("completed", "failed", "expired", "cancelled"):
                break
            counts = getattr(batch, "request_counts", None)
            done = getattr(counts, "completed", 0) if counts else 0
            total = getattr(counts, "total", 0) if counts else 0
            print(f"    {batch.status} {done:,}/{total:,}", flush=True)
            time.sleep(args.interval)

        if batch.status != "completed":
            detail = ""
            if getattr(batch, "errors", None):
                data = getattr(batch.errors, "data", None) or []
                if data:
                    detail = getattr(data[0], "message", "")[:160]
            print(f"    {path.name} {batch.status}. {detail}")
            if args.stop_on_failure:
                return 1
            continue

        collected += 1
        print(f"    {path.name} completed")

    print(f"\n{collected} chunk(s) completed this pass. "
          f"Run `collect --stage {args.stage}` to merge results.")
    return 0


def cmd_finalize(args) -> int:
    """Majority vote across runs, then write the Stage 2 corpus."""
    cls = pd.read_parquet(CACHE / "classify_results.parquet")
    val = pd.read_parquet(CACHE / "validate_results.parquet")

    cls["cls"] = cls.payload.apply(
        lambda p: bool(json.loads(p).get("is_construct_related")))
    val["verdict"] = val.payload.apply(
        lambda p: json.loads(p).get("verdict"))
    val["val"] = val.verdict == "APPROVED"

    merged = cls.merge(val[["pr_key", "language", "run", "val", "verdict"]],
                       on=["pr_key", "language", "run"], how="left")
    merged["val"] = merged["val"].fillna(False)
    # Accept(p) = Retain(p) and Cls(p) and Val(p); UNCERTAIN is a rejection.
    merged["accept"] = merged.cls & merged.val

    votes = merged.groupby(["language", "pr_key"]).agg(
        n_runs=("accept", "size"),
        n_accept=("accept", "sum")).reset_index()
    votes["final_is_type_related"] = votes.n_accept * 2 > votes.n_runs
    votes["unanimous"] = votes.n_accept.isin([0]) | (
        votes.n_accept == votes.n_runs)

    for language in votes.language.unique():
        sub = votes[votes.language == language]
        frame = stage1_frame(language).merge(
            sub.drop(columns="language"), on="pr_key", how="inner")
        kept = frame[frame.final_is_type_related]
        dest = DATA_DIR[language] / "stage2_corpus.parquet"
        kept.to_parquet(dest, index=False, compression="zstd")
        agree = 100 * sub.unanimous.mean()
        print(f"[{language}] {len(sub):,} judged -> {len(kept):,} accepted "
              f"({100 * len(kept) / max(len(sub), 1):.1f}%), "
              f"{agree:.1f}% unanimous across runs")
        print(f"    -> {dest.relative_to(REPO)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare")
    p.add_argument("--stage", choices=["classify", "validate"],
                   default="classify")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--language", choices=list(LANGUAGES), action="append")
    p.add_argument("--limit", type=int, default=None)
    p.set_defaults(func=cmd_prepare)

    p = sub.add_parser("submit")
    p.add_argument("--stage", choices=["classify", "validate"], required=True)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("poll")
    p.set_defaults(func=cmd_poll)

    p = sub.add_parser("drip")
    p.add_argument("--stage", choices=["classify", "validate"], required=True)
    p.add_argument("--interval", type=int, default=60,
                   help="seconds between status checks")
    p.add_argument("--stop-on-failure", action="store_true")
    p.set_defaults(func=cmd_drip)

    p = sub.add_parser("collect")
    p.add_argument("--stage", choices=["classify", "validate"], required=True)
    p.set_defaults(func=cmd_collect)

    p = sub.add_parser("finalize")
    p.set_defaults(func=cmd_finalize)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

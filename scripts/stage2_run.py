"""Stage 2 over the standard API: concurrent, cached, resumable.

The Batch API path in `llm_stage2.py` works but this organisation is capped at
5,000,000 enqueued tokens for this model, so the corpus has to be drip-fed in
31 chunks at roughly 35 requests a minute. That projects to about 71 hours. The
standard API at 50 concurrent finishes the same work in about two hours for
roughly double the money, which is the trade taken here.

Design, in the order the old pipeline got each of these wrong:

  * **Cache first.** Every response is appended to a JSONL cache keyed by
    (stage, pr_key, run, model, prompt hash). A killed run resumes free. The
    old classifiers had no cache: a crash at 90% re-billed the whole corpus.
  * **Retries with backoff.** The old code had none, and a single transport
    error became a permanent negative for that PR.
  * **Timeouts are errors, not negatives.** The old code returned a synthetic
    `is_type_related: False` on timeout *without* setting the error flag, so a
    timed-out call was indistinguishable from a genuine rejection.
  * **Three classifier samples in one request** via `n=3`, so the prompt is
    billed once rather than three times.
  * **The validator audits the majority decision once**, rather than once per
    run. The stochasticity measurement is about the classification; auditing
    the stable decision is both cheaper and arguably the more sensible check.

Usage:
    python3 scripts/stage2_run.py --stage classify
    python3 scripts/stage2_run.py --stage validate
    python3 scripts/stage2_run.py --stage classify --language Rust --limit 50
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import AsyncOpenAI

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import llm_stage2 as S  # noqa: E402
from catalogue.constructs import LANGUAGES  # noqa: E402

CACHE_DIR = REPO / "datasets" / "llm_cache"

# USD per million tokens, (input, output). The live cost display had the
# previous model's prices hardcoded and over-reported spend by ~50%.
PRICING = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-5-nano": (0.05, 0.40),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5.6-luna": (0.20, 1.20),
    "gpt-5.6-terra": (2.00, 12.00),
    "gpt-5.6-sol": (5.00, 30.00),
}


def price_for(model: str) -> tuple[float, float]:
    return PRICING.get(model, (0.15, 0.60))


def prompt_hash(messages: list[dict]) -> str:
    blob = json.dumps(messages, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def cache_path(stage: str) -> Path:
    return CACHE_DIR / f"{stage}_cache.jsonl"


def load_cache(stage: str) -> dict[str, dict]:
    path = cache_path(stage)
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue          # truncated final line from a hard kill
            # A later success supersedes an earlier failure for the same key.
            existing = out.get(rec["key"])
            if existing is None or (not existing.get("payloads")
                                    and rec.get("payloads")):
                out[rec["key"]] = rec
    return out


def completed_keys(stage: str) -> set[str]:
    """Only responses that actually carry payloads count as done.

    Failures are cached too, so that a run can report them, but they must be
    retried on the next pass rather than skipped as if they had succeeded.
    """
    return {k for k, v in load_cache(stage).items() if v.get("payloads")}


class OutOfCredits(RuntimeError):
    """Billing is exhausted. Retrying cannot help, so stop the whole run."""


class TokenBucket:
    """Self-throttle to a tokens-per-minute budget.

    The organisation enforces a TPM cap, and 50 concurrent requests at roughly
    2,500 tokens each blew straight through it: 38% of the first pass came back
    429. Reserving budget before each call keeps the run under the cap instead
    of discovering it one rejection at a time.
    """

    def __init__(self, tokens_per_minute: int):
        self.capacity = tokens_per_minute
        self.tokens = float(tokens_per_minute)
        self.updated = time.monotonic()
        self.lock = asyncio.Lock()

    async def take(self, amount: int) -> None:
        amount = min(amount, self.capacity)
        while True:
            async with self.lock:
                now = time.monotonic()
                self.tokens = min(
                    self.capacity,
                    self.tokens + (now - self.updated) * self.capacity / 60.0)
                self.updated = now
                if self.tokens >= amount:
                    self.tokens -= amount
                    return
                deficit = amount - self.tokens
                wait = deficit * 60.0 / self.capacity
            await asyncio.sleep(min(wait, 5.0))


_RETRY_AFTER = re.compile(r"try again in ([0-9.]+)(ms|s)", re.IGNORECASE)


def retry_delay(message: str, attempt: int) -> float:
    """Honour the server's own advice when it gives one."""
    match = _RETRY_AFTER.search(message)
    if match:
        value = float(match.group(1))
        seconds = value / 1000.0 if match.group(2).lower() == "ms" else value
        return min(max(seconds, 0.5), 60.0)
    return min(2 ** attempt, 30.0) + random.uniform(0, 1.5)


class Runner:
    def __init__(self, stage: str, concurrency: int, model: str,
                 caps: dict, retries: int = 8, timeout: float = 120.0,
                 tpm: int = 200_000, est_tokens: int = 2_600):
        self.stage = stage
        self.client = AsyncOpenAI(timeout=timeout, max_retries=0)
        self.sem = asyncio.Semaphore(concurrency)
        self.caps = caps
        self.model = model
        self.retries = retries
        self.bucket = TokenBucket(tpm)
        self.est_tokens = est_tokens
        self.lock = asyncio.Lock()
        self.aborted = False
        self.handle = cache_path(stage).open("a")
        self.done = 0
        self.errors = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.started = time.time()
        self.total = 0

    async def close(self) -> None:
        self.handle.close()

    async def call(self, key: str, meta: dict, body: dict) -> None:
        if self.aborted:
            return
        async with self.sem:
            last = ""
            for attempt in range(self.retries):
                if self.aborted:
                    return
                await self.bucket.take(self.est_tokens)
                try:
                    response = await self.client.chat.completions.create(**body)
                    payloads = [c.message.content for c in response.choices]
                    record = {"key": key, **meta,
                              "payloads": payloads,
                              "prompt_tokens": response.usage.prompt_tokens,
                              "completion_tokens": response.usage.completion_tokens}
                    async with self.lock:
                        self.handle.write(json.dumps(record) + "\n")
                        self.handle.flush()
                        self.done += 1
                        self.tokens_in += response.usage.prompt_tokens
                        self.tokens_out += response.usage.completion_tokens
                        self._progress()
                    return
                except Exception as exc:                    # noqa: BLE001
                    text = str(exc)
                    last = f"{type(exc).__name__}: {text}"[:200]
                    if "no credits remaining" in text.lower() or \
                            "billing_hard_limit" in text.lower():
                        # Retrying cannot conjure credit. Stop the run so the
                        # cache keeps what was paid for and nothing is wasted.
                        self.aborted = True
                        raise OutOfCredits(text[:200]) from exc
                    # Timeouts and rate limits are retried, never silently
                    # converted into a negative classification.
                    await asyncio.sleep(retry_delay(text, attempt))
            async with self.lock:
                self.errors += 1
                self.handle.write(json.dumps(
                    {"key": key, **meta, "payloads": None,
                     "error": last}) + "\n")
                self.handle.flush()
                self._progress()

    def _progress(self) -> None:
        total = self.done + self.errors
        if total % 250 and total != self.total:
            return
        elapsed = max(time.time() - self.started, 1e-6)
        rate = total / elapsed
        remaining = (self.total - total) / rate if rate > 0 else 0
        pin, pout = price_for(self.model)
        cost = (self.tokens_in / 1e6 * pin) + (self.tokens_out / 1e6 * pout)
        print(f"  {total:,}/{self.total:,}  {rate * 60:,.0f}/min  "
              f"errors {self.errors}  ${cost:,.2f}  "
              f"eta {remaining / 60:,.0f} min", flush=True)


def classify_jobs(language: str, limit: int | None, caps: dict,
                  runs: int) -> list[tuple[str, dict, dict]]:
    frame = S.stage1_frame(language)
    if limit:
        frame = frame.head(limit)
    jobs = []
    for row in frame.to_dict("records"):
        messages = S.classifier_messages(row, language)
        body = S.request_body(messages, S.CLASSIFIER_SCHEMA, 1, caps, n=runs)
        key = (f"classify|{caps.get('model', S.MODEL)}|{language}|"
               f"{row['pr_key']}|{prompt_hash(messages)}")
        jobs.append((key, {"pr_key": row["pr_key"], "language": language},
                     body))
    return jobs


def majority_classifications(language: str) -> dict[str, dict]:
    """Majority vote over the n classifier samples, per PR."""
    cache = load_cache("classify")
    out: dict[str, dict] = {}
    for rec in cache.values():
        if rec.get("language") != language or not rec.get("payloads"):
            continue
        parsed = []
        for payload in rec["payloads"]:
            try:
                parsed.append(json.loads(payload))
            except (json.JSONDecodeError, TypeError):
                continue
        if not parsed:
            continue
        votes = [bool(p.get("is_construct_related")) for p in parsed]
        decision = sum(votes) * 2 > len(votes)
        # Keep a sample that agrees with the majority, so the validator audits
        # reasoning that actually supports the decision it is given.
        chosen = next((p for p, v in zip(parsed, votes) if v == decision),
                      parsed[0])
        out[rec["pr_key"]] = {
            "decision": decision, "payload": chosen,
            "n_runs": len(votes), "n_true": sum(votes),
            "unanimous": len(set(votes)) == 1,
        }
    return out


def validate_jobs(language: str, limit: int | None,
                  caps: dict) -> list[tuple[str, dict, dict]]:
    majority = majority_classifications(language)
    if not majority:
        raise SystemExit(f"no classify results cached for {language}")
    frame = S.stage1_frame(language)
    if limit:
        frame = frame.head(limit)
    jobs = []
    for row in frame.to_dict("records"):
        found = majority.get(row["pr_key"])
        if found is None:
            continue
        messages = S.validator_messages(row, found["payload"], language)
        body = S.request_body(messages, S.VALIDATOR_SCHEMA, 1, caps)
        key = (f"validate|{caps.get('model', S.MODEL)}|{language}|"
               f"{row['pr_key']}|{prompt_hash(messages)}")
        jobs.append((key, {"pr_key": row["pr_key"], "language": language},
                     body))
    return jobs


async def run_stage(stage: str, languages: list[str], limit: int | None,
                    concurrency: int, runs: int, tpm: int) -> None:
    caps = S.load_capabilities()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = completed_keys(stage)
    print(f"{stage}: {len(cached):,} successful responses already cached")

    jobs: list[tuple[str, dict, dict]] = []
    for language in languages:
        builder = classify_jobs if stage == "classify" else validate_jobs
        built = (builder(language, limit, caps, runs) if stage == "classify"
                 else builder(language, limit, caps))
        fresh = [j for j in built if j[0] not in cached]
        print(f"  {language}: {len(built):,} jobs, {len(fresh):,} to run")
        jobs.extend(fresh)

    if not jobs:
        print("nothing to do; all responses cached")
        return

    est = 2_600 if stage == "classify" else 1_000
    runner = Runner(stage, concurrency, caps.get("model", S.MODEL), caps,
                    tpm=tpm, est_tokens=est)
    runner.total = len(jobs)
    print(f"\nrunning {len(jobs):,} requests at {concurrency} concurrent, "
          f"throttled to {tpm:,} tokens/min\n")
    try:
        await asyncio.gather(*(runner.call(k, m, b) for k, m, b in jobs))
    except OutOfCredits as exc:
        print(f"\n!! OUT OF CREDITS: {exc}")
        print("   Everything already paid for is cached. Add credits and "
              "re-run the same command; it resumes and re-bills nothing.")
    finally:
        await runner.close()

    elapsed = time.time() - runner.started
    pin, pout = price_for(runner.model)
    cost = (runner.tokens_in / 1e6 * pin) + (runner.tokens_out / 1e6 * pout)
    print(f"\n{stage} finished: {runner.done:,} ok, {runner.errors:,} failed, "
          f"{elapsed / 60:.1f} min, ${cost:,.2f}")
    print(f"  tokens in {runner.tokens_in:,}  out {runner.tokens_out:,}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=["classify", "validate"], required=True)
    ap.add_argument("--language", choices=list(LANGUAGES), action="append")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--concurrency", type=int, default=12,
                    help="in-flight requests; the TPM budget is the real cap")
    ap.add_argument("--tpm", type=int, default=200_000,
                    help="tokens-per-minute budget to self-throttle to")
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()

    load_dotenv(REPO / ".env")
    asyncio.run(run_stage(args.stage, args.language or list(LANGUAGES),
                          args.limit, args.concurrency, args.runs, args.tpm))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

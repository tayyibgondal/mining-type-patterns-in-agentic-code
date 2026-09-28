"""Preflight: find out which request parameters the Stage 2 model accepts.

GPT-5.x reasoning models reject `temperature` on some variants, and structured
outputs are only available where the model advertises `json_schema`. Discovering
that during a 100,000-request batch is expensive, so this probe makes a handful
of single calls first and writes what it learns to
`datasets/llm_cache/model_capabilities.json`, which the Stage 2 runner reads.

Costs a fraction of a cent. Run once per model.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "datasets" / "llm_cache" / "model_capabilities.json"

SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "probe",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        },
    },
}

MESSAGES = [
    {"role": "system", "content": "Reply with JSON only."},
    {"role": "user", "content": 'Reply exactly {"ok": true}.'},
]


def try_call(client: OpenAI, model: str, label: str, **extra) -> tuple[bool, str]:
    try:
        r = client.chat.completions.create(
            model=model, messages=MESSAGES, **extra)
        return True, (r.choices[0].message.content or "")[:80]
    except Exception as exc:  # noqa: BLE001 - reporting, not handling
        return False, f"{type(exc).__name__}: {exc}"[:200]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="gpt-5.6-luna")
    args = ap.parse_args()

    load_dotenv(REPO / ".env")
    client = OpenAI()

    caps: dict[str, object] = {"model": args.model}
    print(f"probing {args.model}\n")

    ok, detail = try_call(client, args.model, "baseline")
    caps["reachable"] = ok
    print(f"  baseline          {'ok' if ok else 'FAIL'}  {detail}")
    if not ok:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(caps, indent=2))
        print("\nModel unreachable. Fix credentials or model id before Stage 2.")
        return 1

    for label, extra in (
        ("temperature", {"temperature": 0.0}),
        ("seed", {"seed": 7}),
        ("json_object", {"response_format": {"type": "json_object"}}),
        ("json_schema", {"response_format": SCHEMA}),
        ("max_completion_tokens", {"max_completion_tokens": 64}),
    ):
        ok, detail = try_call(client, args.model, label, **extra)
        caps[label] = ok
        print(f"  {label:<18}{'ok' if ok else 'unsupported'}  "
              f"{'' if ok else detail}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(caps, indent=2))
    print(f"\nwrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

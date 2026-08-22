#!/usr/bin/env python3
"""Step 4A.10 Phase 31 — >=40 formatting-only mutations of locked semantic
cases. Presentation changes only; legal meaning unchanged."""
import json
import re
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_benchmark.json"
OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_mutations.json"

CASES = json.load(open(BENCH))
positives = [c for c in CASES if c["label"] == "POSITIVE"]


def mutate_whitespace(text):
    return re.sub(r" ", "  ", text)


def mutate_linebreaks(text):
    words = text.split(" ")
    out = []
    for i, w in enumerate(words):
        out.append(w)
        if (i + 1) % 10 == 0:
            out.append("\n")
    return " ".join(out).replace(" \n ", "\n")


def mutate_numbering(text):
    return f"1.1  {text}"


def mutate_heading(text):
    return f"SECTION 7 — INDEMNIFICATION AND RISK ALLOCATION\n\n{text}"


def mutate_bullets(text):
    parts = text.split(", ")
    if len(parts) > 1:
        return parts[0] + ":\n" + "\n".join(f"  - {p}" for p in parts[1:])
    return f"  - {text}"


def mutate_punctuation_spacing(text):
    return text.replace(", ", " , ").replace(". ", " . ")


def mutate_tabs(text):
    return "\t" + text.replace(". ", ".\t")


MUTATORS = [mutate_whitespace, mutate_linebreaks, mutate_numbering, mutate_heading,
            mutate_bullets, mutate_punctuation_spacing, mutate_tabs]

MUTATIONS = []
i = 0
for case in positives:
    mutator = MUTATORS[i % len(MUTATORS)]
    MUTATIONS.append({
        "id": f"S4A10-MUT-{i + 1:03d}",
        "source_id": case["id"],
        "mutation": mutator.__name__,
        "text": mutator(case["text"]),
        "note": f"formatting mutation of {case['id']} via {mutator.__name__}",
    })
    i += 1
    if i >= 40:
        break

OUT.write_text(json.dumps(MUTATIONS, indent=2))
print(f"Wrote {len(MUTATIONS)} formatting mutations to {OUT}")

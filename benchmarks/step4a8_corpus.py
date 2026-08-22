"""Step 4A.8 — independent held-out corpus loader. Loads the locked JSON
corpus files (step4a8_corpus_semantic.json, step4a8_corpus_formatting_
mutations.json) — the JSON files, not this loader, are the locked artifact;
this module exists only so benchmark runners can `from
benchmarks.step4a8_corpus import CASES, MUTATIONS` like every other corpus
in this repo."""
import json
from pathlib import Path

_DIR = Path(__file__).resolve().parent

with open(_DIR / "step4a8_corpus_semantic.json") as f:
    CASES = json.load(f)

with open(_DIR / "step4a8_corpus_formatting_mutations.json") as f:
    MUTATIONS = json.load(f)

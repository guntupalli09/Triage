"""Step 4A.11 Phase 4 — overlap check for the fresh adversarial battery.

Methodology: exact-substring and n-gram-overlap checks between each
battery case's text and every case text in the corpora this battery is
required to be independent of. This is NOT a semantic-similarity check
(no embeddings/LLM judgment used) -- it is a literal-text-reuse
detector, which is what "do not copy or lightly paraphrase" requires
catching: verbatim copies, near-verbatim copies (shared long n-grams),
and systematic synonym-substitution templates (shared short/mid n-grams
at high density). A genuinely independently-authored case describing a
similar legal concept in different words will share few, if any, n-grams
of length >= 6 words with any prior corpus case -- ordinary short legal
phrases ("shall not exceed", "third-party claims") are expected to
recur across any two indemnification/liability corpora and are not
evidence of copying by themselves; this check flags LONGER shared runs.

Limitation, disclosed: this cannot detect purely conceptual
reuse (the same legal scenario described in completely different
words) -- that is a design intent this script cannot verify
automatically. Human/self-review of the case list against the
implementation code (checking new verb clusters and cross-reference
prose used in Phase 1-3 aren't reused verbatim) supplements this
mechanical check.
"""

import json
import re
import sys

sys.path.insert(0, ".")

from benchmarks.step4a11_fresh_adversarial_battery import CASES as BATTERY_CASES

N = 6  # shared n-gram length (words) that counts as notable overlap


def ngrams(text: str, n: int = N):
    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    return set(tuple(words[i:i + n]) for i in range(len(words) - n + 1))


def load_prior_corpora():
    corpora = {}

    import scripts.step4a10_generate_corpus as g
    corpora["step4a10_corpus"] = [c["text"] for c in g.CASES]

    from benchmarks.step4a11_cross_reference_dev_benchmark import CASES as p1
    corpora["phase1_dev_benchmark"] = [c["text"] for c in p1]

    from benchmarks.step4a11_conditional_applicability_dev_benchmark import CASES as p2
    corpora["phase2_dev_benchmark"] = [c["text"] for c in p2]

    from benchmarks.step4a11_structural_risk_transfer_dev_benchmark import CASES as p3
    corpora["phase3_dev_benchmark"] = [c["text"] for c in p3]

    return corpora


def main() -> None:
    corpora = load_prior_corpora()
    corpus_ngrams = {name: [(text, ngrams(text)) for text in texts] for name, texts in corpora.items()}

    findings = []
    for case in BATTERY_CASES:
        case_ng = ngrams(case["text"])
        if not case_ng:
            continue
        for corpus_name, entries in corpus_ngrams.items():
            for prior_text, prior_ng in entries:
                shared = case_ng & prior_ng
                if shared:
                    findings.append({
                        "battery_id": case["id"], "corpus": corpus_name,
                        "shared_ngram_count": len(shared),
                        "example_shared_ngram": " ".join(next(iter(shared))),
                        "prior_text_excerpt": prior_text[:100],
                    })

    print(f"Battery size: {len(BATTERY_CASES)}")
    print(f"Prior corpora checked: {list(corpora.keys())}")
    print(f"Total prior cases checked against: {sum(len(v) for v in corpora.values())}")
    print(f"N-gram length used for overlap: {N} words")
    print()
    print(f"Cases with >=1 shared {N}-word n-gram against any prior corpus: "
          f"{len(set(f['battery_id'] for f in findings))} / {len(BATTERY_CASES)}")
    print()
    if findings:
        print("=== FINDINGS (each an exact shared 6+-word run) ===")
        for f in findings:
            print(f"  {f['battery_id']} <-> {f['corpus']}: \"{f['example_shared_ngram']}\" "
                  f"(prior: {f['prior_text_excerpt']!r})")
    else:
        print("No shared 6+-word runs found against any prior corpus.")


if __name__ == "__main__":
    main()

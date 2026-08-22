"""Step 4A.11 Phase 6 -- overlap check for the final authoritative corpus.

Same literal n-gram-overlap methodology as
scripts/step4a11_battery_overlap_check.py (see that file's docstring for the
full methodology/limitation disclosure), extended to also check against the
Phase 4 fresh adversarial battery itself, since the final corpus must be
independent of it as well as the Step 4A.10/4A.10.x and Phase 1-3 corpora.
"""
import re
import sys

sys.path.insert(0, ".")

from benchmarks.step4a11_final_corpus import CASES as FINAL_CASES

N = 6


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

    from benchmarks.step4a11_fresh_adversarial_battery import CASES as p4
    corpora["phase4_battery"] = [c["text"] for c in p4]

    return corpora


def main() -> None:
    corpora = load_prior_corpora()
    corpus_ngrams = {name: [(text, ngrams(text)) for text in texts] for name, texts in corpora.items()}

    findings = []
    for case in FINAL_CASES:
        case_ng = ngrams(case["text"])
        if not case_ng:
            continue
        for corpus_name, entries in corpus_ngrams.items():
            for prior_text, prior_ng in entries:
                shared = case_ng & prior_ng
                if shared:
                    findings.append({
                        "final_id": case["id"], "corpus": corpus_name,
                        "shared_ngram_count": len(shared),
                        "example_shared_ngram": " ".join(next(iter(shared))),
                        "prior_text_excerpt": prior_text[:100],
                    })

    print(f"Final corpus size: {len(FINAL_CASES)}")
    print(f"Prior corpora checked: {list(corpora.keys())}")
    print(f"Total prior cases checked against: {sum(len(v) for v in corpora.values())}")
    print(f"N-gram length used for overlap: {N} words")
    print()
    print(f"Cases with >=1 shared {N}-word n-gram against any prior corpus: "
          f"{len(set(f['final_id'] for f in findings))} / {len(FINAL_CASES)}")
    print()
    if findings:
        print("=== FINDINGS (each an exact shared 6+-word run) ===")
        for f in findings:
            print(f"  {f['final_id']} <-> {f['corpus']}: \"{f['example_shared_ngram']}\" "
                  f"(prior: {f['prior_text_excerpt']!r})")
    else:
        print("No shared 6+-word runs found against any prior corpus.")


if __name__ == "__main__":
    main()

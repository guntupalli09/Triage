"""Step 4A.11 Remediation — Phase 7 overlap check for the fresh
remediation-validation corpus. Same literal n-gram methodology as prior
overlap checks, extended to include the Phase 6 final 393-case corpus AND
the Phase 2 role-boundary DEV benchmark (rb-*) as additional prior
corpora this new corpus must be independent of.
"""
import re
import sys

sys.path.insert(0, ".")

from benchmarks.step4a11_remediation_validation_corpus import CASES as RV_CASES

N = 6


def ngrams(text, n=N):
    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    return set(tuple(words[i:i + n]) for i in range(len(words) - n + 1))


def words(text):
    return re.findall(r"[A-Za-z0-9']+", text.lower())


def longest_common_run(a, b):
    lo, hi, best = 1, min(len(a), len(b)), 0
    while lo <= hi:
        mid = (lo + hi) // 2
        A = set(tuple(a[i:i + mid]) for i in range(len(a) - mid + 1))
        B = set(tuple(b[i:i + mid]) for i in range(len(b) - mid + 1))
        if A & B:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def load_prior_texts():
    texts = []
    import scripts.step4a10_generate_corpus as g
    texts += [c["text"] for c in g.CASES]
    from benchmarks.step4a11_cross_reference_dev_benchmark import CASES as p1
    texts += [c["text"] for c in p1]
    from benchmarks.step4a11_conditional_applicability_dev_benchmark import CASES as p2
    texts += [c["text"] for c in p2]
    from benchmarks.step4a11_structural_risk_transfer_dev_benchmark import CASES as p3
    texts += [c["text"] for c in p3]
    from benchmarks.step4a11_fresh_adversarial_battery import CASES as p4
    texts += [c["text"] for c in p4]
    from benchmarks.step4a11_final_corpus import CASES as p6
    texts += [c["text"] for c in p6]
    from benchmarks.step4a11_remediation_role_boundary_dev_benchmark import CASES as rb
    texts += [c["text"] for c in rb]
    return texts


def main():
    prior_texts = load_prior_texts()
    prior_words = [words(t) for t in prior_texts]

    worst = []
    for c in RV_CASES:
        cw = words(c["text"])
        m = 0
        for pw in prior_words:
            r = longest_common_run(cw, pw)
            if r > m:
                m = r
        worst.append((m, c["id"]))
    worst.sort(reverse=True)

    print(f"RV corpus size: {len(RV_CASES)}")
    print(f"Prior cases checked against: {len(prior_texts)}")
    print(f"Max longest-common-run: {worst[0][0]} words ({worst[0][1]})")
    print(f"Cases with run >=10 words: {sum(1 for m, _ in worst if m >= 10)}")
    print(f"Cases with run >=13 words: {sum(1 for m, _ in worst if m >= 13)}")
    print("\nTop 15:")
    for m, cid in worst[:15]:
        print(f"  {m} {cid}")


if __name__ == "__main__":
    main()

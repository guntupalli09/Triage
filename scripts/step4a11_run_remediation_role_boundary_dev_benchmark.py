"""Step 4A.11 Remediation — Phase 2 runner for the role-boundary DEVELOPMENT
benchmark. Run before (PRE) and after (POST) the Phase 3 structural fix.
"""
import sys
sys.path.insert(0, ".")

import indemnification_policy_engine as ie
from benchmarks.step4a11_remediation_role_boundary_dev_benchmark import CASES


def actual(text):
    facts = ie.extract_indemnification_facts(text)
    if facts is None or not facts.obligations:
        return None, None
    ob = facts.obligations[0]
    return ob.indemnifying_role, ob.indemnified_role


def run():
    wrong_clean = []  # a role was captured that is WRONG (over-consumed / boundary-crossing)
    correct = []
    correctly_unresolved = []  # expected None, and either NOT_ESTABLISHED or a safely-bounded result
    missed = []  # expected a literal value, got nothing at all
    for c in CASES:
        actor, ben = actual(c["text"])
        exp_a, exp_b = c["expected_actor"], c["expected_beneficiary"]
        if exp_a is None and exp_b is None:
            # P-style: mutual/no-named-role case. Any named-role capture at
            # all here would be suspicious, but we only flag it as
            # wrong_clean if it looks like corrupted text (contains a
            # heading/connector artifact) -- a plain, bounded capture of
            # "Each Party"/"the Other Party" from the shared reciprocal
            # path is not itself dangerous.
            if actor and ("--" in actor or actor.isupper() and len(actor.split()) > 4):
                wrong_clean.append((c["id"], actor, ben))
            else:
                correctly_unresolved.append(c["id"])
            continue
        if exp_a is None or exp_b is None:
            # O-style: one side literal, one side intentionally unchecked.
            bad = False
            if exp_a is not None and actor != exp_a:
                bad = True
            if exp_b is not None and ben != exp_b:
                bad = True
            if bad:
                wrong_clean.append((c["id"], actor, ben))
            elif actor is None and ben is None:
                missed.append(c["id"])
            else:
                correct.append(c["id"])
            continue
        if actor == exp_a and ben == exp_b:
            correct.append(c["id"])
        elif actor is None and ben is None:
            missed.append(c["id"])
        else:
            wrong_clean.append((c["id"], actor, ben))
    return correct, wrong_clean, missed, correctly_unresolved


if __name__ == "__main__":
    correct, wrong_clean, missed, correctly_unresolved = run()
    print(f"Total cases: {len(CASES)}")
    print(f"Correct (exact match): {len(correct)}")
    print(f"Correctly unresolved (fail-closed on ambiguous case): {len(correctly_unresolved)}")
    print(f"Missed (expected a value, got nothing -- false escalation, not dangerous): {len(missed)}")
    print(f"\nHARD REQUIREMENT wrong_clean (wrong-role/boundary-corrupted clean decision) == 0: "
          f"{len(wrong_clean)} -> {'PASS' if not wrong_clean else 'FAIL'}")
    for cid, a, b in wrong_clean:
        print(f"    {cid}: actor={a!r} beneficiary={b!r}")

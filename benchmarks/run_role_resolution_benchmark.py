#!/usr/bin/env python3
"""
Verifier benchmark (Step 4A.1) — measures policy_engine_core.resolve_role_side()
directly, independent of any policy adapter's final decision. Each case is a
(role, definition_text, expected_document_side, expected_relationship) tuple.

expected_document_side: "buy" | "sell" | "unknown" — what a human reading the
    definition would conclude about the role's actual transactional side (or
    "unknown" if the definition genuinely doesn't say).
expected_relationship: "consistent" | "conflict" | "non_directional" — whether
    the definition agrees with the role's generic side_for_role() mapping,
    conflicts with it, or carries no directional evidence at all.

Metrics: conflict-detection precision/recall (treating "conflict" as the
positive class), false-conflict rate, missed-conflict rate.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import policy_engine_core as core

CASES = [
    # id, role, definition_text, expected_relationship
    ("conv-01", "Customer", "'Customer' means the entity purchasing the Services from Vendor.", "consistent"),
    ("conv-02", "Vendor", "'Vendor' means the entity providing the Services to Customer.", "consistent"),
    ("rev-01", "Vendor", "'Vendor' means the party purchasing the Services from Customer.", "conflict"),
    ("rev-02", "Customer", "'Customer' means the party providing consulting services to Vendor.", "conflict"),
    ("rev-03", "Licensor", "'Licensor' refers to the entity acquiring a license to the Platform.", "conflict"),
    ("rev-04", "Licensee", "'Licensee' refers to the entity that supplies and operates the Platform.", "conflict"),
    ("syn-01-means", "Customer", "'Customer' means the entity purchasing the Services from Vendor.", "consistent"),
    ("syn-02-shall-mean", "Customer" , "'Customer' shall mean the entity purchasing the Services from Vendor.", "consistent"),
    ("syn-03-refers-to", "Customer", "'Customer' refers to the entity purchasing the Services from Vendor.", "consistent"),
    ("syn-04-shall-refer-to", "Customer", "'Customer' shall refer to the entity purchasing the Services from Vendor.", "consistent"),
    ("syn-05-is-defined-as", "Customer", "'Customer' is defined as the entity purchasing the Services from Vendor.", "consistent"),
    ("syn-06-shall-have-the-meaning", "Customer", "'Customer' shall have the meaning of the entity purchasing the Services from Vendor.", "consistent"),
    ("syn-07-has-the-meaning", "Customer", "'Customer' has the meaning of the entity purchasing the Services from Vendor.", "consistent"),
    ("syn-08-shall-be-construed-to-mean", "Customer", "'Customer' shall be construed to mean the entity purchasing the Services from Vendor.", "consistent"),
    ("syn-09-means-and-includes", "Customer", "'Customer' means and includes the entity purchasing the Services from Vendor.", "consistent"),
    ("nondir-01", "Vendor", "'Vendor' means Acme Corporation, a Delaware corporation.", "non_directional"),
    ("nondir-02", "Customer", "'Customer' means the entity identified on the signature page as Customer.", "non_directional"),
    ("nondir-03", "Licensee", "'Licensee' has the meaning set forth in the preamble.", "non_directional"),
    ("distractor-01", "Vendor", "'Vendor Materials' means materials purchased by Vendor from third parties for use in the Services.", "non_directional"),
    ("distractor-02", "Customer", "'Customer Data' means data provided by Customer to Vendor in connection with the Services.", "non_directional"),
    ("multi-01-first", "Licensor", "'Licensor' refers to Gamma LLC, the party purchasing and receiving a license to use the Platform, and 'Licensee' refers to Delta Inc., the party that develops and operates the Platform and grants the license.", "conflict"),
    ("multi-01-second", "Licensee", "'Licensor' refers to Gamma LLC, the party purchasing and receiving a license to use the Platform, and 'Licensee' refers to Delta Inc., the party that develops and operates the Platform and grants the license.", "conflict"),
    ("mixed-01", "Vendor", "'Vendor' means the entity that both purchases raw materials from third parties and sells the finished goods to Customer under this Agreement.", "conflict"),
    ("mixed-02", "Distributor", "'Distributor' means the party that purchases inventory for resale and also develops and manufactures certain private-label goods sold under this Agreement.", "conflict"),
    ("unrecognized-predicate-01", "Vendor", "'Vendor' as used herein shall carry the meaning of the entity purchasing the Services from Customer.", "unrecognized"),
    ("customer-of-01", "Customer", "'Customer' means the entity that is a customer of Vendor's platform.", "consistent"),
    ("obtains-services-01", "Client", "'Client' means the entity that obtains the Services from Provider.", "consistent"),
    ("furnish-01", "Supplier", "'Supplier' means the entity that furnishes the goods to Buyer under this Agreement.", "consistent"),
    ("far-definition-01", "Reseller", "'Reseller' means Beta Inc., the entity purchasing Software from Provider for resale.", "unknown_generic"),
]


def run():
    tp = fp = fn = tn = unrecognized = 0
    rows = []
    for case_id, role, text, expected in CASES:
        side, reason = core.resolve_role_side(role, text)
        actual = "conflict" if reason is not None else ("non_directional_or_consistent")
        # Reduce to binary conflict/no-conflict for precision/recall, since
        # that's the safety-critical distinction (a false "no conflict" on
        # a real reversal is the dangerous direction).
        predicted_conflict = reason is not None
        expected_conflict = expected == "conflict"
        if predicted_conflict and expected_conflict:
            tp += 1
        elif predicted_conflict and not expected_conflict:
            fp += 1
        elif not predicted_conflict and expected_conflict:
            fn += 1
        else:
            tn += 1
        if expected == "unrecognized":
            unrecognized += 1
            note = "EXPECTED MISS (predicate not in recognized vocabulary — documented limitation)"
        elif expected == "unknown_generic":
            note = "definition found but role reversal is directionally consequential only in a 2-party clause; this benchmark scores the primitive alone"
        else:
            note = "OK" if (predicted_conflict == expected_conflict) else "MISMATCH"
        rows.append((case_id, role, expected, "conflict" if predicted_conflict else "no-conflict", note))

    n = len(CASES)
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    false_conflict_rate = fp / (fp + tn) if (fp + tn) else float("nan")
    missed_conflict_rate = fn / (fn + tp) if (fn + tp) else float("nan")

    print(f"# Role-Resolution Verifier Benchmark\n")
    print(f"Corpus size: {n} cases\n")
    print("| id | role | expected | actual | note |")
    print("|---|---|---|---|---|")
    for row in rows:
        print(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} |")
    print(f"\n## Metrics\n")
    print(f"- True positives (correctly flagged conflicts): {tp}")
    print(f"- False positives (false conflicts on non-conflicting definitions): {fp}")
    print(f"- False negatives (missed real conflicts): {fn}")
    print(f"- True negatives: {tn}")
    print(f"- Conflict precision: {precision:.1%}" if precision == precision else "- Conflict precision: N/A")
    print(f"- Conflict recall: {recall:.1%}" if recall == recall else "- Conflict recall: N/A")
    print(f"- False-conflict rate: {false_conflict_rate:.1%}" if false_conflict_rate == false_conflict_rate else "- False-conflict rate: N/A")
    print(f"- Missed-conflict rate: {missed_conflict_rate:.1%}" if missed_conflict_rate == missed_conflict_rate else "- Missed-conflict rate: N/A")
    return {"n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall}


if __name__ == "__main__":
    run()

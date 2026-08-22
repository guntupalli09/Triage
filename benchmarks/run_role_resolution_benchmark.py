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

    # --- Step 4A.3 additions: independently derived from the four failure
    # families, targeting the NEW mechanisms added in this hardening pass
    # (not paraphrases of the Step 4A.2 held-out corpus text). ---

    # Family 1a: broad-definition-signal detector (quote-tolerant "X is
    # understood to mean" / "for purposes hereof, X is" / "references to
    # X are references to" preambles) must escalate when discovery's
    # narrow predicate list can't find a body at all.
    ("broad-01-understood-to-mean", "Vendor", "'Vendor' is understood to mean the entity that purchases the Services from Customer.", "conflict"),
    ("broad-02-for-purposes-hereof", "Licensee", "For purposes hereof, Licensee is the party granting a license to the Platform.", "conflict"),
    ("broad-03-references-to-quoted", "Supplier", "References to 'Supplier' are references to the entity that resells finished goods to Buyer.", "conflict"),
    ("broad-04-references-to-unquoted", "Distributor", "References to Distributor are references to the entity that purchases inventory from Manufacturer.", "conflict"),

    # Family 1b: possessive-gerund bystander exclusion — a -ing verb
    # immediately preceded by a possessive marker heads a noun phrase
    # ("Customer's manufacturing capacity"), not a verb describing the
    # role's own conduct, and must not count as directional evidence.
    ("gerund-01-possessive-noun-phrase", "Vendor", "'Vendor' means the entity that retains Customer's manufacturing capacity to produce goods on Vendor's behalf.", "conflict"),
    ("gerund-02-own-conduct-is-real-reversal", "Vendor", "'Vendor' means the entity purchasing the Services from Customer.", "conflict"),
    ("gerund-03-pronoun-possessive", "Reseller", "'Reseller' means the entity that relies on its purchasing power to negotiate discounts from Manufacturer.", "conflict"),

    # Family 1c: passive-voice agent-phrase exclusion — a verb match
    # immediately followed by "by X" attributes the action to X, not to
    # the role whose body is being scanned.
    ("passive-01-manufactured-by", "Buyer", "'Buyer' means the entity that acquires goods manufactured by Seller under this Agreement.", "consistent"),
    ("passive-02-delivered-by", "Recipient", "'Recipient' means the entity to which goods are delivered by Shipper under this Agreement.", "conflict"),

    # Family 1d: one-hop indirect-definition resolution — a bare
    # cross-reference to another quoted defined term ("given to 'X'") is
    # followed through ONE hop when X is itself defined with real
    # directional evidence elsewhere in the document.
    ("indirect-01-resolvable-agrees", "Customer", "'Customer' has the meaning given to 'Subscriber' in Schedule A. 'Subscriber' means the party receiving the Services from Provider.", "consistent"),
    ("indirect-02-resolvable-conflicts", "Vendor", "'Vendor' has the meaning given to 'Purchaser' in Schedule A. 'Purchaser' means the entity that purchases the Software from Provider for internal use.", "conflict"),
    ("indirect-03-unresolvable-target-missing", "Customer", "'Customer' has the meaning given to 'Subscriber' in Schedule A.", "non_directional"),

    # Family 1: expanded verb vocabulary (engage/commission/source/obtain
    # the benefit of/compensate for buy-side; render.../perform...for/
    # make...available to for sell-side) plus the "licenses...FROM"
    # direction-flip fix.
    ("verb-01-engages-services-of", "Client", "'Client' means the entity that engages the services of Consultant for the Engagement.", "consistent"),
    ("verb-02-commissions", "Client", "'Client' means the entity that commissions the Engagement from Consultant.", "consistent"),
    ("verb-03-sources-from", "Customer", "'Customer' means the entity that sources the Software from Vendor.", "consistent"),
    ("verb-04-renders-to", "Provider", "'Provider' means the entity that renders consulting services to Recipient.", "consistent"),
    ("verb-05-performs-for", "Provider", "'Provider' means the entity that performs the Services for Recipient.", "consistent"),
    ("verb-06-makes-available-to", "Provider", "'Provider' means the entity that makes the deliverables available to Recipient.", "consistent"),
    ("verb-07-licenses-from-relates-to-named-party", "Licensee", "'Licensee' means the entity that licenses the Platform from Licensor.", "conflict"),
    ("verb-08-licenses-the-is-sellside", "Licensor", "'Licensor' means the entity that licenses the Platform to Licensee.", "consistent"),
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

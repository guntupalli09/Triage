"""
Step 4A.3 — Indemnification reciprocal-asymmetry benchmark. Targets the
mechanism built for Failure Family 4: a clause must not be treated as
reciprocal merely because its opener is reciprocal, when later text
creates a deterministically-detectable party-specific difference; only
deterministically-establishable asymmetries are supported, otherwise
REQUIRES_REVIEW.

Each case: (id, text, expect_asymmetry_detected).
  expect_asymmetry_detected: True if _detect_reciprocal_asymmetry should
      return a non-empty reasons list for the mutual/reciprocal
      obligation found in the text; False if it should be empty (a
      genuinely symmetric clause).
"""

CASES = [
    # --- genuinely reciprocal / symmetric (8) ---
    ("asym-01", "8. Indemnification. Each party shall indemnify, defend, and hold harmless the other party from and against third-party claims arising from the indemnifying party's gross negligence, up to a cap equal to 1 times the fees paid.", False),
    ("asym-02", "8. Indemnification. The parties shall mutually indemnify, defend, and hold harmless each other from and against third-party claims arising from breach of this Agreement, up to a cap of 2 times the fees paid.", False),
    ("asym-03", "8. Indemnification. Each party shall indemnify the other party from third-party IP infringement claims, without limitation as to amount.", False),
    ("asym-04", "8. Indemnification. Each party shall indemnify, defend, and hold harmless the other party from and against third-party claims, up to a cap of 3 times the fees paid, subject to a notice and cooperation requirement.", False),
    ("asym-05", "8. Indemnification. The parties shall mutually indemnify each other from and against third-party claims arising from gross negligence or willful misconduct, up to a cap of 1 times the fees paid.", False),
    ("asym-06", "8. Indemnification. Each party shall indemnify, defend, and hold harmless the other party and its affiliates from and against third-party claims, up to a cap of 2 times the fees paid.", False),
    ("asym-07", "8. Indemnification. Each party shall indemnify the other party from third-party claims arising from breach of confidentiality, up to a cap of 1 times the fees paid, provided the indemnified party gives prompt notice.", False),
    ("asym-08", "8. Indemnification. The parties shall mutually indemnify each other from and against third-party claims, up to a cap of 2 times the fees paid, and each party shall control the defense of claims against it.", False),

    # --- clearly one-way (not mutual at all — no asymmetry mechanism engaged, treated separately) (4) ---
    ("asym-09", "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against third-party claims arising from Vendor's gross negligence, up to a cap of 1 times the fees paid.", None),
    ("asym-10", "8. Indemnification. Provider shall indemnify Customer from third-party IP infringement claims, without limitation as to amount.", None),
    ("asym-11", "8. Indemnification. Licensor shall indemnify, defend, and hold harmless Licensee from and against third-party claims arising from the Platform, up to a cap of 3 times the fees paid.", None),
    ("asym-12", "8. Indemnification. Consultant shall indemnify Client from third-party claims arising from Consultant's negligence, up to a cap of 2 times the fees paid.", None),

    # --- reciprocal opener + party-specific carve-out (differing cap for one named party) (5) ---
    ("asym-13", "8. Indemnification. Each party shall indemnify, defend, and hold harmless the other party from and against third-party claims arising from the indemnifying party's gross negligence, up to a cap equal to 2 times the fees paid, except that Vendor's cap for IP infringement claims shall be 4 times the fees paid.", True),
    ("asym-14", "8. Indemnification. The parties shall mutually indemnify each other from and against third-party claims, up to a cap of 1 times the fees paid, provided that Customer's cap shall be 3 times the fees paid.", True),
    ("asym-15", "8. Indemnification. Each party shall indemnify the other party from third-party claims, up to a cap of 2 times the fees paid, except that Licensor's obligations shall not exceed 5 times the fees paid.", True),
    ("asym-16", "8. Indemnification. Each party shall indemnify the other party from third-party claims. Vendor's indemnification obligations under this Section shall not exceed 1 times the fees paid. Customer's indemnification obligations under this Section shall not exceed 5 times the fees paid.", True),
    ("asym-17", "8. Indemnification. The parties shall mutually indemnify each other from third-party claims. Vendor's indemnification obligations under this Section shall not exceed 1 times the fees paid. Customer's indemnification obligations under this Section shall not exceed 3 times the fees paid.", True),

    # --- reciprocal opener + different cap stated for both named parties, differing from each other (3) ---
    ("asym-18", "8. Indemnification. Each party shall indemnify the other party from third-party claims, provided that Vendor's obligations under this Section shall not exceed 1 times the fees paid and Customer's obligations under this Section shall not exceed 4 times the fees paid.", True),
    ("asym-19", "8. Indemnification. The parties shall mutually indemnify each other, provided that Licensor's obligations under this Section shall not exceed 2 times the fees paid and Licensee's obligations under this Section shall not exceed 2 times the fees paid.", False),
    ("asym-20", "8. Indemnification. Each party shall indemnify the other, provided that Provider's obligations under this Section shall not exceed 1 times the fees paid and Recipient's obligations under this Section shall not exceed 6 times the fees paid.", True),

    # --- reciprocal opener + different claim categories/triggers for one named party (3) ---
    ("asym-21", "8. Indemnification. Each party shall indemnify the other party from third-party claims arising from gross negligence, except that Vendor's indemnification obligations under this Section shall also include claims arising from IP infringement.", True),
    ("asym-22", "8. Indemnification. The parties shall mutually indemnify each other from third-party claims arising from willful misconduct, provided that Customer's indemnification obligations under this Section shall be limited to claims arising from gross negligence only.", True),
    ("asym-23", "8. Indemnification. Each party shall indemnify the other from third-party claims arising from gross negligence, except that Licensee's indemnification obligations under this Section shall also cover claims arising from data breach.", True),

    # --- ambiguous asymmetry (structurally present but not deterministically resolvable — conservative True is the safe/acceptable outcome) (3) ---
    ("asym-24", "8. Indemnification. Each party shall indemnify the other party from third-party claims, up to a cap of 2 times the fees paid, except that Vendor's obligations shall be handled in accordance with the parties' separate understanding.", None),
    ("asym-25", "8. Indemnification. The parties shall mutually indemnify each other from third-party claims, subject to such additional or different terms as the parties may agree with respect to a particular Order Form.", None),
    ("asym-26", "8. Indemnification. Each party shall indemnify the other party from third-party claims arising from its own acts or omissions, on terms to be further specified by the parties from time to time.", None),
]

assert len(CASES) == 26, len(CASES)

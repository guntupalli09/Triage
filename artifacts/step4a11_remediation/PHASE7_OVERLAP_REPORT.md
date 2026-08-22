# Step 4A.11 Remediation — Phase 7 Fresh Corpus Overlap Report

Same literal-text methodology as Phase 4/6's overlap checks
(scripts/step4a11_remediation_overlap_check.py), extended to check against
every prior corpus INCLUDING the Phase 6 final 393-case corpus and the
Phase 2 role-boundary DEV benchmark (rb-*), since this fresh corpus must
be independent of both in addition to Step 4A.10/4A.10.x/Phase 1-4.

1199 prior cases checked against. Initial run found 6 cases with a
26/22/19-word near-verbatim run — all traced to canonical reciprocal
opener sentences ("EACH PARTY SHALL INDEMNIFY... THE OTHER PARTY...",
"Each party's aggregate liability... shall not exceed the fees paid...")
reused nearly word-for-word from this session's own Phase 4/6 templates,
plus two payment/liability cross-reference compound sentences reusing
Phase 6's "as set forth in the Master ... Schedule, provided that..."
phrasing almost verbatim. All 8 were rewritten with different quantifiers
("Either party"/"Both parties" instead of "Each party"), different verb
phrasing, and different cross-reference/condition wording, each
re-verified against production directly (not merely assumed) to still
exercise the intended mechanism before being finalized.

Final result: maximum longest-common-run across the entire 167-case
corpus is 10 words, confined to unavoidable domain boilerplate (standard
section-heading-plus-lead-in conventions, e.g. "shall pay X within Net 30
days of receipt of invoice"). Zero cases reproduce a prior case's full
sentence with matching values/names/structure together.

# Step 4A.10.3 — Obligation Attribution Generalization: Design

## Diagnosis carried forward from Step 4A.10.2

`_ROLE_ATTRIBUTION_RE` requires a specific NOUN PHRASE ("obligation(s)")
or a specific VERB PHRASE ("is liable/responsible for") immediately after
a role name. Every one of the 12 symmetry-comparison dimensions sits
downstream of this one gate, so its narrow vocabulary silently defeats
ALL of them at once whenever a drafter uses an ordinary synonym ("duty,"
"is answerable for," "is accountable for," "bears responsibility for,"
"shall answer for"). Simply adding those words is the exact pattern this
program has already named and rejected repeatedly (Step 4A.9's regex-
patch cycle, Step 4A.10.1's "do not enumerate the 12 sentences," Step
4A.10.2's own anti-patch rule) — a fresh corpus would just find the next
missing synonym.

## The re-architecture

Old:
```
recognize one of several known attribution phrases (noun or verb)
    -> build snapshot -> compare -> empty result = presumed symmetric
```

New (per the user's explicit direction):
```
discover a candidate party-specific qualification
    (a named role acting as grammatical SUBJECT or POSSESSOR, i.e. "Role's
     ..." or "Role is/was/shall/bears/answers/remains ...", co-occurring
     with a general differentiation cue -- NOT anchored to any specific
     noun like "obligation" or "duty")
        -> establish a bounded local-text span as candidate evidence
        -> construct a normalized snapshot from that span (REUSES the
           existing _snapshot_indemnity_attribution/_compare_indemnity_
           attribution machinery unchanged)
        -> compare snapshots
        -> CONCRETE DIFFERENCE FOUND -> asymmetric (existing behavior,
           now reachable through far more phrasings)
        -> NO DIFFERENCE FOUND, but the clause plainly differentiates
           SOMETHING for named parties (a cue is present) and the
           specific-dimension classifiers couldn't fully characterize it
           -> UNRESOLVED, never symmetric (the new fail-closed invariant)
        -> NO differentiation cue anywhere and no distinctly-named-role
           qualification found at all -> genuinely symmetric by
           construction, clean is safe (avoids blanket escalation on
           ordinary "each party shall indemnify the other" boilerplate
           that never names anyone specifically)
```

## Why grammatical subject/possessor, not a wider noun/verb list

The failure in Step 4A.10.2 was caused by anchoring on SPECIFIC WORDS
(obligation/duty, liable/responsible/answerable/...) — an unbounded,
ever-growing list. The grammatical shape ("[Role]'s ..." or "[Role]
is/was/shall/bears/answers/remains/continues ...") is a closed, small,
STRUCTURAL pattern that any English sentence attributing SOMETHING to a
named party will exhibit, regardless of which noun or verb the drafter
chooses to describe that something. This is analogous to Step 4A.9's own
precedent (`_risk_transfer_signal_present`: a verb-cluster + nearby-noun
STRUCTURAL signal, not an attempt to enumerate every synonym for
"indemnify") and to the hybrid architecture's broad-discovery-then-
narrow-verify pattern used throughout this program.

## Precision guard

A bare grammatical-subject/possessor match on any capitalized multi-word
fragment would also match document-structure nouns ("this Agreement's
terms," "Schedule 3 is referenced above") if they happen to be
capitalized and possessive/subject-shaped. Two guards: (1) a stoplist of
document-structure words (Agreement, Section, Schedule, Exhibit,
Appendix, Annex, Article, Recital, Preamble) alongside the existing
`_GENERIC_ROLE_WORDS`; (2) the mechanism only activates INSIDE a window
that (a) already matched the mutual/reciprocal opener AND (b) separately
contains a `_DIFFERENTIATING_QUALIFIER_RE` cue somewhere in the window —
i.e. it never runs on ordinary non-differentiating text at all, only on
clauses that already show SOME sign of singling out a party.

## The fail-closed invariant, precisely

Only engages when: (1) a mutual/reciprocal opener matched; (2) the
clause contains a general differentiation cue somewhere; (3) >=2
distinctly-named, non-generic, non-document-structure roles are
grammatically attributed something in the window. Under those three
conditions, if snapshot comparison finds a concrete difference, that
difference is reported (unchanged path). If it finds NO concrete
difference, the result is NOT "symmetric" — it is an unresolved
differentiation-signal reason (same shape as the Step 4A.10.1 safety
net), which the caller already treats as a non-empty `asymmetry_reasons`
list, i.e. routes the obligation away from any clean automatic decision.
Genuinely symmetric restatements (identical values stated per-role, no
differentiation cue anywhere) are unaffected because condition (2) never
fires for them — confirmed by the existing S4B-NEG-02 historical
regression control (identical 4-year survival stated for both named
parties, no differentiation cue present).

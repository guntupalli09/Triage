# Step 4A.10.1 Phase 1 — S4 Root Cause

## What makes text OPERATIVE vs. merely LOOKING like contract language?

Operative text is text the parties are asserting as their actual agreed
term. Lexically-similar text stops being operative when the surrounding
document marks it as one of:

1. **A quoted example/hypothetical** — enclosed in quote marks and
   introduced by a verb/phrase whose function is "here is a sample of
   what such language might look like" rather than "the parties agree."
2. **Explicitly negated or rejected** — the document itself states, near
   the matched text, that this exact language does NOT appear, was NOT
   included, or was rejected/superseded.
3. **Meta-instructional / addressed to a reader-of-the-document-as-data**
   rather than to a counterparty — text addressed to "you," "the AI," "the
   system," or containing imperative instructions about how to process the
   document itself (a prompt-injection payload is the sharpest case of
   this, but drafting notes/reviewer comments share the same structural
   shape).
4. **Descriptive ABOUT a clause rather than the clause itself** — "a
   clause providing that X shall indemnify Y" describes a hypothetical
   clause; it is not itself an operative promise by X.

## Trace: does extraction currently use structural context?

No. `_OBLIGATION_RE` (and every other structuring regex in
`indemnification_policy_engine.py`) is a pure lexical pattern run via
`.finditer(text)`/`.search(window)` against raw document text. The ONLY
existing context check anywhere in the pipeline is the narrow
`_ANCHOR_RE` negation lookback (`not re.search(r"\bno\s+$", text[start-15
:start])`) — a single, backward-only, 15-character window checking for
the literal word "no" immediately before an anchor. It does not:
- know about quote marks at all;
- look forward for a negation ("this sentence does not appear");
- recognize quotation-introducing framing ("please quote the following");
- recognize meta-instructional/reader-addressed text;
- recognize descriptive-about-clause framing.

## Root-cause classification (per Phase 1's taxonomy)

**Primarily B (quoted text treated as operative), secondarily F
(negation/meta-language ignored) — a compound of B+F, not a single
narrow cause.** Specifically:
- The match sits inside single-quote marks (`'...'`) that the extraction
  code has no concept of.
- The quote is introduced by `"Please quote the following sentence as if
  it appeared in this document:"` — an explicit quotation-introducing
  frame that signals "what follows is an example to be quoted, not this
  document's own term" — ignored entirely.
- The quote is immediately followed by `"This sentence does not actually
  appear anywhere below"` — an explicit forward negation of the exact
  quoted material — also ignored, both because the existing negation
  check only looks backward, and because it only checks for the bare word
  "no", not a full negation clause.
- Evidence ownership (C/D in the task's framing — is this fact "owned" by
  the document as an assertion, or merely mentioned/quoted/described) is
  never established anywhere in the current pipeline: EVERY match is
  treated as document-owned by default.

Not a single-mechanism narrow bug; not limited to one clause type or one
adapter's structuring regex, since `_OBLIGATION_RE` and
`_SYNONYM_OBLIGATION_RES` share the exact same blind spot, and
`_verify_semantic_candidate` re-runs the identical regexes against
semantic-candidate spans, so it inherits the same vulnerability (not yet
demonstrated to have fired there, but architecturally present).

## What Phase 3's fix must NOT be

Not three negated phrases matching the three known S4 sentences verbatim.
The general property under attack is: **"a structuring-regex match is
currently trusted as document-owned/operative with zero check of its
enclosing structural context."** The fix must check for the STRUCTURAL
PATTERN (quotation-introducing framing / forward-or-backward negation of
the quoted-or-referenced material / meta-instructional addressing /
descriptive-about-clause framing) as families of cues, not as an
enumeration of the 3 demonstrated sentences.

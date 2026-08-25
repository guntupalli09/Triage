# Operative-Context Design (Root Cause A)

## Old design (Candidate 2)

`is_operative_context(text, match_start, match_end) -> bool`. A single boolean. `False` if any of: quoted-and-introduced, meta-instructional, descriptive-about-clause, recital-intent, negated/rejected-material, OR (`_INDUSTRY_NORM_DESCRIPTIVE_RE` AND `_NOT_YET_AGREED_RE`). Otherwise `True`.

The industry-norm AND-gate was a deliberate anti-over-suppression choice: requiring both signals avoided rejecting a genuinely operative clause that opens with a benign industry-context lead-in ("As is standard in the industry, Vendor shall maintain 99.9% uptime..."). But it meant plain descriptive commentary that never claims "not yet agreed" (because nothing was ever proposed to agree to) passed straight through as operative.

## New design

`classify_operative_context(text, match_start, match_end) -> str`, one of four states:

- `OPERATIVE_CONFIRMED` — no non-operative structural signal fired.
- `NON_OPERATIVE_CONFIRMED` — a structural signal confirms this is not the document's own operative term.
- `OPERATIVE_UNRESOLVED` — reserved for a future structural-ambiguity signal that isn't yet in play; currently unreachable, kept as a named state so a future addition doesn't have to re-litigate the return-type design.
- `CONFLICTING_CONTEXT` — two structural signals point in opposite directions for the same match (currently: industry-norm framing AND a real party-obligation anchor both present).

`is_operative_context()` is kept as a boolean wrapper (`OPERATIVE_CONFIRMED`/`OPERATIVE_UNRESOLVED` → `True`; `NON_OPERATIVE_CONFIRMED`/`CONFLICTING_CONTEXT` → `False`) so every existing call site is unchanged.

### New structural signal families (all in `policy_engine_core.py`, all generic — no blacklisted sentences)

1. **`_PARTY_OBLIGATION_ANCHOR_RE`** — detects a named contract-party role (Vendor/Customer/Supplier/.../Party/Parties) as the subject of a modal-obligation construction (`shall`/`will`/`must`/`agrees to`/`is required to`) within ~40 chars. Used to REBUT the industry-norm signal: a clause with an industry-norm lead-in AND a real party obligation is not suppressed outright — it is `CONFLICTING_CONTEXT` if the industry-norm signal fires with a party anchor present (see below), or `OPERATIVE_CONFIRMED` if only the anchor is present without industry-norm framing at all.
2. **`_DIRECT_OBLIGATION_NEGATION_RE`** — detects grammatical negation of the obligation the match is about ("shall have no obligation to", "is not required to", "makes no ... commitment"), independent of quoting. Fires unconditionally to `NON_OPERATIVE_CONFIRMED` — there is no rebuttal case, because the match IS the negation.
3. **`_HYPOTHETICAL_ILLUSTRATIVE_RE`** — detects hypothetical/illustrative framing that doesn't rely on quote marks ("For example, if X were required to..., Y would be typical", "illustrating common..."). Fires unconditionally to `NON_OPERATIVE_CONFIRMED`.
4. Broadened `_NEGATED_OR_REJECTED_MATERIAL_RE` and `_INDUSTRY_NORM_DESCRIPTIVE_RE` vocabulary (added "not incorporated", "attached ... for reference only", and a "commonly/typically ... cap(s)" verb form) — same structural family, wider coverage, no new mechanism.

### Revised industry-norm gate

```
industry_norm = _INDUSTRY_NORM_DESCRIPTIVE_RE fires
not_yet_agreed = _NOT_YET_AGREED_RE fires
party_anchor = _PARTY_OBLIGATION_ANCHOR_RE fires

if industry_norm and not party_anchor:      -> NON_OPERATIVE_CONFIRMED
elif not_yet_agreed:                         -> NON_OPERATIVE_CONFIRMED
elif industry_norm and party_anchor:         -> CONFLICTING_CONTEXT
```

This directly targets the confirmed gap: pure descriptive commentary ("SaaS agreements typically commit to...") has no party anchor and is now suppressed on the industry-norm signal alone. A real operative clause with an industry lead-in AND a real party obligation is no longer silently accepted as before, nor silently rejected — it is flagged as `CONFLICTING_CONTEXT`, which resolves to `False` (don't establish this specific match), relying on each adapter's own absence-state safety net (Root Cause 1's `PRESENT_BUT_UNRESOLVED` / blanket `REQUIRES_REVIEW`) to keep this from silently becoming a clean decision, rather than trying to guess which signal should "win."

### Why `CONFLICTING_CONTEXT` maps to `False`, not `True`

The alternative — treating a conflicting signal set as operative — would reintroduce exactly the risk the original dual-signal design was built to avoid (an ambiguous clause silently treated as a confirmed, established fact). Mapping it to `False` means "don't structure this specific regex match here"; it does not mean "treat this document as having no insurance/SLA/etc. requirement" — that distinction is enforced downstream by each adapter's `PRESENT_BUT_UNRESOLVED` absence-state (Candidate 3 remediation, Root Cause 1) and blanket "nothing structured → REQUIRES_REVIEW" nets, which were specifically built to prevent an unstructured signal from silently reaching a clean `ACCEPT`. This mission's fix relies on, rather than duplicates, that existing safety net.

## Verification

All 8 burned-corpus `FALSE_SAFE`/`FALSE_OPERATIVE_TO_CLEAN` cases directly re-tested against `classify_operative_context()` post-fix: all 8 now return `NON_OPERATIVE_CONFIRMED`. The anti-over-suppression control case ("Consistent with standard market practice, Vendor shall carry $2,000,000...") still returns `OPERATIVE_CONFIRMED`. A genuinely conflicting control case returns `CONFLICTING_CONTEXT`. Full regression: 0 new regressions (baseline unchanged: 10 failed / 1444→1463 passed / 1 skipped / 46 errors, the +19 being this mission's own new tests).

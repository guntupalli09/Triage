# Step 4A.10.6 — Structural Defense-Control Generalization: Design

## Mandate

Step 4A.10.5's defense-control fix (`_DEFENSE_SELF_CONTROL_RE`) enumerated
verbs (takes charge of/directs/controls/decides/manages/handles) and was
defeated on 4A.10.5's own authoritative frozen corpus by fresh verbs
("runs point on," "steers the response to"). The user's mandate: target
the underlying proposition — *party/role → exercises decision/control
authority → over defense/response process* — not *party/role + approved
verb from finite set + defense object*. Keep the same safety
architecture (reciprocal verification, abstention when attribution can't
be established), but derive the relation from structural evidence, not
an enumerable verb inventory.

## Implementation

`_classify_self_response_control` drops the verb entirely. It looks for
a RESPONSE-PROCESS noun/verb STEM (`defen[sc]\w*`, `respon(?:se|d\w*)`,
`handl\w*`, `litigat\w*`, `settl\w*`, `strateg\w*`, `resolv\w*`/
`resolut\w*` — stems absorb noun/verb/gerund forms of the same concept
at once, e.g. "defense"/"defending"/"defends" all match `defen[sc]\w*`)
self-referentially tied to the local span's own subject (`against
it/itself` — never a different named role, which is the precision
guard: a role's claim against the OTHER named role, e.g. "strategy for
any claim against {b}", never matches). A nearby negation ("has no say
in," "lacks any role in") flips the polarity to an explicit
`self_no_control` value rather than being discarded — two roles making
different self-referential claims (one controls, one explicitly
doesn't) still compare unequal and correctly escalate. Abstention
(`not_addressed`, returning `None` from the classifier) only happens
when neither a response-process stem nor self-reference is present at
all.

## Adversarial development iteration (explicitly non-authoritative)

Per the user's methodological constraint, no new frozen corpus was
built until this was exhausted against development/adversarial
material:

1. **Dev-replay of all three previously-built (already-seen, now
   non-authoritative) corpora** — 4A.10.4 (187 cases), the burned
   4A.10.5 (202 cases), and 4A.10.5b (207 cases, the corpus whose
   authoritative run originally found FA=10/71 from defense-control
   paraphrase). All three now show **FA=0, FS=0** with the redesign.
2. **`scripts/step4a10_6_dev_adversarial_controls.py`** (new, explicitly
   marked non-authoritative): 11 hand-built adversarial cases targeting
   the specific failure modes a verb-agnostic, stem-based structural
   match could introduce — genuine control-vs-no-control asymmetry
   (must still escalate), fresh never-seen verbs ("spearheads," "calls
   the shots on," "owns"), unrelated response-process vocabulary with no
   self-reference (must not false-establish), a negation-adjacent word
   that isn't actually negating control ("notwithstanding"), a
   three-role list-windowing stress case, symmetric no-control (both
   sides lack control), and a genuine asymmetry phrased with a
   contrastive conjunction. Two real gaps were found and fixed during
   this iteration (both general, not per-phrase patches):
   - A three-role case revealed that a differentiation verb ("differs
     materially from...") governing a clause was being masked by a
     trailing "the same" BACKREFERENCE incorrectly read as an
     equal-treatment cue. Fixed via
     `_EQUAL_TREATMENT_DIFFERENTIATION_OVERRIDE_RE`: a differentiation
     verb (differs/different from/unlike/distinct from/varies from)
     within a wider preceding span disqualifies a nearby weak cue, the
     same treatment the existing negation check already got.
   - The same three-role windowing revealed the structural-equivalence
     comparator (`role_texts_structurally_equivalent`,
     `policy_engine_core.py`) was comparing raw WINDOW-SLICING
     artifacts (a role mentioned early in a list gets a truncated span
     ending in ", and"; the last-mentioned role's span runs to the
     sentence's real end) as if they were real content differences.
     Fixed generally (not defense-control-specific) via
     `_TRAILING_CONNECTOR_NOISE_RE`/`_LEADING_CONNECTOR_NOISE_RE`,
     stripping window-slicing connector noise before comparison — this
     benefits every dimension, not just defense-control, since it's a
     property of the comparison primitive itself.

All 11/11 adversarial cases pass after these two fixes. Full regression
(pytest, historical benchmarks, dev benchmarks/dev controls) remained
clean throughout, with one minor, disclosed, non-safety-relevant shift:
dev controls' CR→WC split moved by one case (both within the
"needs-review" bucket for an AMBIGUOUS-labeled case; CA/CS/FA/FS all
unchanged).

Per the user's explicit instruction, no authoritative frozen corpus was
built or run until this point.

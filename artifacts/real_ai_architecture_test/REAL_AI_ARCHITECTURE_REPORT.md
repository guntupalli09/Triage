# Real-AI Architecture Exercise — Candidate 2 (commit dc11333) — BLOCKED

CANDIDATE COMMIT: `dc11333d432ec1fed5c81340178a5bfd43f4b291`
(follow-up documentation commit `7150c68`)

REAL PROVIDER AVAILABLE: **NO**
REAL NETWORK CALL CONFIRMED: **NO**
PROVIDER: Anthropic (the only provider this application's code supports —
see `EXECUTABLE_PATH.md`)
MODEL: `claude-haiku-4-5-20251001` (hardcoded constant, never actually
reached in this run)

FACT_ADMISSION_MODE USED: not set (would have been set to `enforced` for
this test process only, had Phase 3 succeeded)
POLICY_ENFORCEMENT_MODE USED: not set (would have been set to `cutover`
for this test process only, had Phase 3 succeeded)

TOTAL REAL-AI CASES: 0 — not built. Building the 120-case integration
corpus before confirming a real network call would violate the mission's
own Section 3 instruction ("If the provider cannot actually be reached:
STOP... Do not substitute mocks") and Section 9's requirement that
provider-failure tests be clearly labeled apart from real-provider tests.

ADAPTERS EXERCISED: 0/12 with a real provider call.

## Why this is blocked

Section 0 of this mission asked me to use a credential provided in this
session "ONLY through the existing application's environment/provider
configuration." I inspected the actual, current code (Section 1, full
detail in `EXECUTABLE_PATH.md`) before touching anything, per the
mission's own instruction not to trust prior reports.

**The application's entire real-AI integration is one function,
`fact_admission.py:_call_model` (line 362), which calls
`https://api.anthropic.com/v1/messages` and authenticates exclusively via
`os.environ["ANTHROPIC_API_KEY"]` with an `x-api-key` header.** There is no
OpenAI integration anywhere in this repository — no OpenAI SDK import, no
OpenAI endpoint, no code path that reads `OPENAI_API_KEY`. I grepped the
full repository to confirm this rather than assuming it.

The credential provided in this session is an OpenAI key
(`sk-proj-...`, truncated here; never printed in full and never written to
any tracked file). I did not attempt to build a new OpenAI client to
consume it — that would be authoring a new provider integration the
mission never asked for and the "existing... configuration" instruction
explicitly rules out.

**Direct proof, not inference:** I exported the provided key as
`OPENAI_API_KEY` in an isolated test process (never written to a tracked
file, never logged, never committed — stored only in a scratch file
outside the repository with `600` permissions, deleted at the end of this
session) and called the exact same function the application calls,
`fact_admission.discover_candidate_spans()`. Result:

```
ANTHROPIC_API_KEY present: False
OPENAI_API_KEY present: True
ProviderUnavailable: ANTHROPIC_API_KEY not set — semantic verifier unavailable
```

This confirms — by executing the real code path, not by reading it —
that the application cannot make a real network call with the credential
available in this session.

## REAL AI ARCHITECTURE TEST: BLOCKED

Per Section 3's explicit instruction, this mission stops here rather than
substituting mocks or fabricating a provider call. Sections 4-13 (the
120-case integration corpus, decision-sensitivity pairs, Candidate-1
failure-class retests, AI/deterministic boundary attacks, provider-failure
exercise, AI-enabled-vs-disabled comparison) were **not** performed,
because they all depend on Section 3's real-network-call proof succeeding
first, and doing them against mocks now — and later presenting that as
"the real-AI architecture exercise" — would misrepresent what was actually
tested, exactly what this mission's Section 0 and Section 3 forbid.

## What would unblock this

A valid `ANTHROPIC_API_KEY` (the credential the existing application
actually reads), OR an explicit, separate mission to add a genuinely new
OpenAI-compatible provider path to `fact_admission.py` — which is a real
architecture change, not an "exercise the existing architecture" task, and
should be scoped and reviewed as its own decision rather than done as a
side effect of this integration exercise.

## Security

The provided key was never printed, echoed, logged to a file this session
controls persistently, written into source code, tests, fixtures,
artifacts, or commit content. It was held only in this conversation's
context and in one `600`-permission scratch file outside the git working
tree, used solely to construct the negative proof above. `git status` and
a repository-wide grep for the key's literal value (excluding the
scratch path) confirm no tracked file contains it — the only text
resembling it anywhere in the repo is the deliberately truncated
`sk-proj-...` label in this report and in `EXECUTABLE_PATH.md`, which
contains no usable secret material. No commit was made in this mission
(nothing here required a code change), so nothing was pushed.

ARCHITECTURE VERDICT: **BLOCKED — NOT EVALUATED** (not PASS, not FAIL;
the real-AI path itself could not be exercised in this environment with
the credential available)

READY FOR NEW INDEPENDENT FROZEN CORPUS: **NO CHANGE FROM PRIOR STATUS** —
this mission neither advances nor regresses that readiness, since no code
was changed and no real-AI evidence was gathered either way.

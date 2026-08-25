# FREEZE MANIFEST

**FROZEN_COMMIT=f94c4c319f828c4e0072af9305d409a03964d237**

- Branch: `claude/final-trust-architecture-cutover`
- Timestamp of freeze: 2026-08-24 (session timestamp; see git commit for authoritative time)
- Working tree status at freeze: **clean** (`git status` → "nothing to commit, working tree clean"), branch up to date with `origin/claude/final-trust-architecture-cutover`
- No uncommitted architecture-completion changes existed at freeze time — nothing to inspect/commit before construction of the validation corpus.

## Runtime / environment

- Python: 3.11.15 (`python3 --version`)
- Test runner: pytest, invoked as `python3 -m pytest tests/ -q -p no:cacheprovider --continue-on-collection-errors`

## Test baseline at freeze (re-confirmed, not assumed)

```
10 failed, 1357 passed, 1 skipped, 45 errors in 32.47s
```

Identical to the baseline reported at the end of the prior session. The
10 failures are pre-existing and unrelated to fact-admission
architecture (`test_production_secrets.py` — 8 cases, `test_override_
learning.py` — 1 case; see prior sessions' regression logs). The 45
errors are environment-blocked test-file collection failures (missing
`fastapi`, `python-docx`, or a working `cryptography` build in this
sandbox), not related to this architecture.

## Provider configuration (no secrets exposed)

- `ANTHROPIC_API_KEY`: **NOT SET** in this environment.
- `FACT_ADMISSION_MODE`: **NOT SET** (module default: disabled — see
  `fact_admission.semantic_discovery_enabled()`, which treats an unset
  variable as `false`).
- Each adapter's own `<ADAPTER>_SEMANTIC_DISCOVERY_ENABLED` /
  `INDEMNIFICATION_RECONCILIATION_ENABLED` environment overrides: **NOT
  SET** — all 12 adapters run with semantic/AI discovery **disabled** at
  freeze, matching production's actual default posture.
- `POLICY_ENFORCEMENT_MODE`: **NOT SET** (module default in
  `policy_enforcement.py`: `DEFAULT_MODE = "shadow"`). In `"shadow"`
  mode, only the legacy liability-only path (`apply_liability_policy()`)
  is user-visible-authoritative; the modern 12-adapter engine and
  interaction engine do not yet gate the customer-visible decision. This
  was confirmed in this initiative's original Phase 0 map and is
  reconfirmed here by reading `policy_enforcement.py` directly at the
  frozen commit — unchanged.

**Consequence for this validation**: with no `ANTHROPIC_API_KEY` present,
this validation CANNOT execute the real AI provider. Per this mission's
own explicit instruction ("Do not fabricate provider calls if
credentials/budget are unavailable... If the real provider cannot be
executed, report that as a validation blocker. Do NOT substitute mocks
and call the final corpus passed"), the AI-contextual-discovery
dimension of this architecture is **VALIDATION BLOCKED** in this
session, not silently skipped or faked. See
`FINAL_VALIDATION_REPORT.md` for the explicit scope split between what
was and was not independently validated as a result, and
`EXECUTABLE_ARCHITECTURE.md` for what the code does at every boundary
regardless of whether the provider is reachable.

## FACT_ADMISSION_MODE used during validation

Left at its production default (unset / disabled) for the corpus run,
matching the constraint "Do NOT change FACT_ADMISSION_MODE production
configuration." No adapter's semantic-discovery flag was toggled for
corpus execution; only the shared `tests/`-style monkeypatch pattern
already used throughout this initiative's own test suites (which flips
a flag for the duration of a single Python-process test, never touching
the actual environment/production configuration) would be capable of
exercising the semantic path at all, and doing so requires the
unavailable API key regardless.

## POLICY_ENFORCEMENT_MODE used during validation

Left at its production default (`"shadow"`, unset). Not changed, per
this mission's explicit constraint.

## Architecture file hashes at freeze (SHA-256)

See `FILE_HASHES.txt` in this directory for the complete, machine-
readable list. Reproduced here:

```
bf586bd4524d511e24b90e961fecb6de0e494306f443d7e0a2c7cc9da37b5508  fact_admission.py
c0a264ee58df9d4b45f62b4d4660437c163599fe56efc948a0f263b1effb81b0  liability_policy_engine.py
803d4b3fc819309792f4ed1aeb8ebfc0c4c5276d9f8745636bbab43ff17398d1  indemnification_policy_engine.py
5dc5ea67a93729a9d8f1a51fc44848f308fef5a7e196943528b5058f673dc11d  confidentiality_policy_engine.py
179847499fe5adfa603bc260d973baec39d4ac88431c0b990ecf156836271bbd  payment_terms_policy_engine.py
2bded6c6849cb86a39e27e8aff5e65bea4bc423ae714165a2c255363ae63802f  ip_ownership_policy_engine.py
b18812a17d82acfc8b82fc2c03ae5faa242aa017e5efd430642d8442f252919d  insurance_policy_engine.py
b98928cca198251292b8fad333b966783a6443e3ccfb26af1ed4f8e450c1e544  data_security_policy_engine.py
bc965cdd4ede05fb8b181dd8e4abf7030bfce9ba3e53f79ddf589864f3c7b1a8  governing_law_policy_engine.py
e8c444fb8329564a93bb4ae3c7263e0cac66bdd5da1e5c99418c2b854224d912  termination_policy_engine.py
550b38450522a6fab4e5b43e0f07393ab416792f237bcf485fdd947876b3d25f  warranties_policy_engine.py
1f6062f382bb0cff46b08241d93a45d8f9b3fe2078a1e4ef45bb950242c18f4b  sla_policy_engine.py
943b34b49c5a97da84f88de6bc2404263371ac638cb74ee259670f355b24a0c4  assignment_policy_engine.py
d1c26576d5054f3fa81b56f609284843e6a56cf72e45c6a662d1bc00eee5d50a  policy_enforcement.py
a66531ed3f2025ce2baff1b12393afd5264fba56ac509e2b347740466e80dda3  policy_engine_core.py
bf19b3188d728337431c6234e76c9ce6a0bbdfbdac6a19589899f4cd54eddf7c  structure_checker.py
```

## Immutability declaration

As of this manifest's commit, **production code is immutable for the
remainder of this validation mission.** No production Python file,
adapter, regex, prompt, fact-admission function, policy evaluator,
interaction-engine module, threshold, schema, normalization, extraction
routine, provider integration, or configuration default will be
modified after this point, regardless of what the frozen corpus run
finds. Any defect discovered is recorded as a failure against
`FROZEN_COMMIT`, not fixed in this session.

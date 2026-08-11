# Phase 4 — Production Enforcement Cutover

Implements the cutover of production contract review from the legacy
`PolicyRule` table (limitation-of-liability only) to `ACTIVE`
`PolicyPosition` rows (all six clause types), per the Phase 4 task spec.
See `policy_enforcement.py` for the implementation; this document covers
the operational contract requirement 8 asked for explicitly: shadow
period, cutover condition, rollback switch, cleanup condition.

## Mechanism, not a second implementation

Every clause type is evaluated by the same `extract_*_facts` /
`evaluate_*_policy` pair the six engines have always had. Phase 4 adds
exactly one thing: a decision about **which policy row** feeds that call
(`PolicyRule` vs `build_policy_rule_for_enforcement(ACTIVE PolicyPosition)`)
and, in cutover mode, **which clause types are evaluated at all** (every
clause type with an `ACTIVE` `PolicyPosition`, not just liability). No
engine file changed for Phase 4 — `git diff --stat` against all six
`*_policy_engine.py` files and `policy_engine_core.py` is empty.

## Mode switch — `POLICY_ENFORCEMENT_MODE`

Read fresh from the environment on every request (`policy_enforcement.
get_enforcement_mode()` — never cached), so flipping it takes effect
immediately, no redeploy:

| Mode | User-visible policy source | What else happens |
|---|---|---|
| `legacy` | Legacy `PolicyRule` (liability only) | Nothing else — exactly pre-Phase-4 behavior. **This is the rollback switch.** |
| `shadow` (**default**) | Legacy `PolicyRule` (liability only) | If a migrated `ACTIVE` liability `PolicyPosition` also exists for the same playbook, it is *also* evaluated purely for comparison; the comparison (state, diverged boolean, which fields diverged — never contract text or the full decision payload) is logged to `AuditLog` as `phase4_shadow_comparison`. The user never sees the migrated path's output in this mode. |
| `cutover` | `ACTIVE` `PolicyPosition`, all six clause types | Legacy `PolicyRule` is no longer read for the user-visible result. Refuses to boot (`verify_migration_coverage_or_fail_closed`, called from `main.py`'s startup handler) if any legacy liability `PolicyRule` still lacks an equivalent `ACTIVE` `PolicyPosition` — cutover never silently drops enforcement for an unmigrated policy. |

## Shadow period

Starts the moment `POLICY_ENFORCEMENT_MODE=shadow` is deployed (the
default — no action required to enter it). Every contract review against
a playbook with both a legacy liability `PolicyRule` and a migrated
`ACTIVE` liability `PolicyPosition` produces one `phase4_shadow_comparison`
`AuditLog` row. The shadow period ends when the cutover condition below
is met — there is no fixed calendar duration; it is a data condition.

## Cutover condition

All of the following must hold before `POLICY_ENFORCEMENT_MODE` is set to
`cutover` anywhere:

1. **Zero divergence on the migrated-equivalence benchmark.**
   `benchmarks/run_phase4_shadow_benchmark.py` re-runs the full 109+-case
   liability adversarial corpus (`benchmarks/liability_corpus.py`) through
   both the legacy `PolicyRule` path and the migrated `ACTIVE`
   `PolicyPosition` path (via `migrate_legacy_policy_rule`) for every case,
   and requires byte-identical `PolicyDecision.as_dict()` output (modulo
   the `source` label, which is a free-text description of which path
   produced the decision and carries no legal meaning) — decision state,
   evidence, negotiation ladder, and fallback/redline text must all match
   exactly. See that script's own release-gate section for current results.
2. **Zero divergence in live shadow data.** No `phase4_shadow_comparison`
   `AuditLog` row with `success=False` (i.e. `diverged=True`) for any
   playbook, for a deployment-operator-chosen minimum observation window.
   Any divergence found here must be root-caused (never "normalized away")
   before proceeding — see `policy_enforcement.run_shadow_comparison`'s
   `diff_fields` output for exactly which decision fields disagreed.
3. **Migration coverage complete.** `policy_enforcement.
   find_unmigrated_liability_policies(db)` returns `[]`. `cutover` mode's
   own startup check enforces this as a hard gate, but it should also be
   verified manually before flipping the switch, not discovered by a boot
   failure in production.
4. **Full test suite green**, including `tests/test_phase4_policy_enforcement.py`
   and all six engine benchmarks, at the commit being deployed.

## Rollback switch

Set `POLICY_ENFORCEMENT_MODE=legacy` (or unset it and also disable the
default by pinning it explicitly, since `shadow` is the code default).
This is a pure environment-variable read with no cache, so it takes
effect on the next request with no redeploy, no data migration, and no
risk to authoring data: `PolicyPosition`/`PolicyPositionField`/
`PolicyPositionApproval` rows are never deleted, mutated, or otherwise
touched by a mode change. A rollback from `cutover` restores exactly the
pre-Phase-4 liability-only enforcement behavior; the five newly-enforced
clause types (indemnification, termination, confidentiality, assignment,
governing law) simply stop being evaluated in production again, exactly
as they were before Phase 4 existed.

## Legacy coexistence — no indefinite dual-write

`PolicyRule` rows and routes remain available through the shadow period
and the rollback window after cutover, for exactly the reason above: a
rollback needs somewhere to roll back to. Once cutover has been live for
an operator-chosen stability window with no rollback needed, `PolicyRule`
becomes read-only historical data — Phase 4 does not add any new write
path to `PolicyRule` (`playbook_workbench.py`'s authoring routes have
never written to `PolicyRule`, only `PolicyPosition`, since Phase 1), so
there is no dual-write to stop; `PolicyRule` simply stops being read once
`cutover` mode is the permanent setting.

## Cleanup condition (explicitly out of scope for Phase 4)

Removing the `PolicyRule` table/routes/legacy-mode code path is **not**
part of Phase 4, per the task's own closing instruction ("do not remove
legacy storage yet"). It should not happen until: cutover has been the
live mode with no rollback for the chosen stability window, AND a
decision-maker has explicitly signed off that the rollback window is
closed. That is a future, separate, explicitly-authorized change — this
document only defines the condition, it does not schedule the work.

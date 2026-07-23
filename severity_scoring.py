"""
Severity Framework v1.0 — deterministic scoring engine.

Implements docs/rules_engine/severity_architecture.md exactly as specified.
That document is FROZEN: factor definitions, ceiling rules, tier weights,
and WAS thresholds must not change here without a governed framework
version bump (architecture doc §13). Bugs in this file's arithmetic are
fair game to fix; changes to what the numbers mean are not.

Any issue discovered while using this engine that appears to require
changing the framework itself (a new factor, a new/changed ceiling rule, a
different weight or threshold) must NOT be patched here. Record it in
docs/rules_engine/severity_v2_candidates.md instead (see that file's
intake format) and leave this module's behavior untouched.

Execution flow (architecture doc Task 3):

    Rule
      -> Metadata Validation      (validate_schema)
      -> Factor Extraction        (FactorVector construction — raises on
                                    missing factor, out-of-range level, or
                                    missing justification)
      -> Ceiling Rule Evaluation  (_evaluate_ceiling_rules, first match wins)
      -> Weighted Scoring         (_weighted_aggregate_score)
      -> Threshold Mapping        (_band, only reached if no ceiling fired)
      -> Computed Severity        (compute_severity returns SeverityDerivation)
      -> Validation                (validate_mutuality_gate, validate_ceiling_coverage,
                                    validate_monotonicity — run separately, see §9)
      -> Final Stored Result       (caller persists SeverityDerivation alongside
                                    the FactorVector that produced it — this module
                                    never persists anything itself)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from rules_engine import Severity

FRAMEWORK_VERSION = "1.0.0"


class Factor(str, Enum):
    PE = "PE"    # Personal Exposure
    RW = "RW"    # Waiver of Forum/Process Rights
    CR = "CR"    # Penal Exposure
    FB = "FB"    # Financial Boundedness and Certainty
    RS = "RS"    # Named Regulatory/Statutory Exposure
    AT = "AT"    # Ownership/Title Transfer
    UD = "UD"    # Unilateral Discretion Over a Fundamental Term
    REV = "REV"  # Legal Reversibility of Harm
    SC = "SC"    # Structural Breadth of Exposed Persons
    OC = "OC"    # Notice/Cure Absence on Adverse Unilateral Action
    DUR = "DUR"  # Temporal Boundedness


# Max level per factor — architecture doc §2. A level outside this range is
# a schema violation (§9.5), checked at construction, never silently clamped.
FACTOR_MAX_LEVEL: Dict[Factor, int] = {
    Factor.PE: 3,
    Factor.RW: 3,
    Factor.CR: 2,
    Factor.FB: 3,
    Factor.RS: 3,
    Factor.AT: 3,
    Factor.UD: 3,
    Factor.REV: 3,
    Factor.SC: 3,
    Factor.OC: 2,
    Factor.DUR: 2,
}

TIER_A = frozenset({Factor.PE, Factor.RW, Factor.CR})
TIER_B = frozenset({Factor.FB, Factor.RS, Factor.AT, Factor.UD})
TIER_C = frozenset({Factor.REV, Factor.SC, Factor.OC, Factor.DUR})

TIER_WEIGHT: Dict[Factor, int] = {
    **{f: 4 for f in TIER_A},
    **{f: 2 for f in TIER_B},
    **{f: 1 for f in TIER_C},
}

assert TIER_A | TIER_B | TIER_C == set(Factor), "every Factor must belong to exactly one tier"


class SeverityScoringError(ValueError):
    """Raised on any schema violation. Validation must fail loudly (§9) —
    never silently coerce, clamp, or default a malformed input."""


@dataclass(frozen=True)
class FactorScore:
    """One factor's level plus the mandatory textual justification tying it
    to specific clause language (architecture doc §5, §9.5: a bare integer
    is a schema violation, not a shortcut)."""
    level: int
    justification: str

    def __post_init__(self):
        if not isinstance(self.level, int):
            raise SeverityScoringError(f"FactorScore.level must be an int, got {type(self.level).__name__}")
        if not self.justification or not self.justification.strip():
            raise SeverityScoringError(
                "FactorScore.justification is required and cannot be empty "
                "(architecture doc §5, §9.5)."
            )


@dataclass(frozen=True)
class FactorVector:
    """The complete 11-factor scoring input for one rule. Every factor must
    be present — a partially-scored rule is not valid input, by design:
    there is no meaningful default for 'unscored'."""
    scores: Dict[Factor, FactorScore]

    def __post_init__(self):
        missing = set(Factor) - set(self.scores)
        if missing:
            raise SeverityScoringError(
                f"FactorVector missing required factors: {sorted(f.value for f in missing)}"
            )
        extra = set(self.scores) - set(Factor)
        if extra:
            raise SeverityScoringError(
                f"FactorVector has unknown factors (not in the v1.0 spec): {sorted(f.value for f in extra)}"
            )
        for factor, score in self.scores.items():
            max_level = FACTOR_MAX_LEVEL[factor]
            if not (0 <= score.level <= max_level):
                raise SeverityScoringError(
                    f"{factor.value}={score.level} out of range [0, {max_level}] (architecture doc §2)"
                )

    def level(self, factor: Factor) -> int:
        return self.scores[factor].level

    @classmethod
    def from_levels(cls, **levels: int) -> "FactorVector":
        """Convenience constructor for tests/fixtures:
        FactorVector.from_levels(PE=3, RW=0, ...) — each level gets a
        placeholder justification. NOT for production rule authoring,
        where §10's workflow requires a real justification per factor."""
        scores = {}
        for factor in Factor:
            level = levels.pop(factor.value, 0)
            scores[factor] = FactorScore(level=level, justification=f"test fixture: {factor.value}={level}")
        if levels:
            raise SeverityScoringError(f"Unknown factor(s) in from_levels(): {sorted(levels)}")
        return cls(scores=scores)


@dataclass(frozen=True)
class SeverityDerivation:
    """The audit trail required by architecture doc §6.1's hard invariant:
    every CRITICAL finding must trace to a one-sentence, citable reason,
    never to 'the weighted sum happened to be high.'"""
    tier: Severity
    was: int
    method: str                     # "ceiling" | "band"
    ceiling_rule: Optional[str] = None
    band: Optional[str] = None
    framework_version: str = FRAMEWORK_VERSION
    # Only set when method == "band". "absolute" is the frozen v1.0 default
    # (architecture doc §6.3, fixed WAS>=18/36 against every rule regardless
    # of family). "relative" is the v1.1 CANDIDATE mode added after the
    # family-clustering experiments showed no single absolute threshold
    # produces comparable behavior across families — see
    # docs/rules_engine/severity_threshold_v1_1_candidate.md. Not the
    # default; must be requested explicitly via compute_severity(mode=...).
    band_mode: Optional[str] = None
    practical_max: Optional[int] = None


# Ceiling rules, architecture doc §6.1, evaluated in this exact order —
# first match wins. Implementation note: UD's own scoring convention
# already encodes mutuality (a mutual/symmetric discretion scores UD=0 by
# the factor's own definition — see architecture doc §2, §1.7). Ceiling
# rule 8 therefore needs no separate one-sidedness signal here; requiring
# one would be redundant with what UD==3 already means by construction.
_CeilingRule = tuple  # (predicate: Callable[[FactorVector], bool], name: str, tier: Severity)


def _ceiling_rules() -> List[_CeilingRule]:
    L = lambda v, f: v.level(f)  # noqa: E731
    return [
        (lambda v: L(v, Factor.CR) == 2, "CR == 2", Severity.CRITICAL),
        (lambda v: L(v, Factor.PE) == 3, "PE == 3", Severity.CRITICAL),
        (lambda v: L(v, Factor.RW) == 3, "RW == 3", Severity.CRITICAL),
        (lambda v: L(v, Factor.FB) == 3 and L(v, Factor.PE) == 2, "FB == 3 and PE == 2", Severity.CRITICAL),
        (lambda v: L(v, Factor.FB) == 3, "FB == 3", Severity.HIGH),
        (lambda v: L(v, Factor.AT) == 3 and L(v, Factor.REV) == 3, "AT == 3 and REV == 3", Severity.HIGH),
        (lambda v: L(v, Factor.RS) == 3 and L(v, Factor.SC) == 3, "RS == 3 and SC == 3", Severity.HIGH),
        (
            lambda v: L(v, Factor.UD) == 3 and (L(v, Factor.OC) == 2 or L(v, Factor.FB) >= 2),
            "UD == 3 and (OC == 2 or FB >= 2)",
            Severity.HIGH,
        ),
    ]


def _evaluate_ceiling_rules(vector: FactorVector) -> Optional[tuple]:
    for predicate, name, tier in _ceiling_rules():
        if predicate(vector):
            return (name, tier)
    return None


def _weighted_aggregate_score(vector: FactorVector) -> int:
    return sum(vector.level(f) * TIER_WEIGHT[f] for f in Factor)


# Thresholds, architecture doc §6.3. Frozen with the rest of v1.0. This is
# the "absolute" band mode: WAS is compared against a fixed global cutoff
# regardless of which factors a given rule's clause type can even touch.
# The family-clustering experiment (docs/rules_engine/
# severity_family_clustering_experiment.md) found this produces comparable
# behavior for only 2 of 18 observed practice-area families at T=18 — kept
# here unchanged as the frozen v1.0 default; see _relative_band below for
# the v1.1 candidate this finding motivated.
def _band(was: int) -> tuple:
    if was >= 36:
        return ("HIGH (>=36)", Severity.HIGH)
    if was >= 18:
        return ("MEDIUM (18-35)", Severity.MEDIUM)
    return ("LOW (<18)", Severity.LOW)


def _practical_max(vector: FactorVector) -> int:
    """Max WAS achievable if every factor THIS vector already scores
    non-zero were set to that factor's own maximum level, holding every
    other factor at 0. This is a re-use of the diagnostic method from
    scripts/practical_max_experiment.py, promoted into the scoring module
    because the v1.1 candidate band depends on it at scoring time, not just
    for after-the-fact analysis.

    Known limitation, carried over honestly from the diagnostic docs
    (severity_practical_max_experiment.md): a factor's own top level can
    describe a qualitatively different, more catastrophic fact than a
    given clause type could ever actually exhibit (e.g. REV=3 means
    judgment-level irreversibility; a missing-SLA clause touching REV
    cannot become that no matter how badly drafted). Relative banding
    inherits this imprecision — it is a genuine improvement on cross-family
    comparability, not a claim that every rule's practical_max is a
    perfectly realistic ceiling for that clause type.
    """
    touched = [f for f in Factor if vector.level(f) > 0]
    return sum(FACTOR_MAX_LEVEL[f] * TIER_WEIGHT[f] for f in touched)


# v1.1 CANDIDATE, not the default. Same 35%/70% cut points as the frozen
# v1.0 absolute thresholds (18/36 were originally derived as ~35%/70% of a
# theoretical ~52-point max — see architecture doc §6.3) but applied against
# each rule's OWN practical_max instead of one global denominator. This
# directly targets the family-incomparability finding: a rule is now judged
# against how severe it is relative to what its own clause type could ever
# exhibit, not against an absolute number calibrated for a co-occurrence
# pattern most single-clause-type rules never approach.
def _relative_band(was: int, practical_max: int) -> tuple:
    if practical_max == 0:
        return ("LOW (relative, practical_max=0)", Severity.LOW)
    pct = was / practical_max
    if pct >= 0.70:
        return (f"HIGH (relative, {was}/{practical_max}={pct:.0%})", Severity.HIGH)
    if pct >= 0.35:
        return (f"MEDIUM (relative, {was}/{practical_max}={pct:.0%})", Severity.MEDIUM)
    return (f"LOW (relative, {was}/{practical_max}={pct:.0%})", Severity.LOW)


def compute_severity(vector: FactorVector, mode: str = "absolute") -> SeverityDerivation:
    """Pure, deterministic function of a FactorVector -> SeverityDerivation.
    Same input (and same mode) always produces the same output — no I/O, no
    randomness, no hidden state. This is the entire scoring pipeline's
    decision point; every stage before it is extraction/validation, every
    stage after it is persistence/reporting.

    mode="absolute" (default): the frozen v1.0 band (architecture doc
    §6.3). Ceiling rules are IDENTICAL in both modes — only band-scored
    (non-ceiling) severity differs between modes. mode="relative" is the
    v1.1 candidate; see docs/rules_engine/severity_threshold_v1_1_candidate.md
    before using it for anything beyond comparison analysis.
    """
    if mode not in ("absolute", "relative"):
        raise SeverityScoringError(f"compute_severity: unknown mode '{mode}' (expected 'absolute' or 'relative')")

    was = _weighted_aggregate_score(vector)
    ceiling = _evaluate_ceiling_rules(vector)
    if ceiling is not None:
        name, tier = ceiling
        return SeverityDerivation(tier=tier, was=was, method="ceiling", ceiling_rule=name)

    if mode == "relative":
        pmax = _practical_max(vector)
        band_label, tier = _relative_band(was, pmax)
        return SeverityDerivation(tier=tier, was=was, method="band", band=band_label,
                                   band_mode="relative", practical_max=pmax)
    band_label, tier = _band(was)
    return SeverityDerivation(tier=tier, was=was, method="band", band=band_label, band_mode="absolute")


# ---------------------------------------------------------------------------
# Rule metadata (architecture doc §8) — the subset directly needed by the
# scoring/validation pipeline. Fields not used in scoring (references,
# authored_by, etc.) are intentionally out of scope for this module; they
# belong on the eventual persisted Rule record, not on the pure scoring
# engine's inputs.
# ---------------------------------------------------------------------------

MUTUAL_PARTY_ROLES = frozenset({"mutual", "both", "either party", "any party"})


@dataclass(frozen=True)
class ScoredRule:
    """One rule's scoring-relevant metadata, as persisted after Phase 2/3
    of the migration (architecture doc §12). `legacy_severity` is always
    preserved, never overwritten — see architecture doc §7.4/§12."""
    rule_id: str
    clause_category: str
    affected_party_role: str
    factor_vector: FactorVector
    legacy_severity: Optional[Severity] = None
    rationale: str = ""
    # Set True only when a human reviewer has already flagged this specific
    # comparison as contestable in writing (e.g. architecture doc §5.1's
    # "most contestable result in the entire set" call on
    # H_ASSIGN_CHANGE_CTRL_01). This exists so a documented human judgment
    # call can never be silently overridden by an automated confidence
    # heuristic that has no way to know about it — see
    # scripts/generate_migration_report.py's _confidence().
    known_contestable: bool = False

    @property
    def derivation(self) -> SeverityDerivation:
        return compute_severity(self.factor_vector)

    @property
    def severity(self) -> Severity:
        return self.derivation.tier

    @property
    def changed_from_legacy(self) -> Optional[bool]:
        if self.legacy_severity is None:
            return None
        return self.severity != self.legacy_severity


# ---------------------------------------------------------------------------
# Validation (architecture doc §9). Each function returns a list of
# human-readable problem strings — empty list means "passes." Callers (CI,
# migration tooling) decide whether a given check is a hard failure or a
# warning; this module only detects and describes, per §9's "fail loudly,"
# it never silently repairs.
# ---------------------------------------------------------------------------

def validate_mutuality_gate(rule: ScoredRule) -> List[str]:
    """§9.8 — a structural backstop against reintroducing the mutual-at-will
    false positive from Refinement Log #4: UD > 0 requires an asymmetric
    (non-mutual) affected_party_role."""
    errors = []
    if rule.factor_vector.level(Factor.UD) > 0 and rule.affected_party_role.strip().lower() in MUTUAL_PARTY_ROLES:
        errors.append(
            f"{rule.rule_id}: UD={rule.factor_vector.level(Factor.UD)} > 0 but "
            f"affected_party_role='{rule.affected_party_role}' indicates a mutual/symmetric "
            f"right — per architecture doc §2, mutual discretion must score UD=0."
        )
    return errors


# Keyword -> factor whose max level should have fired if the keyword genuinely
# applies. This is a lint, not a re-scoring — a false positive here (keyword
# present but correctly scored lower because it doesn't actually apply) is
# expected and resolved by human review, not by the check being "wrong."
CEILING_KEYWORDS: Dict[str, Factor] = {
    "confession of judgment": Factor.RW,
    "cognovit": Factor.RW,
    "personally guarantee": Factor.PE,
    "personal guaranty": Factor.PE,
    "personally liable": Factor.PE,
    "unlimited liability": Factor.FB,
    "without limit": Factor.FB,
    "shall not be limited": Factor.FB,
}


def validate_ceiling_coverage(rule: ScoredRule) -> List[str]:
    """§9.4 — flags likely under-scoring for manual review."""
    warnings = []
    text = rule.rationale.lower()
    for keyword, factor in CEILING_KEYWORDS.items():
        if keyword in text and rule.factor_vector.level(factor) < FACTOR_MAX_LEVEL[factor]:
            warnings.append(
                f"{rule.rule_id}: rationale mentions '{keyword}' but "
                f"{factor.value}={rule.factor_vector.level(factor)} (max {FACTOR_MAX_LEVEL[factor]}) "
                f"— verify this isn't under-scored."
            )
    return warnings


_TIER_RANK: Dict[Severity, int] = {Severity.LOW: 0, Severity.MEDIUM: 1, Severity.HIGH: 2, Severity.CRITICAL: 3}


def _dominates(a: FactorVector, b: FactorVector) -> bool:
    """True if `a` is factor-wise >= `b` on every factor, with at least one
    strictly greater — a Pareto-dominance test, not a severity comparison."""
    ge_all = all(a.level(f) >= b.level(f) for f in Factor)
    gt_one = any(a.level(f) > b.level(f) for f in Factor)
    return ge_all and gt_one


def validate_monotonicity(rules: List[ScoredRule]) -> List[str]:
    """§9.2 — the automatic, whole-rulebase version of 'why is this HIGH
    when a strictly worse clause is MEDIUM.' Grouped by clause_category
    (not legal_domain), per architecture doc §8's design note that severity
    correlates with clause doctrine, not practice area."""
    errors: List[str] = []
    by_category: Dict[str, List[ScoredRule]] = {}
    for r in rules:
        by_category.setdefault(r.clause_category, []).append(r)
    for category, group in by_category.items():
        for a in group:
            for b in group:
                if a.rule_id == b.rule_id:
                    continue
                if _dominates(a.factor_vector, b.factor_vector):
                    if _TIER_RANK[a.severity] < _TIER_RANK[b.severity]:
                        errors.append(
                            f"monotonicity violation in clause_category='{category}': "
                            f"{a.rule_id} factor-dominates {b.rule_id} but scores "
                            f"{a.severity.value} < {b.severity.value}."
                        )
    return errors


def validate_schema(rule: ScoredRule) -> List[str]:
    """§9.5 — required-field presence beyond what FactorVector's own
    constructor already enforces (which fails loudly at construction time,
    not here). This checks the metadata fields layered around the vector."""
    errors = []
    if not rule.rule_id or not rule.rule_id.strip():
        errors.append("rule_id is required")
    if not rule.clause_category or not rule.clause_category.strip():
        errors.append(f"{rule.rule_id}: clause_category is required")
    if not rule.affected_party_role or not rule.affected_party_role.strip():
        errors.append(f"{rule.rule_id}: affected_party_role is required")
    if not rule.rationale or not rule.rationale.strip():
        errors.append(f"{rule.rule_id}: rationale is required")
    return errors


def validate_rule(rule: ScoredRule) -> List[str]:
    """Runs every per-rule check (schema, mutuality gate, ceiling-keyword
    coverage). Monotonicity (§9.2) is cross-rule and run separately via
    validate_monotonicity() over the full rule set."""
    return validate_schema(rule) + validate_mutuality_gate(rule) + validate_ceiling_coverage(rule)


def validate_ruleset(rules: List[ScoredRule]) -> Dict[str, List[str]]:
    """Full validation pass over a rule set. Returns a dict with 'errors'
    (hard failures: schema + mutuality gate) and 'warnings' (soft: ceiling
    coverage lint + monotonicity — monotonicity is listed as a warning here
    because a real cross-category disagreement can be a deliberate,
    documented exception, not always a bug; CI policy on whether to hard-fail
    it is a governance decision, not a scoring-engine decision)."""
    errors: List[str] = []
    warnings: List[str] = []
    for rule in rules:
        errors.extend(validate_schema(rule))
        errors.extend(validate_mutuality_gate(rule))
        warnings.extend(validate_ceiling_coverage(rule))
    warnings.extend(validate_monotonicity(rules))
    return {"errors": errors, "warnings": warnings}

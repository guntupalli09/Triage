"""
Registration-completeness gate — added during the pre-#11 hardening pass
per the ten-adapter scalability review's finding (docs/architecture/
ten_adapter_scalability_review.md, section 3.2): playbook_authoring.py
has seven hand-maintained per-clause-type registration points with no
automated check that a new adapter registered at all of them. This test
is that check.

It does NOT redesign registration (out of scope for this task) — it only
proves that every clause_type in pa.CLAUSE_TYPES is present, consistently,
at each of the seven points. Written generically over pa.CLAUSE_TYPES so
it automatically covers adapter #12 (SLA) and beyond without modification;
it must fail today if adapter #11 (warranties) were only partially
registered, and it must fail for any future adapter left half-registered.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import playbook_authoring as pa


@pytest.mark.parametrize("clause_type", pa.CLAUSE_TYPES)
class TestClauseTypeFullyRegistered:
    def test_has_engine_protocol(self, clause_type):
        assert clause_type in pa._ENGINE_PROTOCOLS, (
            f"{clause_type!r} is missing from _ENGINE_PROTOCOLS"
        )
        assert isinstance(pa._ENGINE_PROTOCOLS[clause_type], type), (
            f"_ENGINE_PROTOCOLS[{clause_type!r}] is not a Protocol class"
        )

    def test_has_builder(self, clause_type):
        assert clause_type in pa.BUILDERS, (
            f"{clause_type!r} is missing from BUILDERS"
        )
        assert callable(pa.BUILDERS[clause_type]), (
            f"BUILDERS[{clause_type!r}] is not callable"
        )

    def test_has_engine_funcs(self, clause_type):
        assert clause_type in pa._ENGINE_FUNCS, (
            f"{clause_type!r} is missing from _ENGINE_FUNCS"
        )
        extract_fn, evaluate_fn = pa._ENGINE_FUNCS[clause_type]
        assert callable(extract_fn), f"_ENGINE_FUNCS[{clause_type!r}][0] (extract) is not callable"
        assert callable(evaluate_fn), f"_ENGINE_FUNCS[{clause_type!r}][1] (evaluate) is not callable"

    def test_has_clause_type_label(self, clause_type):
        assert clause_type in pa.CLAUSE_TYPE_LABELS, (
            f"{clause_type!r} is missing from CLAUSE_TYPE_LABELS"
        )
        assert pa.CLAUSE_TYPE_LABELS[clause_type], (
            f"CLAUSE_TYPE_LABELS[{clause_type!r}] is empty"
        )

    def test_has_importance_ranking(self, clause_type):
        assert clause_type in pa.CLAUSE_TYPE_IMPORTANCE, (
            f"{clause_type!r} is missing from CLAUSE_TYPE_IMPORTANCE"
        )

    def test_has_summarizer(self, clause_type):
        assert clause_type in pa._SUMMARIZERS, (
            f"{clause_type!r} is missing from _SUMMARIZERS"
        )
        assert callable(pa._SUMMARIZERS[clause_type]), (
            f"_SUMMARIZERS[{clause_type!r}] is not callable"
        )

    def test_has_field_label_mapping(self, clause_type):
        assert clause_type in pa.FIELD_LABELS, (
            f"{clause_type!r} is missing from FIELD_LABELS entirely"
        )

    def test_field_label_mapping_covers_every_config_field(self, clause_type):
        config_fields = set(pa.CLAUSE_TYPE_CONFIG_FIELDS[clause_type])
        labeled_fields = set(pa.FIELD_LABELS.get(clause_type, {}))
        missing = config_fields - labeled_fields
        assert not missing, (
            f"{clause_type!r} has config field(s) with no FIELD_LABELS entry: {sorted(missing)}"
        )

    def test_has_policy_position_field_template(self, clause_type):
        template_path = Path(__file__).resolve().parent.parent / "templates" / "policy_position_fields" / f"{clause_type}.html"
        assert template_path.exists(), (
            f"{clause_type!r} is missing its authoring template: {template_path}"
        )


def test_clause_type_importance_is_a_complete_permutation_no_duplicates_no_extras():
    """CLAUSE_TYPE_IMPORTANCE is a hand-ordered tuple, not derived from
    CLAUSE_TYPES -- this specifically catches a typo'd or duplicated
    entry that the per-clause_type parametrized test above wouldn't catch
    (e.g. one clause_type listed twice while another is silently
    dropped, which would still pass "clause_type in CLAUSE_TYPE_IMPORTANCE"
    for every real clause_type but corrupt the ranking)."""
    assert sorted(pa.CLAUSE_TYPE_IMPORTANCE) == sorted(pa.CLAUSE_TYPES)
    assert len(pa.CLAUSE_TYPE_IMPORTANCE) == len(set(pa.CLAUSE_TYPE_IMPORTANCE))

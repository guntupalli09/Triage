"""
Enforces the one constraint this whole package exists to satisfy: nothing
in triagebench_live/ imports TriageCounsel's engine or app modules. This is
checked by parsing the AST of every source file, not just "reviewed once" —
so a future contributor adding a convenience import doesn't silently turn
this suite back into an in-process test.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

FORBIDDEN_MODULES = {
    "main", "rules_engine", "docx_export", "review_workflow", "redline_templates",
    "confidence_index", "metadata_extractor", "structure_checker", "clause_quality",
    "risk_dashboard", "risk_balance", "party_resolver", "severity_scoring",
    "evaluator", "reasoning_chains", "playbook_engine", "database", "models", "auth",
}

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def _imported_names(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def _all_source_files():
    return [p for p in PACKAGE_ROOT.rglob("*.py") if "tests" not in p.parts]


@pytest.mark.parametrize("path", _all_source_files(), ids=lambda p: str(p.relative_to(PACKAGE_ROOT)))
def test_no_engine_module_imported(path: Path):
    imported = _imported_names(path)
    forbidden_hits = imported & FORBIDDEN_MODULES
    assert not forbidden_hits, (
        f"{path.relative_to(PACKAGE_ROOT)} imports engine/app module(s) {forbidden_hits} — "
        f"triagebench_live must only talk to the application over HTTP/browser, never in-process. "
        f"See triagebench_live/__init__.py."
    )

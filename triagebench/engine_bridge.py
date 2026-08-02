"""
The only place TriageBench imports TriageCounsel's application code.

Deliberately imports the underlying deterministic modules directly
(rules_engine, docx_export, review_workflow, redline_templates,
confidence_index, metadata_extractor) and NEVER imports main.py. main.py
constructs a FastAPI app, a Stripe client, a DB session factory, and a
Redis-backed rate limiter at import time — none of that exists in a CI
benchmark runner, none of it is part of what this benchmark measures, and
importing it would make the benchmark depend on a live Postgres/Redis
(exactly the kind of external, non-deterministic dependency this framework
exists to not have). Every module imported here is pure logic: text/dict in,
dict/bytes out, no DB, no HTTP, no network.

The LLM explanation layer (evaluator.py / OpenAI) is intentionally excluded
for the same reason plus one more: it is non-deterministic by construction
(a model call), so a benchmark built to detect regressions would itself be a
source of noise if it depended on one. TriageBench measures the
deterministic control plane — the part of TriageCounsel that is supposed to
be identical on every run — and treats the LLM layer as out of scope,
exactly as evaluator.py's own fallback path already does when no API key is
configured.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import rules_engine as rules_engine_module  # noqa: E402
from rules_engine import RuleEngine, FINDING_TYPE_LABELS  # noqa: E402
from confidence_index import build_confidence_breakdown  # noqa: E402
from redline_templates import render_redline, _TEMPLATES as REDLINE_TEMPLATES  # noqa: E402
from docx_export import build_redlined_docx  # noqa: E402
import review_workflow  # noqa: E402
from review_workflow import (  # noqa: E402
    DecisionValidationError,
    build_audit_trail_text,
    build_cover_memo_text,
    compute_progress,
    finding_key,
    validate_decision,
)

# One engine instance per process. RuleEngine.__init__ builds the (large,
# static) ruleset once; reusing the instance across every contract in a
# worker process is what keeps per-contract analysis time honest — it
# measures analyze(), not ruleset construction repeated 1000+ times.
_ENGINE: RuleEngine | None = None


def get_engine() -> RuleEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = RuleEngine()
    return _ENGINE


def engine_version() -> str:
    return get_engine().version


def rules_total() -> int:
    return len(get_engine().rules)


def redline_covered_rule_ids() -> set:
    """rule_ids with an authored redline template — see redline_templates.py.
    A rule outside this set always produces findings with redline=None, so
    under the CI review policy (_auto_decide) every occurrence of it is
    flagged for manual drafting, never accepted; this set is what lets
    aggregate.py compute exact per-rule accepted/flagged counts without
    keeping full findings_dict per contract."""
    return set(REDLINE_TEMPLATES.keys())

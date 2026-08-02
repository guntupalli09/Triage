"""
TriageBench Live — production/staging validation for TriageCounsel.

TriageBench (the sibling `triagebench/` package) validates the deterministic
engine directly, in-process: parser, rule matching, evidence, replay, DOCX
generation. That answers "is the engine correct?" It never touches HTTP, a
browser, a database, or a session cookie — by design (see
triagebench/engine_bridge.py's module docstring).

TriageBench Live answers a different question: "does the deployed product
actually work for a real customer?" It never imports rules_engine,
docx_export, review_workflow, redline_templates, confidence_index,
metadata_extractor, or any other TriageCounsel engine module — see
tests/test_no_engine_imports.py, which enforces this as a hard, automated
constraint, not just a convention. Every action in this package happens the
way a customer's browser or HTTP client would: real signup, real session
cookies, real file upload, real page loads, real downloads. If the engine
has a bug, TriageBench will already have found it before this ever runs;
this package exists to catch the bugs the engine tests structurally cannot
see — a broken deploy, a misconfigured reverse proxy, a session that doesn't
persist, a download that requires no authorization, a DOCX that the engine
built correctly in memory but that got mangled somewhere between the server
and the customer's browser.
"""

__version__ = "1.0.0"

"""
Prepares real upload payloads for the live workflow.

This is the one place TriageBench Live touches the `triagebench` package
(not `triagebench_live`'s own concern to re-implement corpus discovery), and
only for test-data preparation — turning a Benchmark - TC SEC filing into
the plain-text bytes a customer would actually upload. That is data prep,
not a shortcut: the produced bytes still go through the real `/upload` HTTP
endpoint and the real (pinned-extension) `extract_text_from_file`/analysis
pipeline exactly like any customer's file would. No engine module
(rules_engine, docx_export, etc.) is imported here or anywhere in this
package — see tests/test_no_engine_imports.py.

TriageCounsel's `/upload` only accepts .pdf/.docx/.txt (see main.py's
ALLOWED_EXTENSIONS) — it has never had to accept the corpus's raw .htm SEC
filings, and a live-app test must upload something the real form actually
accepts. Every contract is therefore uploaded as `.txt`, using
`triagebench.html_extract.extract_primary` to turn the SEC HTML into plain
text first. This is exactly what a real customer would do with an emailed
SEC exhibit they wanted triaged: save it as text and upload it.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from triagebench import corpus as tb_corpus          # noqa: E402
from triagebench import html_extract as tb_html       # noqa: E402


@dataclass
class UploadPayload:
    contract_id_hint: str  # corpus contract_id, for correlating across runs
    category: str
    company_name: str
    filename: str          # the .txt filename actually POSTed to /upload
    content: bytes


def discover_payloads(
    categories: Optional[List[str]] = None,
    limit: Optional[int] = None,
    per_category_limit: Optional[int] = 5,
    seed: int = 20260101,
) -> List[UploadPayload]:
    refs = tb_corpus.discover(categories)
    selected = tb_corpus.select(refs, limit=limit, per_category_limit=per_category_limit, seed=seed)
    payloads = []
    for ref in selected:
        raw = ref.doc_path.read_bytes()
        text = tb_html.extract_primary(raw)
        if not text.strip():
            continue
        payloads.append(UploadPayload(
            contract_id_hint=ref.contract_id,
            category=ref.category,
            company_name=ref.company_name,
            filename=Path(ref.filename).stem[:60] + ".txt",
            content=text.encode("utf-8"),
        ))
    return payloads


def unique_test_email(prefix: str = "triagebench-live") -> str:
    """A fresh, disposable account per contract — see README for why: it
    keeps every contract's journey an isolated, realistic first-time
    customer signup (exercising the real signup flow every time) and sidesteps
    the free plan's 3-contracts/month quota without touching the database or
    granting the test account special treatment the real product doesn't
    offer any customer."""
    token = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=12))
    return f"{prefix}+{token}@example-triagebench.test"

"""
Corpus discovery: turns "Benchmark - TC/" into a flat, stable, addressable
list of ContractRef records TriageBench can iterate over.

Stability matters more than cleverness here. `contract_id` is derived only
from data that cannot change between runs (category + archive path), never
from row order in the parquet file or filesystem iteration order — both of
those are allowed to vary, and if `contract_id` depended on them, every
contract would silently get a new identity on every run and regression
detection (which joins two runs' results by contract_id) would report every
contract as "new" and "missing" simultaneously.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List, Optional

from . import config

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "triagebench requires pandas+pyarrow to read Benchmark - TC/*/archive/metadata.parquet "
        "(pip install pandas pyarrow)"
    ) from exc


@dataclass(frozen=True)
class ContractRef:
    contract_id: str
    category: str  # normalized label, e.g. "Employment"
    category_dir: str  # corpus folder name, e.g. "Employement"
    company_name: str
    form_type: str
    date_filed: str
    cik: str
    accession: str
    exhibit: Optional[str]
    archive_name: str
    doc_path: Path
    row_index: int

    @property
    def filename(self) -> str:
        return Path(self.archive_name).name

    def as_dict(self) -> dict:
        return {
            "contract_id": self.contract_id,
            "category": self.category,
            "company_name": self.company_name,
            "form_type": self.form_type,
            "date_filed": self.date_filed,
            "cik": self.cik,
            "accession": self.accession,
            "exhibit": self.exhibit,
            "archive_name": self.archive_name,
            "filename": self.filename,
        }


def _make_contract_id(category_dir: str, archive_name: str) -> str:
    digest = hashlib.sha1(f"{category_dir}/{archive_name}".encode("utf-8")).hexdigest()[:16]
    return f"{category_dir}:{digest}"


def discover(categories: Optional[List[str]] = None) -> List[ContractRef]:
    """Reads every category's metadata.parquet and resolves each row to the
    document on disk. Rows whose document is missing on disk are skipped at
    discovery time (recorded by the caller as a corpus-integrity issue, not
    a per-contract benchmark failure — the row never became a contract)."""
    categories = categories or config.CATEGORIES
    refs: List[ContractRef] = []
    for category_dir in categories:
        cat_root = config.CORPUS_ROOT / category_dir / "archive"
        parquet_path = cat_root / "metadata.parquet"
        if not parquet_path.exists():
            continue
        df = pd.read_parquet(parquet_path)
        label = config.CATEGORY_LABELS.get(category_dir, category_dir)
        for row_index, row in df.iterrows():
            archive_name = str(row.get("archive_name") or "")
            if not archive_name:
                continue
            doc_path = cat_root / "documents" / archive_name
            if not doc_path.exists():
                continue
            refs.append(
                ContractRef(
                    contract_id=_make_contract_id(category_dir, archive_name),
                    category=label,
                    category_dir=category_dir,
                    company_name=str(row.get("company_name") or ""),
                    form_type=str(row.get("form_type") or ""),
                    date_filed=str(row.get("date_filed") or ""),
                    cik=str(row.get("cik") or ""),
                    accession=str(row.get("accession") or ""),
                    exhibit=(str(row["exhibit"]) if pd.notna(row.get("exhibit")) else None),
                    archive_name=archive_name,
                    doc_path=doc_path,
                    row_index=int(row_index),
                )
            )
    # Sort by contract_id: a fixed, content-derived total order so the same
    # corpus always produces the same iteration order regardless of
    # filesystem/parquet row order — required for deterministic sampling
    # and for `--limit` to select the same contracts on every run.
    refs.sort(key=lambda r: r.contract_id)
    return refs


def select(
    refs: List[ContractRef],
    limit: Optional[int] = None,
    per_category_limit: Optional[int] = None,
    seed: int = config.BenchmarkConfig.__dataclass_fields__["seed"].default,
) -> List[ContractRef]:
    """Applies deterministic sampling. A fixed seed plus the fixed sort order
    from discover() means `--limit N` always returns the same N contracts for
    a given corpus snapshot — essential for a CI "quick" benchmark to be
    reproducible rather than a random subset each run."""
    rng = random.Random(seed)
    pool = list(refs)
    rng.shuffle(pool)  # shuffle is seeded -> deterministic, but avoids
    # biasing samples toward whichever category happens to sort first

    if per_category_limit is not None:
        by_cat: dict[str, List[ContractRef]] = {}
        for r in pool:
            by_cat.setdefault(r.category_dir, []).append(r)
        selected: List[ContractRef] = []
        for cat, items in by_cat.items():
            selected.extend(items[:per_category_limit])
        pool = selected

    if limit is not None:
        pool = pool[:limit]

    pool.sort(key=lambda r: r.contract_id)
    return pool

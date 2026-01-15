"""
I/O utilities for experiments.
"""
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional


def load_json(path: Path) -> Dict[str, Any]:
    """Load JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Dict[str, Any], path: Path) -> None:
    """Save JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_text(path: Path) -> str:
    """Read text file."""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def save_text(text: str, path: Path) -> None:
    """Save text file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def evidence_hash(evidence_text: str) -> str:
    """Compute hash of evidence text for normalization."""
    if not evidence_text:
        return ""
    # Normalize whitespace
    normalized = " ".join(evidence_text.split())
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:8]


def get_doc_ids(data_dir: Path) -> List[str]:
    """Get all document IDs from data directory."""
    ids = set()
    for path in data_dir.glob("*.txt"):
        ids.add(path.stem)
    return sorted(list(ids))

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
    """Get all document IDs from data directory (supports subdirectories for contract types)."""
    ids = set()
    # Check main directory
    if data_dir.exists():
        for path in data_dir.glob("*.txt"):
            ids.add(path.stem)
        # Check subdirectories (ndas/, msas/, employment/)
        for subdir in data_dir.iterdir():
            if subdir.is_dir():
                for path in subdir.glob("*.txt"):
                    ids.add(path.stem)
    
    # Also check parent data directory's subdirectories
    parent_dir = data_dir.parent if data_dir.name in ["ndas", "msas", "employment", "licensing"] else None
    if parent_dir and (parent_dir.name == "data" or (parent_dir.parent / "data").exists()):
        for subdir_name in ["ndas", "msas", "employment", "licensing"]:
            subdir = parent_dir / subdir_name
            if subdir.exists() and subdir.is_dir():
                for path in subdir.glob("*.txt"):
                    ids.add(path.stem)
    
    return sorted(list(ids))


def find_doc_file(data_dir: Path, doc_id: str, extension: str = ".txt") -> Optional[Path]:
    """Find a document file across all contract type subdirectories."""
    # Check main directory first (for backward compatibility)
    main_path = data_dir / f"{doc_id}{extension}"
    if main_path.exists():
        return main_path
    
    # Check parent data directory and its subdirectories (ndas/, msas/, employment/, licensing/)
    parent_dir = data_dir.parent if data_dir.name in ["ndas", "msas", "employment", "licensing"] else data_dir
    if parent_dir.name == "data" or (parent_dir.parent / "data").exists():
        # Check all contract type subdirectories
        for subdir_name in ["ndas", "msas", "employment", "licensing"]:
            subdir = parent_dir / subdir_name
            if subdir.exists() and subdir.is_dir():
                sub_path = subdir / f"{doc_id}{extension}"
                if sub_path.exists():
                    return sub_path
    
    # Also check direct subdirectories of data_dir
    if data_dir.exists():
        for subdir in data_dir.iterdir():
            if subdir.is_dir():
                sub_path = subdir / f"{doc_id}{extension}"
                if sub_path.exists():
                    return sub_path
    
    return None

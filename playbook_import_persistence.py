"""Import transaction boundaries — source-document provenance persistence."""

from __future__ import annotations

from sqlalchemy.orm import Session, make_transient

from models import PlaybookSourceDocument, PolicyPositionField


def ensure_source_document_persisted(
    db: Session, source_document: PlaybookSourceDocument,
) -> PlaybookSourceDocument:
    """Insert (or re-insert) the source document in this transaction before
    any PolicyPositionField rows reference it.

    A prior db.flush() followed by db.rollback() leaves source_document.id
    populated while the row no longer exists — copying that id onto field
    rows then fails the provenance FK at the next flush.
    """
    if source_document.id is not None and db.get(PlaybookSourceDocument, source_document.id) is None:
        make_transient(source_document)
    db.add(source_document)
    db.flush()
    return source_document


def assign_field_evidence(field: PolicyPositionField, source_document: PlaybookSourceDocument) -> None:
    """Bind provenance via ORM relationship so flush dependency ordering is correct."""
    field.evidence_document = source_document


def copy_field_evidence_from_revision(
    db: Session, new_field: PolicyPositionField, old_field: PolicyPositionField,
) -> None:
    """Copy provenance when forking an ACTIVE position — skip orphaned FK ids."""
    old_id = old_field.evidence_document_id
    if old_id is None:
        new_field.evidence_document_id = None
        return
    if db.get(PlaybookSourceDocument, old_id) is None:
        new_field.evidence_document_id = None
        return
    new_field.evidence_document_id = old_id

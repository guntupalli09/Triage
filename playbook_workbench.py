"""
Playbook Workbench — Phase 1 manual authoring routes.

A FastAPI APIRouter included into main.py's `app` (see
`app.include_router(playbook_workbench.router)` in main.py), kept in its
own module rather than growing main.py's already-large route list
further. Nothing here touches main.py's existing /playbooks/* routes,
PolicyRule, or any contract-review evaluation call site — see
docs/architecture/playbook_authoring_ux_design.md and
playbook_authoring.py's module docstring for the boundary this respects.
Production contract analysis continues reading PolicyRule exclusively;
PolicyPosition is authoring-only until Phase 4.

Every route re-derives the user from the session cookie and re-queries
the playbook filtered by that user's id — no route ever trusts a
playbook_id, clause_type, or position id from the URL/body as sufficient
authorization on its own. Ownership is re-checked on every request.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DBSession

import audit_log
import google_oauth
import playbook_authoring as pa
from auth import get_current_user
from csrf import csrf_protect, get_csrf_token
from database import get_db
from models import Playbook, PolicyPosition, PolicyPositionApproval

router = APIRouter()

# A second Jinja2Templates instance pointed at the same directory as
# main.py's — not shared module state, to avoid a circular import
# (main.py imports this module; this module cannot import `templates`
# back from main.py). Registers the same two globals main.py's instance
# does, since templates/base_app.html depends on both.
templates = Jinja2Templates(directory="templates")
templates.env.globals["google_signin_enabled"] = google_oauth.is_configured()
templates.env.globals["csrf_token"] = get_csrf_token


def _require_user(request: Request, db: DBSession):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user


def _get_owned_playbook(db: DBSession, user, playbook_id: int) -> Playbook:
    """The single ownership check every route in this module goes
    through — filtered by both id AND user_id in one query, so a
    nonexistent playbook and someone else's playbook are indistinguishable
    (both 404, never a 403 that would confirm the id exists)."""
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.user_id == user.id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return playbook


def _require_clause_type(clause_type: str) -> str:
    if clause_type not in pa.CLAUSE_TYPES:
        raise HTTPException(status_code=404, detail="Unknown clause type")
    return clause_type


def _base_context(request: Request, user, playbook: Playbook, clause_type: str, position: Optional[PolicyPosition]) -> dict:
    return {
        "request": request, "user": user, "playbook": playbook,
        "clause_type": clause_type, "clause_label": pa.CLAUSE_TYPE_LABELS[clause_type],
        "position": position, "cfg": (position.config_json or {}) if position else {},
        "field_statuses": pa.current_field_statuses(position) if position else {},
        "field_labels": pa.FIELD_LABELS[clause_type],
        "shared_field_labels": pa.SHARED_FIELD_LABELS,
        "vocab": {f: pa.vocabulary_for(clause_type, f) for f in pa.CLAUSE_TYPE_CONFIG_FIELDS[clause_type]},
        "is_new_revision": False,
        "current_year": datetime.now().year,
        "error": None,
    }


# ---------------------------------------------------------------------------
# Workbench
# ---------------------------------------------------------------------------

@router.get("/playbooks/{playbook_id}/workbench", response_class=HTMLResponse)
async def playbook_workbench(request: Request, playbook_id: int, db: DBSession = Depends(get_db)):
    user = _require_user(request, db)
    playbook = _get_owned_playbook(db, user, playbook_id)
    coverage = pa.compute_coverage(db, playbook)
    cards = []
    for c in coverage.clauses:
        missing = []
        if c.position is not None and c.position.status in ("NEEDS_REVIEW", "APPROVED", "DRAFT"):
            try:
                pa.validate_position_for_activation(c.position)
            except pa.PolicyActivationError as exc:
                missing = pa.missing_field_labels(c.clause_type, exc.missing_fields)
        cards.append({
            "clause_type": c.clause_type, "label": c.label, "status_bucket": c.status_bucket,
            "position": c.position, "headline": pa.card_headline(c.position),
            "missing_required": missing,
        })
    return templates.TemplateResponse("playbook_workbench.html", {
        "request": request, "user": user, "playbook": playbook,
        "coverage": coverage, "cards": cards, "current_year": datetime.now().year,
    })


# ---------------------------------------------------------------------------
# Authoring — edit / save
# ---------------------------------------------------------------------------

@router.get("/playbooks/{playbook_id}/positions/{clause_type}/edit", response_class=HTMLResponse)
async def position_edit_page(request: Request, playbook_id: int, clause_type: str, db: DBSession = Depends(get_db)):
    user = _require_user(request, db)
    playbook = _get_owned_playbook(db, user, playbook_id)
    clause_type = _require_clause_type(clause_type)

    # Idempotent: only actually creates a new row the first time this is
    # opened after the position reached ACTIVE (see
    # get_or_build_editable_position's docstring) — a page refresh never
    # forks a second revision.
    position, is_new_revision = pa.get_or_build_editable_position(db, playbook, clause_type)
    db.commit()

    ctx = _base_context(request, user, playbook, clause_type, position)
    ctx["is_new_revision"] = is_new_revision
    return templates.TemplateResponse(f"policy_position_fields/{clause_type}.html", ctx)


@router.post("/playbooks/{playbook_id}/positions/{clause_type}/save", response_class=HTMLResponse)
async def position_save(
    request: Request, playbook_id: int, clause_type: str,
    db: DBSession = Depends(get_db), _csrf: None = Depends(csrf_protect),
):
    user = _require_user(request, db)
    playbook = _get_owned_playbook(db, user, playbook_id)
    clause_type = _require_clause_type(clause_type)
    form = await request.form()

    position, is_new_revision = pa.get_or_build_editable_position(db, playbook, clause_type)

    try:
        clause_updates = pa.parse_clause_form(clause_type, form)
        pa.apply_position_update(
            db, position, clause_field_updates=clause_updates,
            contract_side=pa.parse_contract_side(form.get("contract_side")),
            escalation_approval_authority=(form.get("escalation_approval_authority") or "").strip() or None,
            fallback_text=(form.get("fallback_text") or "").strip() or None,
            user=user,
        )
    except (pa.PositionFormError, pa.PolicyConfigValidationError) as exc:
        db.rollback()
        ctx = _base_context(request, user, playbook, clause_type, None)
        ctx["position"] = None
        ctx["is_new_revision"] = is_new_revision
        ctx["error"] = str(exc)
        return templates.TemplateResponse(f"policy_position_fields/{clause_type}.html", ctx, status_code=400)

    db.commit()
    audit_log.record_event(
        db, "policy_position_saved", request=request, actor_user_id=user.id,
        target_type="policy_position", target_id=position.id, success=True,
        metadata={"clause_type": clause_type, "playbook_id": playbook.id},
    )
    db.commit()
    return RedirectResponse(url=f"/playbooks/{playbook.id}/positions/{clause_type}/edit", status_code=302)


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------

def _get_current_position_or_404(db: DBSession, playbook: Playbook, clause_type: str) -> PolicyPosition:
    position = pa.get_position_for_display(db, playbook.id, clause_type)
    if position is None:
        raise HTTPException(status_code=404, detail="No policy position exists yet for this clause type")
    return position


@router.post("/playbooks/{playbook_id}/positions/{clause_type}/submit-for-review", response_class=HTMLResponse)
async def position_submit_for_review(
    request: Request, playbook_id: int, clause_type: str,
    db: DBSession = Depends(get_db), _csrf: None = Depends(csrf_protect),
):
    user = _require_user(request, db)
    playbook = _get_owned_playbook(db, user, playbook_id)
    clause_type = _require_clause_type(clause_type)
    position = _get_current_position_or_404(db, playbook, clause_type)

    try:
        pa.mark_ready_for_review(db, position, user)
    except (pa.PositionLifecycleError, pa.PolicyConfigValidationError) as exc:
        db.rollback()
        ctx = _base_context(request, user, playbook, clause_type, position)
        ctx["error"] = str(exc)
        return templates.TemplateResponse(f"policy_position_fields/{clause_type}.html", ctx, status_code=400)

    db.commit()
    audit_log.record_event(
        db, "policy_position_submitted_for_review", request=request, actor_user_id=user.id,
        target_type="policy_position", target_id=position.id, success=True,
        metadata={"clause_type": clause_type, "playbook_id": playbook.id},
    )
    db.commit()
    return RedirectResponse(url=f"/playbooks/{playbook.id}/positions/{clause_type}/review", status_code=302)


@router.post("/playbooks/{playbook_id}/positions/{clause_type}/return-to-draft", response_class=HTMLResponse)
async def position_return_to_draft(
    request: Request, playbook_id: int, clause_type: str,
    db: DBSession = Depends(get_db), _csrf: None = Depends(csrf_protect),
):
    user = _require_user(request, db)
    playbook = _get_owned_playbook(db, user, playbook_id)
    clause_type = _require_clause_type(clause_type)
    position = _get_current_position_or_404(db, playbook, clause_type)

    try:
        pa.return_to_draft(db, position, user)
    except pa.PositionLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    db.commit()
    audit_log.record_event(
        db, "policy_position_returned_to_draft", request=request, actor_user_id=user.id,
        target_type="policy_position", target_id=position.id, success=True,
        metadata={"clause_type": clause_type, "playbook_id": playbook.id},
    )
    db.commit()
    return RedirectResponse(url=f"/playbooks/{playbook.id}/positions/{clause_type}/edit", status_code=302)


@router.get("/playbooks/{playbook_id}/positions/{clause_type}/review", response_class=HTMLResponse)
async def position_review_page(request: Request, playbook_id: int, clause_type: str, db: DBSession = Depends(get_db)):
    user = _require_user(request, db)
    playbook = _get_owned_playbook(db, user, playbook_id)
    clause_type = _require_clause_type(clause_type)
    position = _get_current_position_or_404(db, playbook, clause_type)

    missing_required = []
    try:
        pa.validate_position_for_activation(position)
    except pa.PolicyActivationError as exc:
        missing_required = pa.missing_field_labels(clause_type, exc.missing_fields)

    history = (
        db.query(PolicyPositionApproval)
        .filter(PolicyPositionApproval.policy_position_id == position.id)
        .order_by(PolicyPositionApproval.created_at.desc())
        .all()
    )

    ctx = _base_context(request, user, playbook, clause_type, position)
    ctx["summary_lines"] = pa.summarize_position(position)
    ctx["missing_required"] = missing_required
    ctx["history"] = history
    return templates.TemplateResponse("playbook_position_review.html", ctx)


@router.post("/playbooks/{playbook_id}/positions/{clause_type}/approve", response_class=HTMLResponse)
async def position_approve(
    request: Request, playbook_id: int, clause_type: str,
    db: DBSession = Depends(get_db), _csrf: None = Depends(csrf_protect),
):
    user = _require_user(request, db)
    playbook = _get_owned_playbook(db, user, playbook_id)
    clause_type = _require_clause_type(clause_type)
    position = _get_current_position_or_404(db, playbook, clause_type)

    try:
        pa.approve_position(db, position, user)
    except pa.PolicyActivationError as exc:
        db.rollback()
        ctx = _base_context(request, user, playbook, clause_type, position)
        ctx["summary_lines"] = pa.summarize_position(position)
        ctx["missing_required"] = pa.missing_field_labels(clause_type, exc.missing_fields)
        ctx["history"] = (
            db.query(PolicyPositionApproval)
            .filter(PolicyPositionApproval.policy_position_id == position.id)
            .order_by(PolicyPositionApproval.created_at.desc()).all()
        )
        ctx["error"] = "This position isn't ready to approve yet — see the unanswered questions below."
        return templates.TemplateResponse("playbook_position_review.html", ctx, status_code=400)
    except pa.PositionLifecycleError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    db.commit()
    audit_log.record_event(
        db, "policy_position_approved", request=request, actor_user_id=user.id,
        target_type="policy_position", target_id=position.id, success=True,
        metadata={"clause_type": clause_type, "playbook_id": playbook.id},
    )
    db.commit()
    return RedirectResponse(url=f"/playbooks/{playbook.id}/positions/{clause_type}/review", status_code=302)


@router.post("/playbooks/{playbook_id}/positions/{clause_type}/activate", response_class=HTMLResponse)
async def position_activate(
    request: Request, playbook_id: int, clause_type: str,
    db: DBSession = Depends(get_db), _csrf: None = Depends(csrf_protect),
):
    user = _require_user(request, db)
    playbook = _get_owned_playbook(db, user, playbook_id)
    clause_type = _require_clause_type(clause_type)
    position = _get_current_position_or_404(db, playbook, clause_type)

    try:
        pa.activate_position(db, position, user)
    except pa.PolicyActivationError as exc:
        db.rollback()
        ctx = _base_context(request, user, playbook, clause_type, position)
        ctx["summary_lines"] = pa.summarize_position(position)
        ctx["missing_required"] = pa.missing_field_labels(clause_type, exc.missing_fields)
        ctx["history"] = (
            db.query(PolicyPositionApproval)
            .filter(PolicyPositionApproval.policy_position_id == position.id)
            .order_by(PolicyPositionApproval.created_at.desc()).all()
        )
        ctx["error"] = "This position isn't ready to activate yet — see the unanswered questions below."
        return templates.TemplateResponse("playbook_position_review.html", ctx, status_code=400)
    except pa.PositionLifecycleError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    db.commit()
    audit_log.record_event(
        db, "policy_position_activated", request=request, actor_user_id=user.id,
        target_type="policy_position", target_id=position.id, success=True,
        metadata={"clause_type": clause_type, "playbook_id": playbook.id},
    )
    db.commit()
    return RedirectResponse(url=f"/playbooks/{playbook.id}/workbench", status_code=302)


# ---------------------------------------------------------------------------
# Preview — read-only, no Contract/review record, no production effect
# ---------------------------------------------------------------------------

@router.get("/playbooks/{playbook_id}/positions/{clause_type}/preview", response_class=HTMLResponse)
async def position_preview_page(request: Request, playbook_id: int, clause_type: str, db: DBSession = Depends(get_db)):
    user = _require_user(request, db)
    playbook = _get_owned_playbook(db, user, playbook_id)
    clause_type = _require_clause_type(clause_type)
    position = _get_current_position_or_404(db, playbook, clause_type)

    return templates.TemplateResponse("playbook_position_preview.html", {
        "request": request, "user": user, "playbook": playbook, "clause_type": clause_type,
        "clause_label": pa.CLAUSE_TYPE_LABELS[clause_type], "position": position,
        "sample_text": "", "decision": None, "current_year": datetime.now().year,
    })


@router.post("/playbooks/{playbook_id}/positions/{clause_type}/preview", response_class=HTMLResponse)
async def position_preview_run(
    request: Request, playbook_id: int, clause_type: str,
    db: DBSession = Depends(get_db), _csrf: None = Depends(csrf_protect),
):
    user = _require_user(request, db)
    playbook = _get_owned_playbook(db, user, playbook_id)
    clause_type = _require_clause_type(clause_type)
    position = _get_current_position_or_404(db, playbook, clause_type)

    form = await request.form()
    sample_text = (form.get("sample_text") or "").strip()
    decision = pa.run_preview(position, sample_text) if sample_text else None

    # Preview is read-only by construction: run_preview never calls
    # db.add/db.commit, and this route doesn't either. No Contract or
    # review record exists as a result of this request.
    return templates.TemplateResponse("playbook_position_preview.html", {
        "request": request, "user": user, "playbook": playbook, "clause_type": clause_type,
        "clause_label": pa.CLAUSE_TYPE_LABELS[clause_type], "position": position,
        "sample_text": sample_text, "decision": decision, "current_year": datetime.now().year,
    })

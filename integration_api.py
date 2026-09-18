"""
TriageCounsel Integration API — thin client surface for Word, Google Docs,
and the web repository/search/reporting/intake flows.

The policy engine is NOT duplicated here. Clients send document text,
choose a playbook, and receive authoritative findings already produced by
policy_enforcement + the interaction engine. Authentication is bearer
tokens (api_tokens.py); every query is tenant-scoped (tenancy.py).
"""
from __future__ import annotations

import io
import zipfile
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import get_db
from models import Contract, ContractRevision, IntakeRequest, Playbook, User
from docx_export import build_redlined_docx
import api_tokens
import audit_log
import auth
import canonical_index
import change_aware
import document_aggregation
import policy_enforcement
import portfolio_nl
import portfolio_query
import portfolio_reporting
import rate_limit
import review_pipeline
import review_workflow
import tenancy
import upload_security

router = APIRouter(prefix="/api/v1", tags=["integration"])


def _current_api_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = api_tokens.require_bearer_user(db, request)
    tenancy.ensure_user_tenant(db, user)
    return user


def _client_kind(request: Request) -> str:
    token = getattr(request.state, "api_token", None)
    if token and token.client_kind:
        return token.client_kind
    header = (request.headers.get("x-triagecounsel-client") or "").lower()
    if header in ("word", "google_docs", "web"):
        return header
    return "api"


class LoginBody(BaseModel):
    email: str
    password: str
    client_kind: str = "api"
    token_name: Optional[str] = None


class ReviewCreateBody(BaseModel):
    document_text: str = Field(..., min_length=1)
    filename: str = "document.txt"
    playbook_id: Optional[int] = None
    workspace_id: Optional[int] = None
    source: str = "api"
    display_name: Optional[str] = None
    contract_type: Optional[str] = None
    counterparty: Optional[str] = None
    business_unit: Optional[str] = None
    customer_type: Optional[str] = None
    deal_value: Optional[float] = None


class FindingActionBody(BaseModel):
    finding_key: str
    action: str
    reason: Optional[str] = None
    edited_text: Optional[str] = None
    comment: Optional[str] = None


class CommentBody(BaseModel):
    finding_key: str
    comment: str
    inserted_in_host: bool = False


class ReconfirmBody(BaseModel):
    document_text: str = Field(..., min_length=1)
    reevaluate_affected: bool = False


class StructuredSearchBody(BaseModel):
    model_config = ConfigDict(extra="allow")
    filters: list
    combinator: str = "and"
    limit: int = 100
    offset: int = 0
    workspace_id: Optional[int] = None


class NaturalLanguageSearchBody(BaseModel):
    question: str
    workspace_id: Optional[int] = None
    limit: int = 100


class IntakeCreateBody(BaseModel):
    document_text: str = Field(..., min_length=1)
    filename: str = "document.txt"
    display_name: Optional[str] = None
    requested_contract_type: Optional[str] = None
    counterparty: Optional[str] = None
    notes: Optional[str] = None
    playbook_id: Optional[int] = None
    workspace_id: Optional[int] = None


class IntakePromoteBody(BaseModel):
    playbook_id: Optional[int] = None


class RevisionImportBody(BaseModel):
    document_text: str = Field(..., min_length=1)
    filename: Optional[str] = None
    source: str = "revision_import"
    reevaluate_affected: bool = True


@router.post("/auth/login")
def api_login(
    body: LoginBody,
    request: Request,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit.rate_limit("api-login", limit=10, window_seconds=60)),
):
    email = body.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.password_hash or not auth.verify_password(body.password, user.password_hash):
        audit_log.record_event(
            db, "api_login_failed", request=request, success=False, detail=email,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    tenancy.ensure_user_tenant(db, user)
    client_kind = body.client_kind if body.client_kind in ("word", "google_docs", "api", "web") else "api"
    token_row, plaintext = api_tokens.mint_token(
        db, user, name=body.token_name or f"{client_kind} session",
        client_kind=client_kind,
    )
    db.commit()
    audit_log.record_event(
        db, "api_token_issued", request=request, actor_user_id=user.id,
        target_type="api_token", target_id=token_row.id, success=True,
        metadata={"client_kind": client_kind},
    )
    return {
        "token": plaintext,
        "token_prefix": token_row.token_prefix,
        "expires_at": token_row.expires_at.isoformat() if token_row.expires_at else None,
        "tenant_id": user.tenant_id,
        "workspace_id": user.workspace_id,
        "user": {"id": user.id, "email": user.email, "name": user.name},
    }


@router.post("/auth/logout")
def api_logout(request: Request, db: Session = Depends(get_db), user: User = Depends(_current_api_user)):
    token = getattr(request.state, "api_token", None)
    if token:
        api_tokens.revoke_token(db, token)
        db.commit()
    return {"ok": True}


@router.get("/me")
def api_me(request: Request, db: Session = Depends(get_db), user: User = Depends(_current_api_user)):
    roles = __import__("rbac").get_user_roles(db, user)
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "tenant_id": user.tenant_id,
        "workspace_id": user.workspace_id,
        "roles": roles,
        "requester_only": tenancy.is_requester_only(db, user),
        "can_modify_playbooks": tenancy.can_modify_playbooks(db, user),
        "can_review_contracts": tenancy.can_review_contracts(db, user),
        "workspaces": [
            {"id": w.id, "name": w.name} for w in tenancy.workspaces_for_user(db, user)
        ],
    }


@router.get("/playbooks")
def api_playbooks(db: Session = Depends(get_db), user: User = Depends(_current_api_user)):
    if tenancy.is_requester_only(db, user):
        raise HTTPException(status_code=403, detail="Business users cannot list or modify legal playbooks.")
    playbooks = tenancy.scoped_playbooks(db, user).order_by(Playbook.updated_at.desc()).all()
    return {
        "playbooks": [
            {
                "id": p.id,
                "name": p.name,
                "contract_type": p.contract_type,
                "description": p.description,
            }
            for p in playbooks
        ]
    }


def _run_review(db: Session, user: User, body: ReviewCreateBody, request: Request) -> Contract:
    if tenancy.is_requester_only(db, user):
        raise HTTPException(
            status_code=403,
            detail="Business users submit intake requests; they cannot run legal review directly.",
        )
    if not auth.check_usage_limit(user):
        raise HTTPException(status_code=402, detail="Monthly review limit reached.")
    text = upload_security.enforce_extracted_text_limit(body.document_text)
    filename = upload_security.sanitize_filename(body.filename or "document.txt")
    source = body.source if body.source in ("web", "word", "google_docs", "intake", "revision_import", "api") else "api"
    playbook = None
    if body.playbook_id:
        playbook = tenancy.get_accessible_playbook(db, user, body.playbook_id)
    workspace = tenancy.select_workspace(db, user, body.workspace_id)
    import main as app_main
    analysis = app_main.run_analysis(text)
    deviations = None
    if playbook and playbook.template_findings_json:
        comparison = app_main.playbook_engine.compare(analysis["findings_dict"], playbook.template_findings_json)
        deviations = comparison
    review_context = {
        "business_unit": (body.business_unit or "").strip() or None,
        "customer_type": (body.customer_type or "").strip() or None,
        "deal_value": body.deal_value,
    }
    policy_result = policy_enforcement.apply_policies_for_review(
        db, playbook, text, analysis["findings_dict"], context=review_context,
    )
    contract = review_pipeline.persist_reviewed_contract(
        db, user,
        contract_text=text,
        filename=filename,
        analysis=analysis,
        policy_result=policy_result,
        playbook=playbook,
        source=source,
        display_name=body.display_name,
        contract_type=body.contract_type,
        counterparty=body.counterparty,
        workspace_id=workspace.id,
        review_context=review_context,
        deviations=deviations,
    )
    user.contracts_this_month = (user.contracts_this_month or 0) + 1
    review_pipeline.record_integration_action(
        db, user, client_kind=_client_kind(request), action="review_created",
        contract_id=contract.id, request=request,
    )
    db.commit()
    db.refresh(contract)
    return contract


@router.post("/reviews")
def api_create_review(
    body: ReviewCreateBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
    _rl: None = Depends(rate_limit.rate_limit("api-review", limit=30, window_seconds=3600)),
):
    api_tokens.require_scope(request, "contracts.write")
    contract = _run_review(db, user, body, request)
    return review_pipeline.serialize_review(contract)


@router.get("/reviews/{contract_id}")
def api_get_review(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
):
    api_tokens.require_scope(request, "contracts.read")
    contract = tenancy.get_accessible_contract(db, user, contract_id)
    return review_pipeline.serialize_review(contract)


@router.get("/reviews/{contract_id}/findings")
def api_get_findings(contract_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(_current_api_user)):
    api_tokens.require_scope(request, "contracts.read")
    contract = tenancy.get_accessible_contract(db, user, contract_id)
    payload = review_pipeline.serialize_review(contract)
    return {"contract_id": contract.id, "findings": payload["findings"]}


@router.post("/reviews/{contract_id}/actions")
def api_finding_action(
    contract_id: int,
    body: FindingActionBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
):
    api_tokens.require_scope(request, "contracts.write")
    if tenancy.is_requester_only(db, user):
        raise HTTPException(status_code=403, detail="Business users cannot record legal-review decisions.")
    contract = tenancy.get_accessible_contract(db, user, contract_id)
    findings = contract.findings_json or []
    keyed = {review_workflow.finding_key(i, f.get("rule_id") or str(i)): (i, f) for i, f in enumerate(findings) if isinstance(f, dict)}
    if body.finding_key not in keyed:
        raise HTTPException(status_code=404, detail="Finding not found.")
    idx, finding = keyed[body.finding_key]
    try:
        review_workflow.validate_decision(
            body.finding_key, body.action, bool(finding.get("redline")),
            body.reason, body.edited_text,
            policy_state=finding.get("policy_state"),
            finding_type=finding.get("finding_type"),
        )
    except review_workflow.DecisionValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    from datetime import datetime
    decisions = dict(contract.review_decisions_json or {})
    entry = {
        "action": body.action,
        "rule_id": finding.get("rule_id"),
        "decided_at": datetime.utcnow().isoformat(),
        "decided_by": user.name or user.email,
    }
    if body.reason:
        entry["reason"] = body.reason.strip()
    if body.action == "edited" and body.edited_text:
        entry["edited_text"] = body.edited_text.strip()
    if body.comment:
        entry["comment"] = body.comment
    elif decisions.get(body.finding_key, {}).get("comment"):
        entry["comment"] = decisions[body.finding_key]["comment"]
    decisions[body.finding_key] = entry
    contract.review_decisions_json = decisions
    if body.action in ("edited", "rejected") and finding.get("clause_type"):
        import interaction_enforcement as ixe
        import playbook_authoring as pa
        label = pa.CLAUSE_TYPE_LABELS.get(finding["clause_type"], finding["clause_type"])
        ixe.mark_dependent_interactions_stale(contract, finding["clause_type"], label)
    canonical_index.upsert_fact_index(db, contract)
    review_pipeline.record_integration_action(
        db, user, client_kind=_client_kind(request), action=f"decision_{body.action}",
        contract_id=contract.id, finding_key=body.finding_key, request=request,
        payload={"action": body.action},
    )
    db.commit()
    return {"ok": True, "review_decisions": contract.review_decisions_json}


@router.post("/reviews/{contract_id}/comments")
def api_insert_comment(
    contract_id: int,
    body: CommentBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
):
    api_tokens.require_scope(request, "contracts.write")
    contract = tenancy.get_accessible_contract(db, user, contract_id)
    decisions = dict(contract.review_decisions_json or {})
    entry = dict(decisions.get(body.finding_key) or {})
    entry["comment"] = body.comment
    decisions[body.finding_key] = entry
    contract.review_decisions_json = decisions
    review_pipeline.record_integration_action(
        db, user, client_kind=_client_kind(request),
        action="comment_inserted" if body.inserted_in_host else "comment_recorded",
        contract_id=contract.id, finding_key=body.finding_key, request=request,
        payload={"inserted_in_host": body.inserted_in_host},
    )
    db.commit()
    return {"ok": True}


@router.post("/reviews/{contract_id}/reconfirm")
def api_reconfirm(
    contract_id: int,
    body: ReconfirmBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
):
    api_tokens.require_scope(request, "contracts.write")
    if tenancy.is_requester_only(db, user):
        raise HTTPException(status_code=403, detail="Business users cannot reconfirm legal decisions.")
    contract = tenancy.get_accessible_contract(db, user, contract_id)
    result = change_aware.reconfirm_against_text(
        db, contract, body.document_text, reevaluate_affected=body.reevaluate_affected,
    )
    canonical_index.upsert_fact_index(db, contract)
    review_pipeline.record_integration_action(
        db, user, client_kind=_client_kind(request), action="reconfirm",
        contract_id=contract.id, request=request,
        payload={"affected": result.get("affected_clause_types")},
    )
    db.commit()
    return {"ok": True, "change_aware": result, "review": review_pipeline.serialize_review(contract)}


def _document_state(contract: Contract) -> Optional[str]:
    effective_mode = "cutover" if contract.interaction_decisions_json is not None else "shadow"
    result = document_aggregation.aggregate_document_state(
        contract.overall_risk, contract.policy_decisions_json,
        contract.interaction_decisions_json, effective_mode,
    )
    return result.get("document_state")


def _export_filename(contract: Contract) -> str:
    import main as app_main
    return app_main.sanitize_filename(contract.filename or "contract")


@router.get("/reviews/{contract_id}/export")
def api_export_review(
    contract_id: int,
    request: Request,
    format: str = "docx",
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
):
    """Export the persisted review as a redlined DOCX or a negotiation zip.

    Word/Google/web clients download this instead of copying redlines by
    hand. The bytes are produced from stored findings + lawyer decisions;
    the policy engine is not re-run.
    """
    api_tokens.require_scope(request, "contracts.read")
    contract = tenancy.get_accessible_contract(db, user, contract_id)
    kind = (format or "docx").lower().strip()
    if kind not in ("docx", "package"):
        raise HTTPException(status_code=400, detail="format must be 'docx' or 'package'.")
    findings = contract.findings_json or []
    decisions = contract.review_decisions_json or {}
    if kind == "package":
        progress = review_workflow.compute_progress(findings, decisions)
        if not progress.is_complete:
            raise HTTPException(
                status_code=400,
                detail="Finish reviewing every finding before generating the negotiation package.",
            )
    author = user.name or user.email
    docx_bytes, skipped = build_redlined_docx(
        contract.filename, contract.contract_text or "", findings, decisions, author=author,
    )
    safe_name = _export_filename(contract)
    review_pipeline.record_integration_action(
        db, user, client_kind=_client_kind(request),
        action="export_package" if kind == "package" else "export_docx",
        contract_id=contract.id, request=request,
        payload={"format": kind, "skipped_redlines": skipped},
    )
    db.commit()
    if kind == "docx":
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="Redlined_{safe_name}.docx"'},
        )
    memo_text = review_workflow.build_cover_memo_text(
        contract.filename, findings, decisions, document_state=_document_state(contract),
    )
    audit_text = review_workflow.build_audit_trail_text(
        contract.filename, contract.rule_engine_version or "2.0.0", findings, decisions,
    )
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"Redlined_{safe_name}.docx", docx_bytes)
        zf.writestr("Cover_Memo.txt", memo_text)
        zf.writestr("Audit_Trail.txt", audit_text)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="NegotiationPackage_{safe_name}.zip"'},
    )


@router.get("/contracts")
def api_list_contracts(
    request: Request,
    q: Optional[str] = None,
    contract_type: Optional[str] = None,
    source: Optional[str] = None,
    review_status: Optional[str] = None,
    risk: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
):
    api_tokens.require_scope(request, "contracts.read")
    query = tenancy.scoped_contracts(db, user).filter(Contract.analysis_completed.is_(True))
    if q:
        like = f"%{q}%"
        from sqlalchemy import or_
        from models import Contract as C
        query = query.filter(or_(C.filename.ilike(like), C.display_name.ilike(like), C.counterparty.ilike(like)))
    if contract_type:
        query = query.filter(Contract.contract_type == contract_type)
    if source:
        query = query.filter(Contract.source == source)
    if review_status:
        query = query.filter(Contract.review_status == review_status)
    if risk:
        query = query.filter(Contract.overall_risk == risk)
    total = query.count()
    rows = query.order_by(Contract.created_at.desc()).offset(max(offset, 0)).limit(min(max(limit, 1), 200)).all()
    return {
        "total": total,
        "contracts": [
            {
                "id": c.id,
                "filename": c.filename,
                "display_name": c.display_name or c.filename,
                "contract_type": c.contract_type,
                "counterparty": c.counterparty,
                "source": c.source,
                "review_status": c.review_status,
                "overall_risk": c.overall_risk,
                "playbook_id": c.playbook_id,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "revision_number": c.revision_number,
                "parent_contract_id": c.parent_contract_id,
            }
            for c in rows
        ],
    }


@router.get("/portfolio/schema")
def api_portfolio_schema(user: User = Depends(_current_api_user)):
    return portfolio_query.query_schema()


@router.post("/portfolio/search")
def api_portfolio_search(
    body: StructuredSearchBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
):
    api_tokens.require_scope(request, "portfolio.search")
    if not tenancy.can_search_portfolio(db, user):
        raise HTTPException(status_code=403, detail="You do not have permission to search the contract portfolio.")
    try:
        payload = body.model_dump() if hasattr(body, "model_dump") else body.dict()
        parsed = portfolio_query.parse_structured_query(payload)
    except portfolio_query.PortfolioQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    requester_id = user.id if tenancy.is_requester_only(db, user) else None
    workspace_id = None
    if body.workspace_id is not None:
        workspace_id = tenancy.select_workspace(db, user, body.workspace_id).id
    rows, total = portfolio_query.apply_structured_query(
        db, tenant_id=user.tenant_id, query=parsed,
        workspace_id=workspace_id, requester_user_id=requester_id,
    )
    return {
        "total": total,
        "query": payload,
        "results": [portfolio_query.serialize_index_row(r) for r in rows],
        "authoritative": True,
        "source": "canonical_fact_index",
    }


@router.post("/portfolio/search/nl")
def api_portfolio_search_nl(
    body: NaturalLanguageSearchBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
):
    api_tokens.require_scope(request, "portfolio.search")
    if not tenancy.can_search_portfolio(db, user):
        raise HTTPException(status_code=403, detail="You do not have permission to search the contract portfolio.")
    try:
        parsed, raw = portfolio_nl.interpret_portfolio_question(body.question)
    except portfolio_nl.UnsupportedPortfolioQuery as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except portfolio_query.PortfolioQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    parsed.limit = min(max(body.limit, 1), 200)
    requester_id = user.id if tenancy.is_requester_only(db, user) else None
    workspace_id = None
    if body.workspace_id is not None:
        workspace_id = tenancy.select_workspace(db, user, body.workspace_id).id
    rows, total = portfolio_query.apply_structured_query(
        db, tenant_id=user.tenant_id, query=parsed,
        workspace_id=workspace_id, requester_user_id=requester_id,
    )
    return {
        "total": total,
        "question": body.question,
        "interpreted_query": {
            "filters": [{"field": f.field, "op": f.op, "value": f.value} for f in parsed.filters],
            "combinator": parsed.combinator,
        },
        "translator_raw": {k: raw[k] for k in raw if k in ("filters", "combinator", "unsupported", "reason")},
        "results": [portfolio_query.serialize_index_row(r) for r in rows],
        "authoritative": True,
        "source": "canonical_fact_index",
        "note": "The structured database result is authoritative. The model only translated the question.",
    }


@router.get("/portfolio/report")
def api_portfolio_report(
    request: Request,
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
):
    api_tokens.require_scope(request, "portfolio.report")
    if not tenancy.can_search_portfolio(db, user):
        raise HTTPException(status_code=403, detail="You do not have permission to view portfolio reports.")
    ws = tenancy.select_workspace(db, user, workspace_id).id if workspace_id is not None else None
    requester_id = user.id if tenancy.is_requester_only(db, user) else None
    return portfolio_reporting.build_portfolio_report(
        db, tenant_id=user.tenant_id, workspace_id=ws, requester_user_id=requester_id,
    )


@router.get("/portfolio/report/drilldown")
def api_portfolio_drilldown(
    ids: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
):
    api_tokens.require_scope(request, "portfolio.report")
    try:
        contract_ids = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="ids must be a comma-separated list of integers.")
    requester_id = user.id if tenancy.is_requester_only(db, user) else None
    return {
        "contracts": portfolio_reporting.drilldown_contracts(
            db, user.tenant_id, contract_ids, requester_user_id=requester_id,
        )
    }


@router.post("/intake")
def api_create_intake(
    body: IntakeCreateBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
    _rl: None = Depends(rate_limit.rate_limit("api-intake", limit=20, window_seconds=3600)),
):
    api_tokens.require_scope(request, "intake.submit")
    if body.playbook_id and tenancy.is_requester_only(db, user):
        raise HTTPException(status_code=403, detail="Business users cannot select or modify legal playbooks.")
    tenancy.ensure_user_tenant(db, user)
    workspace = tenancy.select_workspace(db, user, body.workspace_id)
    text = upload_security.enforce_extracted_text_limit(body.document_text)
    row = IntakeRequest(
        tenant_id=user.tenant_id,
        workspace_id=workspace.id,
        requester_user_id=user.id,
        filename=upload_security.sanitize_filename(body.filename or "document.txt"),
        contract_text=text,
        display_name=body.display_name,
        requested_contract_type=body.requested_contract_type,
        counterparty=body.counterparty,
        notes=body.notes,
        status="submitted",
        playbook_id=None if tenancy.is_requester_only(db, user) else body.playbook_id,
    )
    db.add(row)
    db.flush()
    audit_log.record_event(
        db, "intake_submitted", request=request, actor_user_id=user.id,
        target_type="intake_request", target_id=row.id, success=True,
    )
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status, "filename": row.filename}


@router.get("/intake")
def api_list_intake(db: Session = Depends(get_db), user: User = Depends(_current_api_user)):
    rows = tenancy.scoped_intake(db, user).order_by(IntakeRequest.created_at.desc()).limit(200).all()
    return {
        "requests": [
            {
                "id": r.id,
                "filename": r.filename,
                "display_name": r.display_name,
                "requested_contract_type": r.requested_contract_type,
                "counterparty": r.counterparty,
                "status": r.status,
                "contract_id": r.contract_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.post("/intake/{intake_id}/promote")
def api_promote_intake(
    intake_id: int,
    body: IntakePromoteBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
):
    if tenancy.is_requester_only(db, user) or not tenancy.can_review_contracts(db, user):
        raise HTTPException(status_code=403, detail="Only legal reviewers can start review from intake.")
    row = tenancy.scoped_intake(db, user).filter(IntakeRequest.id == intake_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Intake request not found.")
    playbook_id = body.playbook_id or row.playbook_id
    review_body = ReviewCreateBody(
        document_text=row.contract_text,
        filename=row.filename,
        playbook_id=playbook_id,
        workspace_id=row.workspace_id,
        source="intake",
        display_name=row.display_name or row.filename,
        contract_type=row.requested_contract_type,
        counterparty=row.counterparty,
    )
    contract = _run_review(db, user, review_body, request)
    contract.intake_request_id = row.id
    contract.review_status = "awaiting_legal"
    row.contract_id = contract.id
    row.status = "in_review"
    row.assigned_reviewer_user_id = user.id
    canonical_index.upsert_fact_index(db, contract)
    db.commit()
    return {"intake_id": row.id, "contract_id": contract.id, "review": review_pipeline.serialize_review(contract)}


@router.post("/reviews/{contract_id}/revisions")
def api_import_revision(
    contract_id: int,
    body: RevisionImportBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_current_api_user),
):
    api_tokens.require_scope(request, "contracts.write")
    if tenancy.is_requester_only(db, user):
        raise HTTPException(status_code=403, detail="Business users cannot import counterparty revisions.")
    original = tenancy.get_accessible_contract(db, user, contract_id)
    review_body = ReviewCreateBody(
        document_text=body.document_text,
        filename=body.filename or original.filename,
        playbook_id=original.playbook_id,
        workspace_id=original.workspace_id,
        source=body.source if body.source in ("revision_import", "word", "google_docs", "web") else "revision_import",
        display_name=original.display_name,
        contract_type=original.contract_type,
        counterparty=original.counterparty,
        business_unit=original.review_business_unit,
        customer_type=original.review_customer_type,
        deal_value=original.review_deal_value,
    )
    new_contract = _run_review(db, user, review_body, request)
    new_contract.parent_contract_id = original.id
    new_contract.revision_number = (original.revision_number or 1) + 1
    new_contract.review_status = "imported_revision"
    # Change-aware: compare new text against the ORIGINAL frozen evidence.
    change_result = change_aware.reconfirm_against_text(
        db, original, body.document_text, reevaluate_affected=False,
    )
    rev = ContractRevision(
        tenant_id=user.tenant_id,
        original_contract_id=original.id,
        revision_contract_id=new_contract.id,
        revision_number=new_contract.revision_number,
        source=new_contract.source,
        imported_by_user_id=user.id,
        change_summary_json={
            "affected_clause_types": change_result.get("affected_clause_types"),
            "preserved_clause_types": change_result.get("preserved_clause_types"),
        },
        invalidated_clause_types_json=change_result.get("affected_clause_types"),
    )
    db.add(rev)
    canonical_index.upsert_fact_index(db, original)
    canonical_index.upsert_fact_index(db, new_contract)
    db.commit()
    return {
        "original_contract_id": original.id,
        "revision_contract_id": new_contract.id,
        "revision_number": new_contract.revision_number,
        "change_aware": change_result,
        "review": review_pipeline.serialize_review(new_contract),
        "prior_review_preserved": True,
    }


@router.get("/reviews/{contract_id}/revisions")
def api_list_revisions(contract_id: int, db: Session = Depends(get_db), user: User = Depends(_current_api_user)):
    original = tenancy.get_accessible_contract(db, user, contract_id)
    rows = (
        db.query(ContractRevision)
        .filter(
            ContractRevision.tenant_id == user.tenant_id,
            (ContractRevision.original_contract_id == original.id) | (ContractRevision.revision_contract_id == original.id),
        )
        .order_by(ContractRevision.revision_number.asc())
        .all()
    )
    return {
        "contract_id": original.id,
        "revisions": [
            {
                "id": r.id,
                "original_contract_id": r.original_contract_id,
                "revision_contract_id": r.revision_contract_id,
                "revision_number": r.revision_number,
                "source": r.source,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "invalidated_clause_types": r.invalidated_clause_types_json,
                "change_summary": r.change_summary_json,
            }
            for r in rows
        ],
    }


@router.get("/reviews/{contract_id}/audit")
def api_review_audit(contract_id: int, db: Session = Depends(get_db), user: User = Depends(_current_api_user)):
    contract = tenancy.get_accessible_contract(db, user, contract_id)
    from models import AuditLog, IntegrationAction
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.target_type == "contract", AuditLog.target_id == contract.id)
        .order_by(AuditLog.created_at.asc())
        .limit(500)
        .all()
    )
    actions = (
        db.query(IntegrationAction)
        .filter(IntegrationAction.tenant_id == user.tenant_id, IntegrationAction.contract_id == contract.id)
        .order_by(IntegrationAction.created_at.asc())
        .limit(500)
        .all()
    )
    return {
        "contract_id": contract.id,
        "audit_log": [
            {
                "event_type": e.event_type,
                "actor_user_id": e.actor_user_id,
                "success": e.success,
                "detail": e.detail,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in logs
        ],
        "integration_actions": [
            {
                "action": a.action,
                "client_kind": a.client_kind,
                "finding_key": a.finding_key,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in actions
        ],
    }

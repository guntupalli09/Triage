"""Pydantic request/response models for playbook/api.py."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MatterCreate(BaseModel):
    client_id: int
    name: str
    matter_number: Optional[str] = None


class ContractTypeCreate(BaseModel):
    name: str
    slug: str


class PolicySetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    organization_id: Optional[int] = None
    practice_group_id: Optional[int] = None
    client_id: Optional[int] = None
    matter_id: Optional[int] = None
    contract_type_id: Optional[int] = None


class PolicyRuleCreate(BaseModel):
    policy_topic: str
    title: str
    status: str  # acceptable | negotiate | prohibited
    bound_rule_ids: Optional[List[str]] = None
    preferred_position: Optional[str] = None
    fallback_position: Optional[str] = None
    approved_redline: Optional[str] = None
    minimum_requirement: Optional[str] = None
    maximum_requirement: Optional[str] = None
    business_reason: Optional[str] = None
    legal_reason: Optional[str] = None
    risk_score: Optional[int] = Field(default=None, ge=0, le=100)
    severity: Optional[str] = None
    approval_required: bool = False
    escalation_owner: Optional[str] = None
    jurisdiction: Optional[str] = None
    applies_to_contract_types: Optional[List[str]] = None
    exceptions: Optional[List[Dict[str, Any]]] = None


class PolicyRuleUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    preferred_position: Optional[str] = None
    fallback_position: Optional[str] = None
    approved_redline: Optional[str] = None
    minimum_requirement: Optional[str] = None
    maximum_requirement: Optional[str] = None
    business_reason: Optional[str] = None
    legal_reason: Optional[str] = None
    risk_score: Optional[int] = Field(default=None, ge=0, le=100)
    severity: Optional[str] = None
    approval_required: Optional[bool] = None
    escalation_owner: Optional[str] = None


class OverrideCreate(BaseModel):
    reason: str
    overridden_status: str
    matter_id: Optional[int] = None
    approval_required: bool = False


class PolicySetImport(BaseModel):
    name: str
    description: Optional[str] = None
    version_major: int = 1
    version_minor: int = 0
    jurisdiction_scope: Dict[str, Optional[int]] = Field(default_factory=dict)
    rules: List[Dict[str, Any]] = Field(default_factory=list)

"""Compliance CRUD API endpoints for APEX-OS Business Platform."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/compliance", tags=["compliance"])

# ── In-memory data stores ─────────────────────────────────────────────────────

_frameworks_db = {
    1: {"id": 1, "name": "SOC 2", "version": "2017", "description": "Service Organization Control 2", "status": "active", "created_at": "2024-01-15T10:00:00"},
    2: {"id": 2, "name": "ISO 27001", "version": "2022", "description": "Information Security Management", "status": "active", "created_at": "2024-02-20T09:00:00"},
    3: {"id": 3, "name": "GDPR", "version": "2018", "description": "General Data Protection Regulation", "status": "active", "created_at": "2024-03-10T14:00:00"},
    4: {"id": 4, "name": "HIPAA", "version": "2013", "description": "Health Insurance Portability and Accountability", "status": "inactive", "created_at": "2024-04-05T11:00:00"},
}
_controls_db = {
    1: {"id": 1, "framework_id": 1, "name": "Access Control Policy", "description": "Restrict system access to authorized users", "status": "implemented", "owner": "Security Team", "created_at": "2024-01-20T10:00:00"},
    2: {"id": 2, "framework_id": 1, "name": "Data Encryption", "description": "Encrypt data at rest and in transit", "status": "implemented", "owner": "Engineering", "created_at": "2024-02-15T09:00:00"},
    3: {"id": 3, "framework_id": 2, "name": "Risk Assessment", "description": "Annual information security risk assessment", "status": "in_progress", "owner": "Compliance Team", "created_at": "2024-03-20T14:00:00"},
    4: {"id": 4, "framework_id": 3, "name": "Data Subject Rights", "description": "Handle data subject access requests", "status": "planned", "owner": "Legal Team", "created_at": "2024-04-10T11:00:00"},
}
_audits_db = {
    1: {"id": 1, "framework_id": 1, "name": "SOC 2 Type I Audit", "auditor": "Deloitte", "start_date": "2024-06-01", "end_date": "2024-08-31", "status": "completed", "result": "passed", "created_at": "2024-05-15T10:00:00"},
    2: {"id": 2, "framework_id": 2, "name": "ISO 27001 Surveillance", "auditor": "BSI", "start_date": "2024-09-01", "end_date": "2024-09-30", "status": "in_progress", "result": None, "created_at": "2024-08-20T09:00:00"},
    3: {"id": 3, "framework_id": 3, "name": "GDPR Compliance Review", "auditor": "Internal", "start_date": "2024-10-01", "end_date": "2024-10-31", "status": "scheduled", "result": None, "created_at": "2024-09-10T14:00:00"},
}
_findings_db = {
    1: {"id": 1, "audit_id": 1, "title": "Missing MFA on legacy systems", "description": "Some legacy admin accounts lack MFA", "severity": "high", "status": "open", "assigned_to": "Security Team", "due_date": "2024-09-15", "created_at": "2024-08-20T10:00:00"},
    2: {"id": 2, "audit_id": 1, "title": "Outdated access reviews", "description": "Quarterly access reviews not documented for Q2", "severity": "medium", "status": "in_progress", "assigned_to": "IT Ops", "due_date": "2024-09-30", "created_at": "2024-08-22T09:00:00"},
    3: {"id": 3, "audit_id": 2, "title": "Incomplete asset inventory", "description": "Cloud assets not fully tracked in CMDB", "severity": "critical", "status": "open", "assigned_to": "Engineering", "due_date": "2024-10-15", "created_at": "2024-09-25T14:00:00"},
}
_remediation_plans_db = {
    1: {"id": 1, "finding_id": 1, "title": "Deploy MFA on all admin accounts", "description": "Roll out MFA to all legacy admin systems", "status": "in_progress", "owner": "Security Team", "target_date": "2024-09-15", "created_at": "2024-08-25T10:00:00"},
    2: {"id": 2, "finding_id": 2, "title": "Document Q2 access reviews", "description": "Complete and document quarterly access reviews", "status": "planned", "owner": "IT Ops", "target_date": "2024-09-30", "created_at": "2024-08-28T09:00:00"},
    3: {"id": 3, "finding_id": 3, "title": "Implement cloud asset tracking", "description": "Deploy automated cloud asset discovery and CMDB sync", "status": "not_started", "owner": "Engineering", "target_date": "2024-10-15", "created_at": "2024-09-26T14:00:00"},
}

_next_ids = {"frameworks": 5, "controls": 5, "audits": 4, "findings": 4, "remediation_plans": 4}


# ── Pydantic models ──────────────────────────────────────────────────────────

class ComplianceFrameworkCreate(BaseModel):
    name: str
    version: str = ""
    description: str = ""
    status: str = "active"


class ComplianceFrameworkUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ComplianceFrameworkResponse(BaseModel):
    id: int
    name: str
    version: str
    description: str
    status: str
    created_at: str


class ControlCreate(BaseModel):
    framework_id: int
    name: str
    description: str = ""
    status: str = "planned"
    owner: str = ""


class ControlUpdate(BaseModel):
    framework_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None


class ControlResponse(BaseModel):
    id: int
    framework_id: int
    name: str
    description: str
    status: str
    owner: str
    created_at: str


class AuditCreate(BaseModel):
    framework_id: int
    name: str
    auditor: str = ""
    start_date: str = ""
    end_date: str = ""
    status: str = "scheduled"
    result: Optional[str] = None


class AuditUpdate(BaseModel):
    framework_id: Optional[int] = None
    name: Optional[str] = None
    auditor: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    result: Optional[str] = None


class AuditResponse(BaseModel):
    id: int
    framework_id: int
    name: str
    auditor: str
    start_date: str
    end_date: str
    status: str
    result: Optional[str]
    created_at: str


class FindingCreate(BaseModel):
    audit_id: int
    title: str
    description: str = ""
    severity: str = "medium"
    status: str = "open"
    assigned_to: str = ""
    due_date: str = ""


class FindingUpdate(BaseModel):
    audit_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None


class FindingResponse(BaseModel):
    id: int
    audit_id: int
    title: str
    description: str
    severity: str
    status: str
    assigned_to: str
    due_date: str
    created_at: str


class RemediationPlanCreate(BaseModel):
    finding_id: int
    title: str
    description: str = ""
    status: str = "not_started"
    owner: str = ""
    target_date: str = ""


class RemediationPlanUpdate(BaseModel):
    finding_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    target_date: Optional[str] = None


class RemediationPlanResponse(BaseModel):
    id: int
    finding_id: int
    title: str
    description: str
    status: str
    owner: str
    target_date: str
    created_at: str


# ── Helper ───────────────────────────────────────────────────────────────────

def _get_store_and_id(store_name: str):
    stores = {
        "frameworks": (_frameworks_db, ComplianceFrameworkCreate, ComplianceFrameworkUpdate, ComplianceFrameworkResponse),
        "controls": (_controls_db, ControlCreate, ControlUpdate, ControlResponse),
        "audits": (_audits_db, AuditCreate, AuditUpdate, AuditResponse),
        "findings": (_findings_db, FindingCreate, FindingUpdate, FindingResponse),
        "remediation_plans": (_remediation_plans_db, RemediationPlanCreate, RemediationPlanUpdate, RemediationPlanResponse),
    }
    return stores[store_name]


# ── CRUD routes for each resource ────────────────────────────────────────────

# Frameworks
@router.get("/frameworks/", response_model=list[ComplianceFrameworkResponse])
async def list_frameworks(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), status: Optional[str] = None):
    frameworks = list(_frameworks_db.values())
    if status:
        frameworks = [f for f in frameworks if f["status"] == status]
    return frameworks[skip : skip + limit]


@router.get("/frameworks/{framework_id}", response_model=ComplianceFrameworkResponse)
async def get_framework(framework_id: int):
    framework = _frameworks_db.get(framework_id)
    if not framework:
        raise HTTPException(status_code=404, detail=f"Framework {framework_id} not found")
    return framework


@router.post("/frameworks/", response_model=ComplianceFrameworkResponse, status_code=201)
async def create_framework(framework: ComplianceFrameworkCreate):
    global _next_ids
    new_framework = {
        "id": _next_ids["frameworks"],
        "name": framework.name,
        "version": framework.version,
        "description": framework.description,
        "status": framework.status,
        "created_at": datetime.utcnow().isoformat(),
    }
    _frameworks_db[_next_ids["frameworks"]] = new_framework
    _next_ids["frameworks"] += 1
    return new_framework


@router.put("/frameworks/{framework_id}", response_model=ComplianceFrameworkResponse)
async def update_framework(framework_id: int, framework: ComplianceFrameworkUpdate):
    existing = _frameworks_db.get(framework_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Framework {framework_id} not found")
    for field, value in framework.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing


@router.delete("/frameworks/{framework_id}", status_code=204)
async def delete_framework(framework_id: int):
    if framework_id not in _frameworks_db:
        raise HTTPException(status_code=404, detail=f"Framework {framework_id} not found")
    del _frameworks_db[framework_id]


# Controls
@router.get("/controls/", response_model=list[ControlResponse])
async def list_controls(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), framework_id: Optional[int] = None, status: Optional[str] = None):
    controls = list(_controls_db.values())
    if framework_id:
        controls = [c for c in controls if c["framework_id"] == framework_id]
    if status:
        controls = [c for c in controls if c["status"] == status]
    return controls[skip : skip + limit]


@router.get("/controls/{control_id}", response_model=ControlResponse)
async def get_control(control_id: int):
    control = _controls_db.get(control_id)
    if not control:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")
    return control


@router.post("/controls/", response_model=ControlResponse, status_code=201)
async def create_control(control: ControlCreate):
    global _next_ids
    new_control = {
        "id": _next_ids["controls"],
        "framework_id": control.framework_id,
        "name": control.name,
        "description": control.description,
        "status": control.status,
        "owner": control.owner,
        "created_at": datetime.utcnow().isoformat(),
    }
    _controls_db[_next_ids["controls"]] = new_control
    _next_ids["controls"] += 1
    return new_control


@router.put("/controls/{control_id}", response_model=ControlResponse)
async def update_control(control_id: int, control: ControlUpdate):
    existing = _controls_db.get(control_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")
    for field, value in control.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing


@router.delete("/controls/{control_id}", status_code=204)
async def delete_control(control_id: int):
    if control_id not in _controls_db:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")
    del _controls_db[control_id]


# Audits
@router.get("/audits/", response_model=list[AuditResponse])
async def list_audits(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), framework_id: Optional[int] = None, status: Optional[str] = None):
    audits = list(_audits_db.values())
    if framework_id:
        audits = [a for a in audits if a["framework_id"] == framework_id]
    if status:
        audits = [a for a in audits if a["status"] == status]
    return audits[skip : skip + limit]


@router.get("/audits/{audit_id}", response_model=AuditResponse)
async def get_audit(audit_id: int):
    audit = _audits_db.get(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail=f"Audit {audit_id} not found")
    return audit


@router.post("/audits/", response_model=AuditResponse, status_code=201)
async def create_audit(audit: AuditCreate):
    global _next_ids
    new_audit = {
        "id": _next_ids["audits"],
        "framework_id": audit.framework_id,
        "name": audit.name,
        "auditor": audit.auditor,
        "start_date": audit.start_date,
        "end_date": audit.end_date,
        "status": audit.status,
        "result": audit.result,
        "created_at": datetime.utcnow().isoformat(),
    }
    _audits_db[_next_ids["audits"]] = new_audit
    _next_ids["audits"] += 1
    return new_audit


@router.put("/audits/{audit_id}", response_model=AuditResponse)
async def update_audit(audit_id: int, audit: AuditUpdate):
    existing = _audits_db.get(audit_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Audit {audit_id} not found")
    for field, value in audit.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing


@router.delete("/audits/{audit_id}", status_code=204)
async def delete_audit(audit_id: int):
    if audit_id not in _audits_db:
        raise HTTPException(status_code=404, detail=f"Audit {audit_id} not found")
    del _audits_db[audit_id]


# Findings
@router.get("/findings/", response_model=list[FindingResponse])
async def list_findings(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), audit_id: Optional[int] = None, severity: Optional[str] = None, status: Optional[str] = None):
    findings = list(_findings_db.values())
    if audit_id:
        findings = [f for f in findings if f["audit_id"] == audit_id]
    if severity:
        findings = [f for f in findings if f["severity"] == severity]
    if status:
        findings = [f for f in findings if f["status"] == status]
    return findings[skip : skip + limit]


@router.get("/findings/{finding_id}", response_model=FindingResponse)
async def get_finding(finding_id: int):
    finding = _findings_db.get(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")
    return finding


@router.post("/findings/", response_model=FindingResponse, status_code=201)
async def create_finding(finding: FindingCreate):
    global _next_ids
    new_finding = {
        "id": _next_ids["findings"],
        "audit_id": finding.audit_id,
        "title": finding.title,
        "description": finding.description,
        "severity": finding.severity,
        "status": finding.status,
        "assigned_to": finding.assigned_to,
        "due_date": finding.due_date,
        "created_at": datetime.utcnow().isoformat(),
    }
    _findings_db[_next_ids["findings"]] = new_finding
    _next_ids["findings"] += 1
    return new_finding


@router.put("/findings/{finding_id}", response_model=FindingResponse)
async def update_finding(finding_id: int, finding: FindingUpdate):
    existing = _findings_db.get(finding_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")
    for field, value in finding.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing


@router.delete("/findings/{finding_id}", status_code=204)
async def delete_finding(finding_id: int):
    if finding_id not in _findings_db:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")
    del _findings_db[finding_id]


# Remediation Plans
@router.get("/remediation-plans/", response_model=list[RemediationPlanResponse])
async def list_remediation_plans(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), finding_id: Optional[int] = None, status: Optional[str] = None):
    plans = list(_remediation_plans_db.values())
    if finding_id:
        plans = [p for p in plans if p["finding_id"] == finding_id]
    if status:
        plans = [p for p in plans if p["status"] == status]
    return plans[skip : skip + limit]


@router.get("/remediation-plans/{plan_id}", response_model=RemediationPlanResponse)
async def get_remediation_plan(plan_id: int):
    plan = _remediation_plans_db.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Remediation plan {plan_id} not found")
    return plan


@router.post("/remediation-plans/", response_model=RemediationPlanResponse, status_code=201)
async def create_remediation_plan(plan: RemediationPlanCreate):
    global _next_ids
    new_plan = {
        "id": _next_ids["remediation_plans"],
        "finding_id": plan.finding_id,
        "title": plan.title,
        "description": plan.description,
        "status": plan.status,
        "owner": plan.owner,
        "target_date": plan.target_date,
        "created_at": datetime.utcnow().isoformat(),
    }
    _remediation_plans_db[_next_ids["remediation_plans"]] = new_plan
    _next_ids["remediation_plans"] += 1
    return new_plan


@router.put("/remediation-plans/{plan_id}", response_model=RemediationPlanResponse)
async def update_remediation_plan(plan_id: int, plan: RemediationPlanUpdate):
    existing = _remediation_plans_db.get(plan_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Remediation plan {plan_id} not found")
    for field, value in plan.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing


@router.delete("/remediation-plans/{plan_id}", status_code=204)
async def delete_remediation_plan(plan_id: int):
    if plan_id not in _remediation_plans_db:
        raise HTTPException(status_code=404, detail=f"Remediation plan {plan_id} not found")
    del _remediation_plans_db[plan_id]

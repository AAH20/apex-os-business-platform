"""Deepened documents module: management, collaboration, templates, search, workflow."""
from __future__ import annotations
import hashlib, re, time, uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

class DocumentStatus(Enum):
    DRAFT, PUBLISHED, ARCHIVED = "draft", "published", "archived"

@dataclass
class DocumentVersion:
    version_id: str
    document_id: str
    content: str
    author: str
    created_at: float
    change_summary: str = ""
    parent_version: str | None = None
    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()[:12]

@dataclass
class Document:
    document_id: str
    title: str
    owner: str
    status: DocumentStatus = DocumentStatus.DRAFT
    current_version: DocumentVersion | None = None
    versions: list[DocumentVersion] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    def create_version(self, content: str, author: str, summary: str = "") -> DocumentVersion:
        v = DocumentVersion(str(uuid.uuid4())[:8], self.document_id, content, author,
                            time.time(), summary,
                            self.current_version.version_id if self.current_version else None)
        self.versions.append(v)
        self.current_version = v
        self.updated_at = time.time()
        return v
    def get_version(self, vid: str) -> DocumentVersion | None:
        return next((v for v in self.versions if v.version_id == vid), None)
    def rollback(self, vid: str) -> DocumentVersion | None:
        t = self.get_version(vid)
        if t:
            self.current_version, self.updated_at = t, time.time()
        return t
    def diff_versions(self, a: str, b: str) -> list[str]:
        va, vb = self.get_version(a), self.get_version(b)
        if not va or not vb:
            return []
        la, lb = va.content.splitlines(), vb.content.splitlines()
        return [f"Line {i+1}: '{la[i] if i < len(la) else ''}' -> '{lb[i] if i < len(lb) else ''}'"
                for i in range(max(len(la), len(lb)))
                if (la[i] if i < len(la) else "") != (lb[i] if i < len(lb) else "")]

class CollabEventType(Enum):
    JOIN, LEAVE, EDIT, CURSOR, COMMENT = "join", "leave", "edit", "cursor", "comment"

@dataclass
class CollabEvent:
    event_id: str
    document_id: str
    event_type: CollabEventType
    user_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class CursorPosition:
    user_id: str
    line: int
    column: int
    selection_start: int | None = None
    selection_end: int | None = None

class CollaborationSession:
    def __init__(self, document_id: str):
        self.document_id = document_id
        self.participants: dict[str, dict[str, Any]] = {}
        self.cursors: dict[str, CursorPosition] = {}
        self.event_log: list[CollabEvent] = []
        self._subs: list[Callable[[CollabEvent], None]] = []
        self._ops: list[dict[str, Any]] = []
    def join(self, uid: str, name: str = "") -> None:
        self.participants[uid] = {"name": name or uid, "joined_at": time.time(), "is_active": True}
        self._emit(CollabEventType.JOIN, uid, {"name": name})
    def leave(self, uid: str) -> None:
        if uid in self.participants:
            self.participants[uid]["is_active"] = False
            self.cursors.pop(uid, None)
            self._emit(CollabEventType.LEAVE, uid, {})
    def update_cursor(self, uid: str, line: int, col: int, ss: int | None = None, se: int | None = None) -> None:
        self.cursors[uid] = CursorPosition(uid, line, col, ss, se)
        self._emit(CollabEventType.CURSOR, uid, {"line": line, "column": col})
    def apply_edit(self, uid: str, op: dict[str, Any]) -> None:
        self._ops.append({"user_id": uid, "timestamp": time.time(), **op})
        self._emit(CollabEventType.EDIT, uid, op)
    def add_comment(self, uid: str, text: str, anchor: dict[str, Any] | None = None) -> None:
        self._emit(CollabEventType.COMMENT, uid, {"text": text, "anchor": anchor or {}})
    def active_participants(self) -> list[dict[str, Any]]:
        return [p for p in self.participants.values() if p.get("is_active")]
    def subscribe(self, cb: Callable[[CollabEvent], None]) -> None:
        self._subs.append(cb)
    def replay(self, since: float = 0) -> list[dict[str, Any]]:
        return [o for o in self._ops if o["timestamp"] >= since]
    def _emit(self, et: CollabEventType, uid: str, payload: dict[str, Any]) -> None:
        ev = CollabEvent(str(uuid.uuid4())[:8], self.document_id, et, uid, payload)
        self.event_log.append(ev)
        for s in self._subs:
            s(ev)

@dataclass
class MergeField:
    name: str
    field_type: str = "string"
    default_value: str = ""
    required: bool = False
    description: str = ""

@dataclass
class DocumentTemplate:
    template_id: str
    name: str
    content: str
    fields: list[MergeField] = field(default_factory=list)
    category: str = "general"
    created_at: float = field(default_factory=time.time)
    def add_field(self, name: str, ftype: str = "string", default: str = "", required: bool = False, desc: str = "") -> None:
        self.fields.append(MergeField(name, ftype, default, required, desc))
    def extract_fields(self) -> list[str]:
        return re.findall(r"\{\{(\w+)\}\}", self.content)
    def render(self, values: dict[str, str]) -> str:
        missing = [f.name for f in self.fields if f.required and f.name not in values]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        result = self.content
        for f in self.fields:
            result = result.replace("{{" + f.name + "}}", values.get(f.name, f.default_value))
        return re.sub(r"\{\{\w+\}\}", "", result)
    def validate(self, values: dict[str, str]) -> list[str]:
        errors: list[str] = []
        for f in self.fields:
            if f.required and not values.get(f.name):
                errors.append(f"Field '{f.name}' is required")
            if f.field_type == "date" and values.get(f.name) and not re.match(r"\d{4}-\d{2}-\d{2}", values[f.name]):
                errors.append(f"Field '{f.name}' must be YYYY-MM-DD")
            if f.field_type == "email" and values.get(f.name) and "@" not in values[f.name]:
                errors.append(f"Field '{f.name}' must be a valid email")
        return errors

@dataclass
class SearchResult:
    document_id: str
    title: str
    snippet: str
    score: float
    highlights: list[str] = field(default_factory=list)
    matched_fields: list[str] = field(default_factory=list)

class DocumentSearchEngine:
    def __init__(self):
        self._index: dict[str, dict[str, Any]] = {}
        self._inv: dict[str, set[str]] = {}
    def index_document(self, doc: Document) -> None:
        content = doc.current_version.content if doc.current_version else ""
        tokens = self._tokenize(f"{content} {doc.title} {' '.join(doc.tags)}")
        self._index[doc.document_id] = {"title": doc.title, "content": content,
                                        "tags": doc.tags, "tokens": tokens,
                                        "status": doc.status.value, "updated_at": doc.updated_at}
        for t in tokens:
            self._inv.setdefault(t, set()).add(doc.document_id)
    def remove_document(self, doc_id: str) -> None:
        if doc_id in self._index:
            for t in self._index[doc_id]["tokens"]:
                self._inv.get(t, set()).discard(doc_id)
            del self._index[doc_id]
    def search(self, query: str, limit: int = 20, filters: dict[str, Any] | None = None) -> list[SearchResult]:
        qt = self._tokenize(query)
        if not qt:
            return []
        scores: dict[str, float] = {}
        for t in qt:
            for did in self._inv.get(t, set()):
                scores[did] = scores.get(did, 0) + 1
        results: list[SearchResult] = []
        for did, sc in scores.items():
            e = self._index[did]
            if filters:
                if "status" in filters and e["status"] != filters["status"]:
                    continue
                if "tags" in filters and not any(t in e["tags"] for t in filters["tags"]):
                    continue
            results.append(SearchResult(did, e["title"], self._snippet(e["content"], qt),
                                        sc / len(qt), self._highlights(e["content"], qt), ["title", "content"]))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]
    def suggest(self, partial: str, limit: int = 5) -> list[str]:
        p = partial.lower()
        return sorted(t for t in self._inv if t.startswith(p))[:limit]
    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [t.lower() for t in re.findall(r"\b\w+\b", text) if len(t) > 1]
    @staticmethod
    def _snippet(content: str, qt: list[str], ctx: int = 40) -> str:
        cl = content.lower()
        for t in qt:
            pos = cl.find(t)
            if pos >= 0:
                return "..." + content[max(0, pos - ctx):pos + len(t) + ctx] + "..."
        return content[:80] + "..." if len(content) > 80 else content
    @staticmethod
    def _highlights(content: str, qt: list[str]) -> list[str]:
        sents = re.split(r"[.!?]\s+", content)
        return [s.strip() for s in sents if any(t in s.lower() for t in qt)][:3]

class WorkflowState(Enum):
    DRAFT, IN_REVIEW, APPROVED, REJECTED, PUBLISHED, ARCHIVED = (
        "draft", "in_review", "approved", "rejected", "published", "archived")

@dataclass
class ApprovalStep:
    step_id: str
    name: str
    approver_ids: list[str]
    order: int
    is_parallel: bool = False
    status: str = "pending"
    decided_by: str | None = None
    decided_at: float | None = None
    comment: str = ""

@dataclass
class WorkflowTransition:
    from_state: WorkflowState
    to_state: WorkflowState
    action: str
    required_role: str | None = None

class DocumentWorkflow:
    TRANSITIONS = [
        WorkflowTransition(WorkflowState.DRAFT, WorkflowState.IN_REVIEW, "submit"),
        WorkflowTransition(WorkflowState.IN_REVIEW, WorkflowState.APPROVED, "approve", "approver"),
        WorkflowTransition(WorkflowState.IN_REVIEW, WorkflowState.REJECTED, "reject", "approver"),
        WorkflowTransition(WorkflowState.REJECTED, WorkflowState.DRAFT, "revise"),
        WorkflowTransition(WorkflowState.APPROVED, WorkflowState.PUBLISHED, "publish", "owner"),
        WorkflowTransition(WorkflowState.PUBLISHED, WorkflowState.ARCHIVED, "archive", "owner"),
        WorkflowTransition(WorkflowState.ARCHIVED, WorkflowState.DRAFT, "restore", "owner"),
    ]
    def __init__(self, document_id: str, owner_id: str):
        self.document_id, self.owner_id = document_id, owner_id
        self.state = WorkflowState.DRAFT
        self.steps: list[ApprovalStep] = []
        self.history: list[dict[str, Any]] = []
        self._default_steps()
    def _default_steps(self) -> None:
        self.steps = [ApprovalStep(str(uuid.uuid4())[:8], n, [], i)
                      for i, n in enumerate(["Manager Review", "Legal Review", "Final Approval"], 1)]
    def configure_steps(self, steps: list[ApprovalStep]) -> None:
        self.steps = sorted(steps, key=lambda s: s.order)
    def submit_for_review(self, uid: str) -> bool:
        return self._tr(WorkflowState.IN_REVIEW, "submit", uid)
    def approve(self, sid: str, uid: str, comment: str = "") -> bool:
        step = next((s for s in self.steps if s.step_id == sid), None)
        if not step or self.state != WorkflowState.IN_REVIEW:
            return False
        if step.approver_ids and uid not in step.approver_ids:
            return False
        step.status, step.decided_by, step.decided_at, step.comment = "approved", uid, time.time(), comment
        self._log("approve", uid, {"step": sid, "comment": comment})
        if all(s.status == "approved" for s in self.steps):
            self.state = WorkflowState.APPROVED
            self._log("auto", "system", {"to": "approved"})
        return True
    def reject(self, sid: str, uid: str, reason: str = "") -> bool:
        step = next((s for s in self.steps if s.step_id == sid), None)
        if not step or self.state != WorkflowState.IN_REVIEW:
            return False
        step.status, step.decided_by, step.decided_at, step.comment = "rejected", uid, time.time(), reason
        self.state = WorkflowState.REJECTED
        self._log("reject", uid, {"step": sid, "reason": reason})
        return True
    def revise(self, uid: str) -> bool:
        if self.state != WorkflowState.REJECTED:
            return False
        for s in self.steps:
            s.status, s.decided_by, s.decided_at = "pending", None, None
        return self._tr(WorkflowState.DRAFT, "revise", uid)
    def publish(self, uid: str) -> bool:
        return uid == self.owner_id and self._tr(WorkflowState.PUBLISHED, "publish", uid)
    def archive(self, uid: str) -> bool:
        return uid == self.owner_id and self._tr(WorkflowState.ARCHIVED, "archive", uid)
    def get_progress(self) -> dict[str, Any]:
        total = len(self.steps)
        approved = sum(1 for s in self.steps if s.status == "approved")
        return {"state": self.state.value, "total_steps": total, "approved_steps": approved,
                "progress_pct": (approved / total * 100) if total else 0, "is_complete": approved == total}
    def _tr(self, to: WorkflowState, action: str, uid: str) -> bool:
        if not any(t.from_state == self.state and t.to_state == to and t.action == action
                   for t in self.TRANSITIONS):
            return False
        old, self.state = self.state, to
        self._log(action, uid, {"from": old.value, "to": to.value})
        return True
    def _log(self, action: str, uid: str, details: dict[str, Any]) -> None:
        self.history.append({"action": action, "user_id": uid, "timestamp": time.time(), "details": details})

class DocumentManager:
    def __init__(self):
        self.documents: dict[str, Document] = {}
        self.sessions: dict[str, CollaborationSession] = {}
        self.templates: dict[str, DocumentTemplate] = {}
        self.workflows: dict[str, DocumentWorkflow] = {}
        self.search = DocumentSearchEngine()
    def create_document(self, title: str, owner: str, content: str = "") -> Document:
        doc = Document(str(uuid.uuid4())[:8], title, owner)
        if content:
            doc.create_version(content, owner, "Initial version")
        self.documents[doc.document_id] = doc
        self.search.index_document(doc)
        return doc
    def get_document(self, did: str) -> Document | None:
        return self.documents.get(did)
    def start_collaboration(self, did: str) -> CollaborationSession:
        if did not in self.sessions:
            self.sessions[did] = CollaborationSession(did)
        return self.sessions[did]
    def create_template(self, name: str, content: str, category: str = "general") -> DocumentTemplate:
        t = DocumentTemplate(str(uuid.uuid4())[:8], name, content, category=category)
        self.templates[t.template_id] = t
        return t
    def create_workflow(self, did: str, owner: str) -> DocumentWorkflow:
        wf = DocumentWorkflow(did, owner)
        self.workflows[did] = wf
        return wf
    def search_docs(self, query: str, **filters: Any) -> list[SearchResult]:
        return self.search.search(query, filters=filters or None)
    def reindex_all(self) -> None:
        self.search = DocumentSearchEngine()
        for d in self.documents.values():
            self.search.index_document(d)

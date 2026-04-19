from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class BatchStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AuditEventType(StrEnum):
    SESSION_CREATED = "session_created"
    SNAPSHOT_STORED = "snapshot_stored"
    MIRROR_SYNCED = "mirror_synced"
    CHECKPOINT_CREATED = "checkpoint_created"
    BATCH_QUEUED = "batch_queued"
    BATCH_APPROVAL_REQUESTED = "batch_approval_requested"
    BATCH_APPROVED = "batch_approved"
    BATCH_REJECTED = "batch_rejected"
    BATCH_DISPATCHED = "batch_dispatched"
    BATCH_COMPLETED = "batch_completed"
    BATCH_FAILED = "batch_failed"
    ROLLBACK_REQUESTED = "rollback_requested"


SUPPORTED_OPERATION_KINDS = {
    "get_project_snapshot",
    "get_selection",
    "read_scripts",
    "apply_script_patch",
    "create_instance",
    "update_properties",
    "reparent_instance",
    "delete_instance",
    "run_playtest",
    "collect_output",
    "create_checkpoint",
    "rollback_checkpoint",
}

HIGH_RISK_OPERATION_KINDS = {"delete_instance", "rollback_checkpoint"}
MEDIUM_RISK_OPERATION_KINDS = {
    "apply_script_patch",
    "create_instance",
    "update_properties",
    "reparent_instance",
    "run_playtest",
}
DESTRUCTIVE_OPERATION_KINDS = {"delete_instance", "rollback_checkpoint"}
MUTATING_OPERATION_KINDS = {
    "apply_script_patch",
    "create_instance",
    "update_properties",
    "reparent_instance",
    "delete_instance",
    "create_checkpoint",
    "rollback_checkpoint",
}

READ_OPERATION_KINDS = {
    "get_project_snapshot",
    "get_selection",
    "read_scripts",
    "collect_output",
}


def risk_for_kind(kind: str) -> RiskLevel:
    if kind in HIGH_RISK_OPERATION_KINDS:
        return RiskLevel.HIGH
    if kind in MEDIUM_RISK_OPERATION_KINDS:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


@dataclass(slots=True)
class ValidationIssue:
    severity: IssueSeverity
    code: str
    message: str
    operation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "operation_id": self.operation_id,
        }


@dataclass(slots=True)
class Operation:
    operation_id: str
    kind: str
    target_path: str
    payload: dict[str, Any] = field(default_factory=dict)
    preconditions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Operation":
        return cls(
            operation_id=str(raw["operation_id"]),
            kind=str(raw["kind"]),
            target_path=str(raw.get("target_path", "")),
            payload=dict(raw.get("payload", {})),
            preconditions=dict(raw.get("preconditions", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "kind": self.kind,
            "target_path": self.target_path,
            "payload": self.payload,
            "preconditions": self.preconditions,
            "risk_level": risk_for_kind(self.kind).value,
        }


@dataclass(slots=True)
class OperationOutcome:
    operation_id: str
    success: bool
    message: str
    changed_paths: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "OperationOutcome":
        return cls(
            operation_id=str(raw["operation_id"]),
            success=bool(raw["success"]),
            message=str(raw.get("message", "")),
            changed_paths=[str(item) for item in raw.get("changed_paths", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "success": self.success,
            "message": self.message,
            "changed_paths": list(self.changed_paths),
        }


@dataclass(slots=True)
class ScriptDocument:
    path: str
    name: str
    class_name: str
    source: str
    source_sha256: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ScriptDocument":
        return cls(
            path=str(raw["path"]),
            name=str(raw["name"]),
            class_name=str(raw["class_name"]),
            source=str(raw.get("source", "")),
            source_sha256=str(raw.get("source_sha256", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "class_name": self.class_name,
            "source": self.source,
            "source_sha256": self.source_sha256,
        }


@dataclass(slots=True)
class SnapshotNode:
    path: str
    name: str
    class_name: str
    script_source: str | None = None
    source_sha256: str | None = None
    child_count: int = 0
    is_selected: bool = False
    children: list["SnapshotNode"] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SnapshotNode":
        return cls(
            path=str(raw["path"]),
            name=str(raw["name"]),
            class_name=str(raw["class_name"]),
            script_source=raw.get("script_source"),
            source_sha256=raw.get("source_sha256"),
            child_count=int(raw.get("child_count", 0)),
            is_selected=bool(raw.get("is_selected", False)),
            children=[cls.from_dict(child) for child in raw.get("children", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "class_name": self.class_name,
            "script_source": self.script_source,
            "source_sha256": self.source_sha256,
            "child_count": self.child_count,
            "is_selected": self.is_selected,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass(slots=True)
class ProjectSnapshot:
    captured_at: str
    project_name: str | None = None
    selection_paths: list[str] = field(default_factory=list)
    nodes: list[SnapshotNode] = field(default_factory=list)
    selection_nodes: list[SnapshotNode] = field(default_factory=list)
    script_documents: list[ScriptDocument] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ProjectSnapshot":
        return cls(
            captured_at=str(raw["captured_at"]),
            project_name=raw.get("project_name"),
            selection_paths=[str(item) for item in raw.get("selection_paths", [])],
            nodes=[SnapshotNode.from_dict(node) for node in raw.get("nodes", [])],
            selection_nodes=[
                SnapshotNode.from_dict(node) for node in raw.get("selection_nodes", [])
            ],
            script_documents=[
                ScriptDocument.from_dict(item) for item in raw.get("script_documents", [])
            ],
            diagnostics=[dict(item) for item in raw.get("diagnostics", [])],
            metadata=dict(raw.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "captured_at": self.captured_at,
            "project_name": self.project_name,
            "selection_paths": list(self.selection_paths),
            "nodes": [node.to_dict() for node in self.nodes],
            "selection_nodes": [node.to_dict() for node in self.selection_nodes],
            "script_documents": [document.to_dict() for document in self.script_documents],
            "diagnostics": list(self.diagnostics),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class Checkpoint:
    checkpoint_id: str
    label: str
    created_at: str
    snapshot_digest: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "label": self.label,
            "created_at": self.created_at,
            "snapshot_digest": self.snapshot_digest,
        }


@dataclass(slots=True)
class AuditEvent:
    event_type: AuditEventType
    created_at: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "created_at": self.created_at,
            "details": self.details,
        }


@dataclass(slots=True)
class OperationBatch:
    batch_id: str
    session_id: str
    operations: list[Operation]
    status: BatchStatus
    created_at: str
    checkpoint_id: str | None = None
    requires_approval: bool = False
    approved_at: str | None = None
    approval_note: str | None = None
    rejected_at: str | None = None
    outcomes: list[OperationOutcome] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "checkpoint_id": self.checkpoint_id,
            "requires_approval": self.requires_approval,
            "approved_at": self.approved_at,
            "approval_note": self.approval_note,
            "rejected_at": self.rejected_at,
            "operations": [operation.to_dict() for operation in self.operations],
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
        }


@dataclass(slots=True)
class MirrorState:
    root_dir: str
    manifest_path: str
    snapshot_path: str
    scripts_dir: str
    last_sync_at: str | None = None
    snapshot_digest: str | None = None
    script_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_dir": self.root_dir,
            "manifest_path": self.manifest_path,
            "snapshot_path": self.snapshot_path,
            "scripts_dir": self.scripts_dir,
            "last_sync_at": self.last_sync_at,
            "snapshot_digest": self.snapshot_digest,
            "script_count": self.script_count,
        }


@dataclass(slots=True)
class SessionContext:
    session_id: str
    client_name: str
    project_root: str
    created_at: str
    capabilities: dict[str, Any] = field(default_factory=dict)
    mirror: MirrorState | None = None
    latest_snapshot: ProjectSnapshot | None = None
    checkpoints: dict[str, Checkpoint] = field(default_factory=dict)
    batches: dict[str, OperationBatch] = field(default_factory=dict)
    audit_log: list[AuditEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "client_name": self.client_name,
            "project_root": self.project_root,
            "created_at": self.created_at,
            "capabilities": self.capabilities,
            "mirror": None if self.mirror is None else self.mirror.to_dict(),
            "latest_snapshot": None if self.latest_snapshot is None else self.latest_snapshot.to_dict(),
            "checkpoints": [checkpoint.to_dict() for checkpoint in self.checkpoints.values()],
            "batches": [batch.to_dict() for batch in self.batches.values()],
            "audit_log": [entry.to_dict() for entry in self.audit_log],
        }

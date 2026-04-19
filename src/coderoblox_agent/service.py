from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from .mirror import LocalMirror, build_mirror_state, resolve_workspace_root
from .models import (
    AuditEvent,
    AuditEventType,
    BatchStatus,
    Checkpoint,
    DESTRUCTIVE_OPERATION_KINDS,
    IssueSeverity,
    MUTATING_OPERATION_KINDS,
    Operation,
    OperationBatch,
    OperationOutcome,
    ProjectSnapshot,
    READ_OPERATION_KINDS,
    ScriptDocument,
    SUPPORTED_OPERATION_KINDS,
    SessionContext,
    ValidationIssue,
    risk_for_kind,
)


class AgentError(Exception):
    """Base error for the local agent."""


class SessionNotFoundError(AgentError):
    """Raised when a session does not exist."""


class BatchNotFoundError(AgentError):
    """Raised when a batch does not exist."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def snapshot_digest(snapshot: ProjectSnapshot | None) -> str | None:
    if snapshot is None:
        return None

    payload = json.dumps(snapshot.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_digest(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def enrich_snapshot(snapshot: ProjectSnapshot) -> ProjectSnapshot:
    unique_documents: dict[str, ScriptDocument] = {}
    for document in snapshot.script_documents:
        if not document.source_sha256:
            document.source_sha256 = source_digest(document.source)
        unique_documents[document.path] = document
    snapshot.script_documents = list(unique_documents.values())

    def enrich_nodes(nodes: list[Any]) -> None:
        for node in nodes:
            if node.script_source is not None and not node.source_sha256:
                node.source_sha256 = source_digest(node.script_source)
            enrich_nodes(node.children)

    enrich_nodes(snapshot.nodes)
    enrich_nodes(snapshot.selection_nodes)
    snapshot.metadata = {
        **snapshot.metadata,
        "script_count": len(snapshot.script_documents),
    }
    return snapshot


class AgentService:
    """Coordinates Studio sessions, queued operations, checkpoints, and audit logs."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionContext] = {}
        self._mirror = LocalMirror()

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "supported_operations": sorted(SUPPORTED_OPERATION_KINDS),
            "read_operations": sorted(READ_OPERATION_KINDS),
            "mutating_operations": sorted(MUTATING_OPERATION_KINDS),
            "session_count": len(self._sessions),
        }

    def start_session(
        self,
        client_name: str,
        project_root: str,
        capabilities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session_id = f"session-{uuid.uuid4().hex[:12]}"
        workspace_root = resolve_workspace_root(project_root)
        normalized_project_root = str(workspace_root)
        session = SessionContext(
            session_id=session_id,
            client_name=client_name,
            project_root=normalized_project_root,
            created_at=utc_now(),
            capabilities=capabilities or {},
            mirror=build_mirror_state(
                session_id=session_id,
                project_root=normalized_project_root,
                project_name=None,
            ),
        )
        session.audit_log.append(
            AuditEvent(
                event_type=AuditEventType.SESSION_CREATED,
                created_at=utc_now(),
                details={
                    "client_name": client_name,
                    "project_root": normalized_project_root,
                    "mirror_root": None if session.mirror is None else session.mirror.root_dir,
                },
            )
        )
        self._sessions[session_id] = session
        self._mirror.ensure_session(session)
        return {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "supported_operations": sorted(SUPPORTED_OPERATION_KINDS),
            "project_root": session.project_root,
            "mirror": None if session.mirror is None else session.mirror.to_dict(),
        }

    def get_session(self, session_id: str) -> SessionContext:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise SessionNotFoundError(f"Unknown session: {session_id}") from exc

    def store_snapshot(self, session_id: str, snapshot: ProjectSnapshot) -> dict[str, Any]:
        session = self.get_session(session_id)
        snapshot = enrich_snapshot(snapshot)
        session.latest_snapshot = snapshot
        digest = snapshot_digest(snapshot)
        mirror = self._mirror.sync_snapshot(
            session=session,
            snapshot=snapshot,
            snapshot_digest=digest,
            synced_at=utc_now(),
        )
        session.audit_log.append(
            AuditEvent(
                event_type=AuditEventType.SNAPSHOT_STORED,
                created_at=utc_now(),
                details={
                    "captured_at": snapshot.captured_at,
                    "selection_paths": snapshot.selection_paths,
                    "snapshot_digest": digest,
                },
            )
        )
        session.audit_log.append(
            AuditEvent(
                event_type=AuditEventType.MIRROR_SYNCED,
                created_at=utc_now(),
                details=mirror.to_dict(),
            )
        )
        return {
            "session_id": session_id,
            "snapshot_digest": digest,
            "mirror": mirror.to_dict(),
        }

    def get_snapshot(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        return {
            "session_id": session_id,
            "mirror": None if session.mirror is None else session.mirror.to_dict(),
            "snapshot": None
            if session.latest_snapshot is None
            else session.latest_snapshot.to_dict(),
        }

    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        return {"session": session.to_dict()}

    def get_mirror_status(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        return {
            "session_id": session_id,
            "mirror": None if session.mirror is None else session.mirror.to_dict(),
        }

    def get_audit_log(self, session_id: str, limit: int | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        entries = session.audit_log if limit is None else session.audit_log[-limit:]
        return {
            "session_id": session_id,
            "audit_log": [entry.to_dict() for entry in entries],
        }

    def _require_snapshot(self, session_id: str) -> ProjectSnapshot:
        session = self.get_session(session_id)
        if session.latest_snapshot is None:
            raise AgentError(f"Session {session_id} does not have a snapshot yet.")
        return session.latest_snapshot

    def read_scripts(
        self,
        session_id: str,
        paths: list[str] | None = None,
        include_source: bool = True,
    ) -> dict[str, Any]:
        snapshot = self._require_snapshot(session_id)
        requested = None if paths is None else {path for path in paths}
        documents: list[ScriptDocument] = []

        for document in snapshot.script_documents:
            if requested is not None and document.path not in requested:
                continue
            if include_source:
                documents.append(document)
            else:
                documents.append(
                    ScriptDocument(
                        path=document.path,
                        name=document.name,
                        class_name=document.class_name,
                        source="",
                        source_sha256=document.source_sha256,
                    )
                )

        missing_paths = []
        if requested is not None:
            found_paths = {document.path for document in documents}
            missing_paths = sorted(requested - found_paths)

        return {
            "session_id": session_id,
            "scripts": [document.to_dict() for document in documents],
            "missing_paths": missing_paths,
        }

    def get_pending_batch(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        pending_batches = [
            batch
            for batch in session.batches.values()
            if batch.status == BatchStatus.PENDING_APPROVAL
        ]
        pending_batches.sort(key=lambda batch: batch.created_at)
        if not pending_batches:
            return {"batch": None}

        return {"batch": pending_batches[0].to_dict()}

    def _create_auto_checkpoint(self, session: SessionContext) -> Checkpoint:
        checkpoint = Checkpoint(
            checkpoint_id=f"chk-{uuid.uuid4().hex[:12]}",
            label=f"auto-before-{len(session.batches) + 1}",
            created_at=utc_now(),
            snapshot_digest=snapshot_digest(session.latest_snapshot),
        )
        session.checkpoints[checkpoint.checkpoint_id] = checkpoint
        session.audit_log.append(
            AuditEvent(
                event_type=AuditEventType.CHECKPOINT_CREATED,
                created_at=utc_now(),
                details=checkpoint.to_dict(),
            )
        )
        return checkpoint

    def validate_operations(
        self,
        session_id: str,
        operations: list[Operation],
        allow_destructive: bool = False,
    ) -> dict[str, Any]:
        self.get_session(session_id)
        issues: list[ValidationIssue] = []
        operation_ids = Counter(operation.operation_id for operation in operations)
        risk_summary = Counter(risk_for_kind(operation.kind).value for operation in operations)
        kind_summary = Counter(operation.kind for operation in operations)

        for operation in operations:
            if operation_ids[operation.operation_id] > 1:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="duplicate_operation_id",
                        message="Operation ids must be unique within a batch.",
                        operation_id=operation.operation_id,
                    )
                )

            if operation.kind not in SUPPORTED_OPERATION_KINDS:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="unsupported_operation",
                        message=f"Unsupported operation kind: {operation.kind}",
                        operation_id=operation.operation_id,
                    )
                )
                continue

            if operation.kind in DESTRUCTIVE_OPERATION_KINDS and not allow_destructive:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="destructive_operation_requires_approval",
                        message="Destructive operations require explicit approval.",
                        operation_id=operation.operation_id,
                    )
                )

            if operation.kind in READ_OPERATION_KINDS:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="read_operation_not_queueable",
                        message=(
                            f"{operation.kind} should be handled through the agent read APIs, "
                            "not through queued plugin batches."
                        ),
                        operation_id=operation.operation_id,
                    )
                )
                continue

            if operation.kind == "apply_script_patch":
                if not isinstance(operation.payload.get("script_source"), str):
                    issues.append(
                        ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            code="missing_script_source",
                            message="apply_script_patch requires payload.script_source.",
                            operation_id=operation.operation_id,
                        )
                    )
                if not isinstance(operation.preconditions.get("expected_sha256"), str):
                    expected_source = operation.preconditions.get("expected_source")
                    if not isinstance(expected_source, str):
                        issues.append(
                            ValidationIssue(
                                severity=IssueSeverity.ERROR,
                                code="missing_expected_revision",
                                message=(
                                    "apply_script_patch requires either "
                                    "preconditions.expected_sha256 or "
                                    "preconditions.expected_source."
                                ),
                                operation_id=operation.operation_id,
                            )
                        )
                snapshot = self.get_session(session_id).latest_snapshot
                if snapshot is not None:
                    script_by_path = {
                        document.path: document for document in snapshot.script_documents
                    }
                    document = script_by_path.get(operation.target_path)
                    if document is None:
                        issues.append(
                            ValidationIssue(
                                severity=IssueSeverity.ERROR,
                                code="unknown_script_target",
                                message=(
                                    "apply_script_patch target was not found in the latest snapshot."
                                ),
                                operation_id=operation.operation_id,
                            )
                        )
                    else:
                        expected_sha = operation.preconditions.get("expected_sha256")
                        if (
                            isinstance(expected_sha, str)
                            and expected_sha != ""
                            and expected_sha != document.source_sha256
                        ):
                            issues.append(
                                ValidationIssue(
                                    severity=IssueSeverity.ERROR,
                                    code="stale_script_revision",
                                    message=(
                                        "apply_script_patch was prepared against an older script "
                                        "revision. Refresh Studio context before queuing it."
                                    ),
                                    operation_id=operation.operation_id,
                                )
                            )
                        expected_source = operation.preconditions.get("expected_source")
                        if (
                            isinstance(expected_source, str)
                            and expected_source != document.source
                        ):
                            issues.append(
                                ValidationIssue(
                                    severity=IssueSeverity.ERROR,
                                    code="stale_script_source",
                                    message=(
                                        "apply_script_patch expected_source does not match the "
                                        "latest Studio snapshot."
                                    ),
                                    operation_id=operation.operation_id,
                                )
                            )

            if operation.kind == "create_instance":
                if not isinstance(operation.payload.get("class_name"), str):
                    issues.append(
                        ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            code="missing_class_name",
                            message="create_instance requires payload.class_name.",
                            operation_id=operation.operation_id,
                        )
                    )
                if not isinstance(operation.payload.get("parent_path"), str):
                    issues.append(
                        ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            code="missing_parent_path",
                            message="create_instance requires payload.parent_path.",
                            operation_id=operation.operation_id,
                        )
                    )
                if not isinstance(operation.payload.get("name"), str):
                    issues.append(
                        ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            code="missing_name",
                            message="create_instance requires payload.name.",
                            operation_id=operation.operation_id,
                        )
                    )

            if operation.kind == "update_properties" and not isinstance(
                operation.payload.get("properties"), dict
            ):
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="missing_properties",
                        message="update_properties requires payload.properties.",
                        operation_id=operation.operation_id,
                    )
                )

            if operation.kind == "reparent_instance" and not isinstance(
                operation.payload.get("new_parent_path"), str
            ):
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="missing_new_parent_path",
                        message="reparent_instance requires payload.new_parent_path.",
                        operation_id=operation.operation_id,
                    )
                )

            if operation.kind == "rollback_checkpoint" and not isinstance(
                operation.payload.get("checkpoint_id"), str
            ):
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="missing_checkpoint_id",
                        message="rollback_checkpoint requires payload.checkpoint_id.",
                        operation_id=operation.operation_id,
                    )
                )

        return {
            "allowed": not any(issue.severity == IssueSeverity.ERROR for issue in issues),
            "issues": [issue.to_dict() for issue in issues],
            "summary": {
                "total": len(operations),
                "destructive": sum(
                    1 for operation in operations if operation.kind in DESTRUCTIVE_OPERATION_KINDS
                ),
                "risk_levels": dict(risk_summary),
                "by_kind": dict(kind_summary),
            },
        }

    def create_checkpoint(self, session_id: str, label: str) -> Checkpoint:
        session = self.get_session(session_id)
        checkpoint = Checkpoint(
            checkpoint_id=f"chk-{uuid.uuid4().hex[:12]}",
            label=label,
            created_at=utc_now(),
            snapshot_digest=snapshot_digest(session.latest_snapshot),
        )
        session.checkpoints[checkpoint.checkpoint_id] = checkpoint
        session.audit_log.append(
            AuditEvent(
                event_type=AuditEventType.CHECKPOINT_CREATED,
                created_at=utc_now(),
                details=checkpoint.to_dict(),
            )
        )
        return checkpoint

    def queue_operations(
        self,
        session_id: str,
        operations: list[Operation],
        allow_destructive: bool = False,
    ) -> dict[str, Any]:
        session = self.get_session(session_id)
        validation = self.validate_operations(
            session_id=session_id,
            operations=operations,
            allow_destructive=allow_destructive,
        )
        if not validation["allowed"]:
            return {"queued": False, "validation": validation}

        requires_approval = any(operation.kind in MUTATING_OPERATION_KINDS for operation in operations)
        checkpoint_id = None

        batch = OperationBatch(
            batch_id=f"batch-{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            operations=operations,
            status=BatchStatus.PENDING_APPROVAL if requires_approval else BatchStatus.QUEUED,
            created_at=utc_now(),
            checkpoint_id=checkpoint_id,
            requires_approval=requires_approval,
        )
        session.batches[batch.batch_id] = batch
        session.audit_log.append(
            AuditEvent(
                event_type=(
                    AuditEventType.BATCH_APPROVAL_REQUESTED
                    if requires_approval
                    else AuditEventType.BATCH_QUEUED
                ),
                created_at=utc_now(),
                details={"batch_id": batch.batch_id, "checkpoint_id": checkpoint_id},
            )
        )
        return {"queued": True, "validation": validation, "batch": batch.to_dict()}

    def approve_batch(self, session_id: str, batch_id: str, note: str = "") -> dict[str, Any]:
        session = self.get_session(session_id)
        try:
            batch = session.batches[batch_id]
        except KeyError as exc:
            raise BatchNotFoundError(f"Unknown batch: {batch_id}") from exc

        if batch.status != BatchStatus.PENDING_APPROVAL:
            raise AgentError(f"Batch {batch_id} is not pending approval.")

        if any(operation.kind in MUTATING_OPERATION_KINDS for operation in batch.operations):
            checkpoint = self._create_auto_checkpoint(session)
            batch.checkpoint_id = checkpoint.checkpoint_id

        batch.status = BatchStatus.QUEUED
        batch.approved_at = utc_now()
        batch.approval_note = note or None
        session.audit_log.append(
            AuditEvent(
                event_type=AuditEventType.BATCH_APPROVED,
                created_at=utc_now(),
                details={
                    "batch_id": batch_id,
                    "checkpoint_id": batch.checkpoint_id,
                    "note": batch.approval_note,
                },
            )
        )
        return {"batch": batch.to_dict()}

    def reject_batch(self, session_id: str, batch_id: str, reason: str = "") -> dict[str, Any]:
        session = self.get_session(session_id)
        try:
            batch = session.batches[batch_id]
        except KeyError as exc:
            raise BatchNotFoundError(f"Unknown batch: {batch_id}") from exc

        if batch.status != BatchStatus.PENDING_APPROVAL:
            raise AgentError(f"Batch {batch_id} is not pending approval.")

        batch.status = BatchStatus.REJECTED
        batch.rejected_at = utc_now()
        batch.approval_note = reason or None
        session.audit_log.append(
            AuditEvent(
                event_type=AuditEventType.BATCH_REJECTED,
                created_at=utc_now(),
                details={"batch_id": batch_id, "reason": batch.approval_note},
            )
        )
        return {"batch": batch.to_dict()}

    def next_batch(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        queued_batches = [
            batch for batch in session.batches.values() if batch.status == BatchStatus.QUEUED
        ]
        queued_batches.sort(key=lambda batch: batch.created_at)
        if not queued_batches:
            return {"batch": None}

        batch = queued_batches[0]
        batch.status = BatchStatus.DISPATCHED
        session.audit_log.append(
            AuditEvent(
                event_type=AuditEventType.BATCH_DISPATCHED,
                created_at=utc_now(),
                details={"batch_id": batch.batch_id},
            )
        )
        return {"batch": batch.to_dict()}

    def complete_batch(
        self,
        session_id: str,
        batch_id: str,
        outcomes: list[OperationOutcome],
    ) -> dict[str, Any]:
        session = self.get_session(session_id)
        try:
            batch = session.batches[batch_id]
        except KeyError as exc:
            raise BatchNotFoundError(f"Unknown batch: {batch_id}") from exc

        batch.outcomes = outcomes
        all_success = all(outcome.success for outcome in outcomes)
        batch.status = BatchStatus.COMPLETED if all_success else BatchStatus.FAILED
        event_type = (
            AuditEventType.BATCH_COMPLETED if all_success else AuditEventType.BATCH_FAILED
        )
        session.audit_log.append(
            AuditEvent(
                event_type=event_type,
                created_at=utc_now(),
                details={
                    "batch_id": batch_id,
                    "outcome_count": len(outcomes),
                    "status": batch.status.value,
                },
            )
        )
        return {"batch": batch.to_dict()}

    def queue_rollback(self, session_id: str, checkpoint_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        if checkpoint_id not in session.checkpoints:
            raise AgentError(f"Unknown checkpoint: {checkpoint_id}")

        operation = Operation(
            operation_id=f"rollback-{uuid.uuid4().hex[:8]}",
            kind="rollback_checkpoint",
            target_path="",
            payload={"checkpoint_id": checkpoint_id},
            preconditions={},
        )
        result = self.queue_operations(
            session_id=session_id,
            operations=[operation],
            allow_destructive=True,
        )
        session.audit_log.append(
            AuditEvent(
                event_type=AuditEventType.ROLLBACK_REQUESTED,
                created_at=utc_now(),
                details={"checkpoint_id": checkpoint_id},
            )
        )
        return result

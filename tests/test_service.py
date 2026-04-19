from __future__ import annotations

import hashlib
import json
import shutil
import unittest
from pathlib import Path

from coderoblox_agent.models import Operation, OperationOutcome, ProjectSnapshot, ScriptDocument
from coderoblox_agent.service import AgentService


def make_snapshot() -> ProjectSnapshot:
    return ProjectSnapshot(
        captured_at="2026-04-04T18:00:00+00:00",
        project_name="TestPlace",
        selection_paths=["Workspace/Baseplate"],
        nodes=[],
        selection_nodes=[],
        script_documents=[
            ScriptDocument(
                path="ReplicatedStorage/MyModule",
                name="MyModule",
                class_name="ModuleScript",
                source="return 1",
                source_sha256="",
            )
        ],
        diagnostics=[],
        metadata={"selected_count": 1},
    )


def patch_operation(operation_id: str = "op-1") -> Operation:
    return Operation(
        operation_id=operation_id,
        kind="apply_script_patch",
        target_path="ReplicatedStorage/MyModule",
        payload={"script_source": "return 2"},
        preconditions={
            "expected_sha256": hashlib.sha256("return 1".encode("utf-8")).hexdigest(),
            "expected_source": "return 1",
        },
    )


class AgentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path("test_artifacts") / "service"
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.project_root = self.temp_root / "workspace"
        if self.project_root.exists():
            shutil.rmtree(self.project_root)
        self.project_root.mkdir(parents=True, exist_ok=True)
        self.service = AgentService()
        session = self.service.start_session(
            client_name="test-suite",
            project_root=str(self.project_root.resolve()),
        )
        self.session_id = session["session_id"]
        self.service.store_snapshot(self.session_id, make_snapshot())

    def tearDown(self) -> None:
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_duplicate_operation_ids_are_blocked(self) -> None:
        operations = [patch_operation("duplicate"), patch_operation("duplicate")]

        report = self.service.validate_operations(self.session_id, operations)

        self.assertFalse(report["allowed"])
        self.assertTrue(
            any(issue["code"] == "duplicate_operation_id" for issue in report["issues"])
        )

    def test_script_patch_requires_revision_precondition(self) -> None:
        operation = patch_operation()
        operation.preconditions = {}

        report = self.service.validate_operations(self.session_id, [operation])

        self.assertFalse(report["allowed"])
        self.assertTrue(
            any(issue["code"] == "missing_expected_revision" for issue in report["issues"])
        )

    def test_script_patch_is_blocked_when_snapshot_hash_is_stale(self) -> None:
        operation = patch_operation()
        operation.preconditions["expected_sha256"] = "stale"

        report = self.service.validate_operations(self.session_id, [operation])

        self.assertFalse(report["allowed"])
        self.assertTrue(any(issue["code"] == "stale_script_revision" for issue in report["issues"]))

    def test_destructive_operations_require_explicit_approval(self) -> None:
        operation = Operation(
            operation_id="delete-1",
            kind="delete_instance",
            target_path="Workspace/OldPart",
        )

        report = self.service.validate_operations(self.session_id, [operation])

        self.assertFalse(report["allowed"])
        self.assertTrue(
            any(
                issue["code"] == "destructive_operation_requires_approval"
                for issue in report["issues"]
            )
        )

    def test_read_operations_are_not_queueable(self) -> None:
        report = self.service.validate_operations(
            self.session_id,
            [
                Operation(
                    operation_id="read-1",
                    kind="read_scripts",
                    target_path="ReplicatedStorage/MyModule",
                    payload={},
                    preconditions={},
                )
            ],
        )

        self.assertFalse(report["allowed"])
        self.assertTrue(
            any(issue["code"] == "read_operation_not_queueable" for issue in report["issues"])
        )

    def test_queue_mutating_batch_requires_plugin_approval(self) -> None:
        result = self.service.queue_operations(self.session_id, [patch_operation()])

        self.assertTrue(result["queued"])
        self.assertEqual(result["batch"]["status"], "pending_approval")
        self.assertTrue(result["batch"]["requires_approval"])

        pending = self.service.get_pending_batch(self.session_id)
        self.assertEqual(pending["batch"]["batch_id"], result["batch"]["batch_id"])

        approved = self.service.approve_batch(
            self.session_id,
            result["batch"]["batch_id"],
            "approved in test",
        )
        self.assertEqual(approved["batch"]["status"], "queued")
        self.assertIsNotNone(approved["batch"]["checkpoint_id"])

        next_batch = self.service.next_batch(self.session_id)
        self.assertEqual(next_batch["batch"]["batch_id"], result["batch"]["batch_id"])

        completion = self.service.complete_batch(
            self.session_id,
            result["batch"]["batch_id"],
            [
                OperationOutcome(
                    operation_id="op-1",
                    success=True,
                    message="Applied patch.",
                    changed_paths=["ReplicatedStorage/MyModule"],
                )
            ],
        )

        self.assertEqual(completion["batch"]["status"], "completed")
        audit = self.service.get_audit_log(self.session_id)["audit_log"]
        event_types = [entry["event_type"] for entry in audit]
        self.assertIn("batch_approval_requested", event_types)
        self.assertIn("batch_approved", event_types)
        self.assertIn("batch_dispatched", event_types)
        self.assertIn("batch_completed", event_types)

    def test_read_scripts_returns_latest_snapshot_documents(self) -> None:
        result = self.service.read_scripts(self.session_id, ["ReplicatedStorage/MyModule"])

        self.assertEqual(result["missing_paths"], [])
        self.assertEqual(result["scripts"][0]["path"], "ReplicatedStorage/MyModule")
        self.assertEqual(result["scripts"][0]["source"], "return 1")
        self.assertTrue(result["scripts"][0]["source_sha256"])

    def test_snapshot_sync_writes_git_friendly_local_mirror(self) -> None:
        session = self.service.get_session(self.session_id)
        self.assertIsNotNone(session.mirror)
        mirror_root = Path(session.mirror.root_dir)
        manifest_path = Path(session.mirror.manifest_path)
        snapshot_path = Path(session.mirror.snapshot_path)
        script_path = mirror_root / "scripts" / "ReplicatedStorage" / "MyModule.module.luau"

        self.assertTrue(mirror_root.is_dir())
        self.assertTrue(manifest_path.is_file())
        self.assertTrue(snapshot_path.is_file())
        self.assertTrue(script_path.is_file())
        self.assertEqual(script_path.read_text(encoding="utf-8"), "return 1")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["script_count"], 1)
        self.assertEqual(manifest["scripts"][0]["mirror_path"], "scripts/ReplicatedStorage/MyModule.module.luau")

    def test_reject_batch_marks_it_rejected(self) -> None:
        result = self.service.queue_operations(self.session_id, [patch_operation()])

        rejected = self.service.reject_batch(
            self.session_id,
            result["batch"]["batch_id"],
            "not safe enough",
        )

        self.assertEqual(rejected["batch"]["status"], "rejected")
        self.assertEqual(self.service.get_pending_batch(self.session_id)["batch"], None)

    def test_queue_rollback_creates_destructive_batch(self) -> None:
        checkpoint = self.service.create_checkpoint(self.session_id, "before-risky-change")

        result = self.service.queue_rollback(self.session_id, checkpoint.checkpoint_id)

        self.assertTrue(result["queued"])
        self.assertEqual(result["batch"]["operations"][0]["kind"], "rollback_checkpoint")
        self.assertEqual(result["batch"]["status"], "pending_approval")


if __name__ == "__main__":
    unittest.main()

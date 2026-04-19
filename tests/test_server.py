from __future__ import annotations

import hashlib
import json
import shutil
import threading
import unittest
from urllib import parse, request
from pathlib import Path

from coderoblox_agent.server import JsonHttpServer
from coderoblox_agent.service import AgentService


def json_request(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=5) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


class AgentServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path("test_artifacts") / "server"
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.project_root = self.temp_root / "workspace"
        if self.project_root.exists():
            shutil.rmtree(self.project_root)
        self.project_root.mkdir(parents=True, exist_ok=True)
        self.server = JsonHttpServer(("127.0.0.1", 0), AgentService())
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_health_endpoint(self) -> None:
        payload = json_request(f"{self.base_url}/health")

        self.assertEqual(payload["status"], "ok")
        self.assertGreater(len(payload["supported_operations"]), 0)
        self.assertIn("read_scripts", payload["read_operations"])

    def test_snapshot_script_and_approval_roundtrip(self) -> None:
        session = json_request(
            f"{self.base_url}/api/sessions",
            method="POST",
            payload={
                "client_name": "studio-plugin",
                "project_root": str(self.project_root.resolve()),
            },
        )
        session_id = session["session_id"]
        self.assertIn("mirror", session)

        json_request(
            f"{self.base_url}/api/snapshots",
            method="POST",
            payload={
                "session_id": session_id,
                "snapshot": {
                    "captured_at": "2026-04-04T18:00:00+00:00",
                    "project_name": "TestPlace",
                    "selection_paths": ["Workspace/Baseplate"],
                    "nodes": [],
                    "selection_nodes": [],
                    "script_documents": [
                        {
                            "path": "ReplicatedStorage/MyModule",
                            "name": "MyModule",
                            "class_name": "ModuleScript",
                            "source": "return 1",
                        }
                    ],
                    "diagnostics": [],
                    "metadata": {"selected_count": 1},
                },
            },
        )

        latest_snapshot = json_request(
            f"{self.base_url}/api/snapshots/latest?session_id={parse.quote(session_id)}"
        )
        self.assertEqual(latest_snapshot["snapshot"]["project_name"], "TestPlace")
        self.assertEqual(latest_snapshot["snapshot"]["metadata"]["script_count"], 1)
        self.assertTrue(latest_snapshot["mirror"]["root_dir"])

        mirror_status = json_request(
            f"{self.base_url}/api/mirror?session_id={parse.quote(session_id)}"
        )
        mirror_root = Path(mirror_status["mirror"]["root_dir"])
        self.assertTrue((mirror_root / "mirror_manifest.json").is_file())
        self.assertTrue((mirror_root / "scripts" / "ReplicatedStorage" / "MyModule.module.luau").is_file())

        scripts = json_request(
            (
                f"{self.base_url}/api/scripts?session_id={parse.quote(session_id)}"
                "&path=ReplicatedStorage/MyModule"
            )
        )
        self.assertEqual(scripts["scripts"][0]["source"], "return 1")
        self.assertTrue(scripts["scripts"][0]["source_sha256"])

        queue_result = json_request(
            f"{self.base_url}/api/operations/queue",
            method="POST",
            payload={
                "session_id": session_id,
                "operations": [
                    {
                        "operation_id": "op-1",
                        "kind": "apply_script_patch",
                        "target_path": "ReplicatedStorage/MyModule",
                        "payload": {"script_source": "return 2"},
                        "preconditions": {
                            "expected_sha256": hashlib.sha256(
                                "return 1".encode("utf-8")
                            ).hexdigest(),
                            "expected_source": "return 1",
                        },
                    }
                ],
            },
        )
        self.assertEqual(queue_result["batch"]["status"], "pending_approval")

        pending = json_request(
            f"{self.base_url}/api/operations/pending?session_id={parse.quote(session_id)}"
        )
        batch = pending["batch"]
        self.assertEqual(batch["batch_id"], queue_result["batch"]["batch_id"])

        approved = json_request(
            f"{self.base_url}/api/operations/approve",
            method="POST",
            payload={
                "session_id": session_id,
                "batch_id": batch["batch_id"],
                "note": "approved in server test",
            },
        )
        self.assertEqual(approved["batch"]["status"], "queued")
        self.assertIsNotNone(approved["batch"]["checkpoint_id"])

        next_batch = json_request(
            f"{self.base_url}/api/operations/next?session_id={parse.quote(session_id)}",
            method="GET",
        )
        self.assertEqual(next_batch["batch"]["status"], "dispatched")

        completion = json_request(
            f"{self.base_url}/api/operations/result",
            method="POST",
            payload={
                "session_id": session_id,
                "batch_id": batch["batch_id"],
                "outcomes": [
                    {
                        "operation_id": "op-1",
                        "success": True,
                        "message": "Applied patch.",
                        "changed_paths": ["ReplicatedStorage/MyModule"],
                    }
                ],
            },
        )
        self.assertEqual(completion["batch"]["status"], "completed")

        session_summary = json_request(
            f"{self.base_url}/api/sessions?session_id={parse.quote(session_id)}"
        )
        self.assertEqual(session_summary["session"]["session_id"], session_id)

        audit = json_request(
            f"{self.base_url}/api/audit?session_id={parse.quote(session_id)}"
        )
        event_types = [entry["event_type"] for entry in audit["audit_log"]]
        self.assertIn("snapshot_stored", event_types)
        self.assertIn("batch_approval_requested", event_types)
        self.assertIn("batch_approved", event_types)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

from .models import MirrorState, ProjectSnapshot, SessionContext


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return slug or "studio-session"


def _safe_path_segments(path: str) -> list[str]:
    segments = [segment for segment in path.replace("\\", "/").split("/") if segment]
    return [_slugify(segment) for segment in segments]


def _script_extension(class_name: str) -> str:
    if class_name == "Script":
        return ".server.luau"
    if class_name == "LocalScript":
        return ".client.luau"
    if class_name == "ModuleScript":
        return ".module.luau"
    return ".luau"


def resolve_workspace_root(project_root: str) -> Path:
    if project_root:
        candidate = Path(project_root).expanduser()
        if candidate.is_dir():
            return candidate.resolve()

    env_root = os.environ.get("CODEROBLOX_ROOT")
    if env_root:
        candidate = Path(env_root).expanduser()
        if candidate.is_dir():
            return candidate.resolve()

    return Path.cwd().resolve()


def build_mirror_state(
    session_id: str,
    project_root: str,
    project_name: str | None,
) -> MirrorState:
    workspace_root = resolve_workspace_root(project_root)
    mirror_name = _slugify(project_name or session_id)
    mirror_root = workspace_root / "studio_mirror" / mirror_name
    return MirrorState(
        root_dir=str(mirror_root),
        manifest_path=str(mirror_root / "mirror_manifest.json"),
        snapshot_path=str(mirror_root / "snapshot.json"),
        scripts_dir=str(mirror_root / "scripts"),
    )


class LocalMirror:
    def ensure_session(self, session: SessionContext) -> MirrorState:
        if session.mirror is None:
            project_name = None if session.latest_snapshot is None else session.latest_snapshot.project_name
            session.mirror = build_mirror_state(session.session_id, session.project_root, project_name)

        root_dir = Path(session.mirror.root_dir)
        root_dir.mkdir(parents=True, exist_ok=True)
        Path(session.mirror.scripts_dir).mkdir(parents=True, exist_ok=True)
        return session.mirror

    def sync_snapshot(
        self,
        session: SessionContext,
        snapshot: ProjectSnapshot,
        snapshot_digest: str | None,
        synced_at: str,
    ) -> MirrorState:
        mirror = self.ensure_session(session)
        root_dir = Path(mirror.root_dir)
        scripts_dir = Path(mirror.scripts_dir)
        if scripts_dir.exists():
            shutil.rmtree(scripts_dir)
        scripts_dir.mkdir(parents=True, exist_ok=True)

        written_script_paths: list[str] = []
        script_entries: list[dict[str, str]] = []
        for document in snapshot.script_documents:
            relative_segments = _safe_path_segments(document.path)
            if not relative_segments:
                continue

            relative_path = Path(*relative_segments)
            script_path = scripts_dir / relative_path
            script_path = script_path.with_suffix(_script_extension(document.class_name))
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text(document.source, encoding="utf-8")
            written_script_paths.append(str(script_path.resolve()))
            script_entries.append(
                {
                    "roblox_path": document.path,
                    "class_name": document.class_name,
                    "source_sha256": document.source_sha256,
                    "mirror_path": str(script_path.relative_to(root_dir)).replace("\\", "/"),
                }
            )

        snapshot_payload = {
            **snapshot.to_dict(),
            "mirror": {
                "root_dir": mirror.root_dir,
                "scripts_dir": mirror.scripts_dir,
                "script_entries": script_entries,
            },
        }
        Path(mirror.snapshot_path).write_text(
            json.dumps(snapshot_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        manifest = {
            "session_id": session.session_id,
            "client_name": session.client_name,
            "project_root": session.project_root,
            "project_name": snapshot.project_name,
            "last_sync_at": synced_at,
            "snapshot_digest": snapshot_digest,
            "script_count": len(script_entries),
            "selection_paths": snapshot.selection_paths,
            "files": {
                "snapshot": str(Path(mirror.snapshot_path).relative_to(root_dir)).replace("\\", "/"),
                "scripts_dir": str(Path(mirror.scripts_dir).relative_to(root_dir)).replace("\\", "/"),
            },
            "scripts": script_entries,
        }
        Path(mirror.manifest_path).write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        mirror.last_sync_at = synced_at
        mirror.snapshot_digest = snapshot_digest
        mirror.script_count = len(script_entries)
        return mirror

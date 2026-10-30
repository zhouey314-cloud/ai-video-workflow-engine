"""Per-job delivery bundles with reproducible checksums and fail-closed verification."""

from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from .engine import run


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def verify_bundle(directory):
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("REGULAR_BUNDLE_DIRECTORY_REQUIRED")
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or manifest_path.stat().st_size > 1024 * 1024:
        raise ValueError("INVALID_MANIFEST")
    manifest = json.loads(manifest_path.read_text())
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or not isinstance(manifest.get("files"), list)
        or not manifest["files"]
    ):
        raise ValueError("INVALID_MANIFEST")
    seen = set()
    for record in manifest["files"]:
        if (
            not isinstance(record, dict)
            or type(record.get("bytes")) is not int
            or record["bytes"] < 0
            or not isinstance(record.get("sha256"), str)
            or len(record["sha256"]) != 64
        ):
            raise ValueError("INVALID_FILE_RECORD")
        name = record.get("path")
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or "/" in name
            or "\\" in name
            or name in {".", "..", "manifest.json"}
            or name in seen
        ):
            raise ValueError("INVALID_BUNDLE_PATH")
        seen.add(name)
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("BUNDLE_FILE_MISSING_OR_UNSAFE")
        if path.stat().st_size != record["bytes"] or digest(path) != record["sha256"]:
            raise ValueError("BUNDLE_CHECKSUM_MISMATCH:" + name)
    if {p.name for p in root.iterdir()} != seen | {"manifest.json"}:
        raise ValueError("UNLISTED_BUNDLE_FILES")
    if "report.json" not in seen:
        raise ValueError("BUNDLE_REPORT_REQUIRED")
    report = json.loads((root / "report.json").read_text())
    if (
        not isinstance(report, dict)
        or report.get("state") != manifest.get("state")
        or report["state"] != "HUMAN_REVIEW"
        or report.get("failures")
    ):
        raise ValueError("BUNDLE_REVIEW_STATE_INVALID")
    return {
        "status": "VERIFIED",
        "files": len(seen),
        "state": report["state"],
        "human_approval": "NOT_GRANTED",
        "limits": "Checksums establish file integrity, not authenticity, editorial quality or human approval.",
    }


def create_bundle(job, assets, provider, directory, *, inputs=()):
    destination = Path(directory).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("NEW_BUNDLE_DIRECTORY_REQUIRED")
    if not destination.parent.is_dir():
        raise ValueError("EXISTING_PARENT_REQUIRED")
    stage = Path(tempfile.mkdtemp(prefix=".video-job-", dir=destination.parent))
    try:
        output = stage / (
            "film.mp4" if provider.output_suffix == ".mp4" else "workflow.json"
        )
        result = run(job, assets, provider, output)
        if result["state"] != "HUMAN_REVIEW":
            return result
        result["output"] = output.name
        (stage / "report.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        )
        source_records = [{"name": Path(p).name, "sha256": digest(p)} for p in inputs]
        manifest = {
            "schema_version": 1,
            "state": "HUMAN_REVIEW",
            "synthetic_unverified": True,
            "inputs": source_records,
            "files": [
                {"path": p.name, "bytes": p.stat().st_size, "sha256": digest(p)}
                for p in sorted(stage.iterdir())
            ],
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        )
        verify_bundle(stage)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError("NEW_BUNDLE_DIRECTORY_REQUIRED")
        os.rename(stage, destination)
        job.output = str(destination / output.name)
        result["bundle"] = str(destination)
        return result
    finally:
        if stage.exists():
            shutil.rmtree(stage)

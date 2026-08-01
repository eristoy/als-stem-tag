"""Build and write the stems manifest (JSON / TXT)."""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any

from .parser import ProjectInfo

AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff", ".mp3", ".flac", ".ogg", ".m4a"}


def list_audio_files(stems_dir: Path) -> list[str]:
    """Return sorted names of audio files directly inside ``stems_dir``."""
    return sorted(
        p.name
        for p in stems_dir.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    )


def build_manifest(info: ProjectInfo, files: list[str]) -> dict[str, Any]:
    """Assemble the manifest dict in the documented field order."""
    return {
        "project": info.project,
        "bpm": info.bpm,
        "time_signature": info.time_signature,
        "key": info.key,
        "scale": info.scale,
        "exported_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "ableton_version": info.ableton_version,
        "file_list": files,
    }


def write_json(manifest: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def write_txt(manifest: dict[str, Any], path: Path) -> None:
    lines = [
        f"Project:        {manifest['project']}",
        f"BPM:            {manifest['bpm']}",
        f"Time signature: {manifest['time_signature']}",
        f"Key:            {manifest['key']}",
        f"Scale:          {manifest['scale']}",
        f"Exported at:    {manifest['exported_at']}",
        f"Ableton:        {manifest['ableton_version']}",
        "",
        "Files:",
        *(f"  - {name}" for name in manifest["file_list"]),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

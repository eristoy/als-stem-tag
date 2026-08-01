import json
from pathlib import Path

from als_stem_tag.manifest import build_manifest, list_audio_files, write_json, write_txt
from als_stem_tag.parser import parse_als


def test_list_audio_files_filters_non_audio(stems_dir: Path):
    files = list_audio_files(stems_dir)
    assert files == ["kick.wav"]  # notes.txt excluded


def test_build_manifest_shape(als_file: Path, stems_dir: Path):
    info = parse_als(als_file)
    manifest = build_manifest(info, list_audio_files(stems_dir))
    assert manifest["project"] == "Test Project"
    assert manifest["bpm"] == 84.0
    assert manifest["time_signature"] == "4/4"
    assert manifest["key"] == "C Minor"
    assert manifest["file_list"] == ["kick.wav"]
    assert "exported_at" in manifest


def test_write_json_roundtrip(als_file: Path, stems_dir: Path, tmp_path: Path):
    info = parse_als(als_file)
    manifest = build_manifest(info, list_audio_files(stems_dir))
    out = tmp_path / "stems-info.json"
    write_json(manifest, out)
    loaded = json.loads(out.read_text())
    assert loaded == manifest


def test_write_txt_contains_fields(als_file: Path, stems_dir: Path, tmp_path: Path):
    info = parse_als(als_file)
    manifest = build_manifest(info, list_audio_files(stems_dir))
    out = tmp_path / "stems-info.txt"
    write_txt(manifest, out)
    text = out.read_text()
    assert "84" in text and "4/4" in text and "C Minor" in text and "kick.wav" in text

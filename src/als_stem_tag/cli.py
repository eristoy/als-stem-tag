"""Command-line interface for als-stem-tag (stdlib argparse, no dependencies)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .manifest import build_manifest, list_audio_files, write_json, write_txt
from .parser import AlsParseError, parse_als
from .tagging import TaggingError, can_tag, tag_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="als-stem-tag",
        description="Attach Ableton Live project metadata to exported stems.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("export", help="Write a manifest (and optionally tag files).")
    export.add_argument("--als", required=True, help="Path to the .als project file.")
    export.add_argument(
        "--stems-dir", required=True, help="Folder of exported stems to describe."
    )
    export.add_argument(
        "--tag-files",
        action="store_true",
        help="Also embed metadata into WAV/AIFF files in place (modifies files).",
    )
    export.add_argument(
        "--format",
        choices=["json", "txt", "both"],
        default="json",
        help="Manifest format(s) to write (default: json).",
    )
    export.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print every extracted field, including raw scale indices.",
    )
    export.set_defaults(func=_cmd_export)
    return parser


def _cmd_export(args: argparse.Namespace) -> int:
    als_path = Path(args.als)
    stems_dir = Path(args.stems_dir)

    if not stems_dir.is_dir():
        print(f"error: stems dir is not a directory: {stems_dir}", file=sys.stderr)
        return 2

    try:
        info = parse_als(als_path)
    except AlsParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    files = list_audio_files(stems_dir)
    if not files:
        print(f"warning: no audio files found in {stems_dir}", file=sys.stderr)

    manifest = build_manifest(info, files)

    written: list[Path] = []
    if args.format in ("json", "both"):
        p = stems_dir / "stems-info.json"
        write_json(manifest, p)
        written.append(p)
    if args.format in ("txt", "both"):
        p = stems_dir / "stems-info.txt"
        write_txt(manifest, p)
        written.append(p)

    # Report what we parsed.
    print(f"Parsed {als_path.name} ({info.ableton_version or 'unknown version'}):")
    if args.verbose:
        for field, value in info.to_dict().items():
            print(f"  {field:<27} {value}")
        print(f"  {'audio_files':<27} {len(files)}")
    else:
        print(f"  BPM: {info.bpm}   Time sig: {info.time_signature}   Key: {info.key}")
    for p in written:
        print(f"  wrote {p}")

    if args.tag_files:
        tagged, skipped = 0, 0
        for name in files:
            fpath = stems_dir / name
            if not can_tag(fpath):
                skipped += 1
                continue
            try:
                tag_file(fpath, info)
                tagged += 1
            except (TaggingError, OSError) as exc:
                print(f"  could not tag {name}: {exc}", file=sys.stderr)
        print(f"  tagged {tagged} file(s); skipped {skipped} unsupported.")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

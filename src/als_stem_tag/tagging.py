"""Embed project metadata directly into exported audio files (stdlib only).

WAV: we write three chunks so the metadata both *travels* and is *machine
readable*:

* ``bext`` -- Broadcast Wave Format description (a human-readable summary line).
* ``iXML`` -- structured XML with the individual fields under a custom block.
* ``acid`` -- the ACIDized-WAV chunk many DAWs (Ableton included) actually read
  to auto-detect tempo and root note when you drop a file into a project.

AIFF: RIFF chunks don't apply; we write an ``ANNO`` (annotation) text chunk.

All writers are idempotent: existing chunks we manage are stripped before the
fresh ones are appended, so re-tagging a file doesn't accumulate duplicates.
MP3 is intentionally out of scope (would require a third-party ID3 library).
"""

from __future__ import annotations

import struct
from pathlib import Path
from xml.sax.saxutils import escape

from .parser import ProjectInfo

# WAV chunk ids this tool owns and will overwrite on re-tag.
_MANAGED_WAV_CHUNKS = {b"bext", b"iXML", b"acid"}


class TaggingError(Exception):
    """Raised when a file isn't a valid WAV/AIFF we can rewrite."""


def _summary_line(info: ProjectInfo) -> str:
    parts = [f"PROJECT={info.project}"]
    if info.bpm is not None:
        parts.append(f"BPM={_fmt_bpm(info.bpm)}")
    if info.key:
        parts.append(f"KEY={info.key}")
    if info.time_signature:
        parts.append(f"TSIG={info.time_signature}")
    return ";".join(parts)


def _fmt_bpm(bpm: float) -> str:
    return str(int(bpm)) if float(bpm).is_integer() else f"{bpm:g}"


# --- chunk builders --------------------------------------------------------

def _build_bext(info: ProjectInfo) -> bytes:
    """A minimal (version 1, no coding history) Broadcast Wave bext chunk."""
    description = _summary_line(info).encode("ascii", "replace")[:256].ljust(256, b"\x00")
    originator = b"als-stem-tag".ljust(32, b"\x00")
    originator_ref = b"".ljust(32, b"\x00")
    orig_date = b"".ljust(10, b"\x00")
    orig_time = b"".ljust(8, b"\x00")
    body = description + originator + originator_ref + orig_date + orig_time
    body += struct.pack("<IIH", 0, 0, 1)   # TimeReference low/high, Version=1
    body += b"\x00" * 64                    # UMID
    body += struct.pack("<hhhhh", 0, 0, 0, 0, 0)  # loudness fields (unset)
    body += b"\x00" * 180                   # Reserved
    return body  # 602 bytes


def _build_ixml(info: ProjectInfo) -> bytes:
    def tag(name: str, value: object) -> str:
        return f"<{name}>{escape(str(value))}</{name}>" if value is not None else ""

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<BWFXML><IXML_VERSION>1.5</IXML_VERSION>"
        "<STEMINFO>"
        + tag("PROJECT", info.project)
        + tag("BPM", _fmt_bpm(info.bpm) if info.bpm is not None else None)
        + tag("KEY", info.key)
        + tag("SCALE", info.scale)
        + tag("TIME_SIGNATURE", info.time_signature)
        + tag("GENERATOR", "als-stem-tag")
        + "</STEMINFO></BWFXML>"
    )
    return xml.encode("utf-8")


def _build_acid(info: ProjectInfo) -> bytes:
    """The 24-byte ACID chunk: tempo, meter and (optionally) root note."""
    has_key = info.root_note is not None
    flags = 0x02 if has_key else 0x00  # bit1 = root note set; bit0 (one-shot) off
    root_midi = (60 + info.root_note) if has_key else 0  # C3 = MIDI 60
    numerator = info.time_signature_numerator or 4
    denominator = info.time_signature_denominator or 4
    tempo = float(info.bpm or 0.0)
    return struct.pack(
        "<IHHfIHHf",
        flags,
        root_midi & 0xFFFF,
        0x8000,          # reserved / "unknown", conventional value
        0.0,             # reserved float
        0,               # number of beats (unknown)
        denominator,
        numerator,
        tempo,
    )


# --- WAV -------------------------------------------------------------------

def _split_riff_chunks(body: bytes, size_fmt: str) -> list[list[bytes]]:
    chunks: list[list[bytes]] = []
    i = 0
    while i + 8 <= len(body):
        cid = body[i : i + 4]
        (csize,) = struct.unpack(size_fmt, body[i + 4 : i + 8])
        cdata = body[i + 8 : i + 8 + csize]
        chunks.append([cid, cdata])
        i += 8 + csize + (csize & 1)  # chunks are word-aligned
    return chunks


def tag_wav(path: Path, info: ProjectInfo) -> None:
    raw = path.read_bytes()
    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise TaggingError(f"{path.name} is not a RIFF/WAVE file")

    chunks = _split_riff_chunks(raw[12:], "<I")
    chunks = [c for c in chunks if c[0] not in _MANAGED_WAV_CHUNKS]
    chunks.append([b"bext", _build_bext(info)])
    chunks.append([b"iXML", _build_ixml(info)])
    chunks.append([b"acid", _build_acid(info)])

    out = bytearray(b"WAVE")
    for cid, cdata in chunks:
        out += cid + struct.pack("<I", len(cdata)) + cdata
        if len(cdata) & 1:
            out += b"\x00"
    path.write_bytes(b"RIFF" + struct.pack("<I", len(out)) + bytes(out))


# --- AIFF ------------------------------------------------------------------

def tag_aiff(path: Path, info: ProjectInfo) -> None:
    raw = path.read_bytes()
    if raw[:4] != b"FORM" or raw[8:12] not in (b"AIFF", b"AIFC"):
        raise TaggingError(f"{path.name} is not an AIFF/AIFC file")

    form_type = raw[8:12]
    chunks = _split_riff_chunks(raw[12:], ">I")
    chunks = [c for c in chunks if c[0] != b"ANNO"]
    chunks.append([b"ANNO", _summary_line(info).encode("ascii", "replace")])

    out = bytearray(form_type)
    for cid, cdata in chunks:
        out += cid + struct.pack(">I", len(cdata)) + cdata
        if len(cdata) & 1:
            out += b"\x00"
    path.write_bytes(b"FORM" + struct.pack(">I", len(out)) + bytes(out))


# --- dispatch --------------------------------------------------------------

_TAGGABLE = {".wav": tag_wav, ".aif": tag_aiff, ".aiff": tag_aiff}


def can_tag(path: Path) -> bool:
    return path.suffix.lower() in _TAGGABLE


def tag_file(path: Path, info: ProjectInfo) -> bool:
    """Tag a single file in place. Returns True if tagged, False if unsupported."""
    handler = _TAGGABLE.get(path.suffix.lower())
    if handler is None:
        return False
    handler(path, info)
    return True

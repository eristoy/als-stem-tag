"""Parse an Ableton Live ``.als`` project file.

An ``.als`` is gzip-compressed XML. The element paths shift between Live
versions (e.g. Live 12 renamed ``MasterTrack`` to ``MainTrack``), so every
lookup here tries the known variants and then a structural fallback, and reports
a clear error rather than a silently-wrong value.

Verified against Ableton Live 12.4.1. Where 12's layout is known to differ from
older versions, both are attempted.
"""

from __future__ import annotations

import gzip
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from .scales import root_note_name, scale_name


class AlsParseError(Exception):
    """Raised when a file cannot be read or does not look like Ableton XML."""


@dataclass
class ProjectInfo:
    """Structured metadata extracted from a Live Set."""

    project: str
    bpm: float | None
    time_signature: str | None
    key: str | None
    scale: str | None
    # Raw pieces, kept for taggers that need them (e.g. ACID root-note MIDI).
    time_signature_numerator: int | None = None
    time_signature_denominator: int | None = None
    root_note: int | None = None
    scale_index: int | None = None
    ableton_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --- XML loading -----------------------------------------------------------

def _load_root(als_path: Path) -> ET.Element:
    try:
        with gzip.open(als_path, "rb") as fh:
            data = fh.read()
    except FileNotFoundError:
        raise AlsParseError(f"No such file: {als_path}")
    except OSError as exc:
        raise AlsParseError(
            f"Could not read {als_path} as a gzip-compressed .als file: {exc}"
        )
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise AlsParseError(f"{als_path} did not contain valid Ableton XML: {exc}")
    if root.tag != "Ableton":
        raise AlsParseError(
            f"{als_path} root element is <{root.tag}>, expected <Ableton>. "
            "This does not look like a Live Set."
        )
    return root


def _first_track(root: ET.Element) -> ET.Element | None:
    """Return the master/main track element across Live versions."""
    live_set = root.find("LiveSet")
    if live_set is None:
        return None
    for name in ("MainTrack", "MasterTrack"):
        track = live_set.find(name)
        if track is not None:
            return track
    return None


# --- Individual fields -----------------------------------------------------

def _extract_tempo(root: ET.Element) -> float | None:
    # Preferred: <...Track>/DeviceChain/Mixer/Tempo/Manual (Live 12 = MainTrack).
    for track in ("MainTrack", "MasterTrack"):
        manual = root.find(f"LiveSet/{track}/DeviceChain/Mixer/Tempo/Manual")
        if manual is not None and manual.get("Value") is not None:
            return _to_float(manual.get("Value"))
    # Fallback: any Tempo/Manual anywhere in the document.
    for tempo in root.iter("Tempo"):
        manual = tempo.find("Manual")
        if manual is not None and manual.get("Value") is not None:
            return _to_float(manual.get("Value"))
    return None


def decode_time_signature(value: int) -> tuple[int, int]:
    """Decode Ableton's packed time-signature enum into (numerator, denominator).

    Live encodes the signature as a single int: the low part gives the
    numerator, the high part selects a power-of-two denominator. e.g. 201 -> 4/4.
    """
    numerator = (value % 99) + 1
    denominator = 2 ** (value // 99)
    return numerator, denominator


def _extract_time_signature(root: ET.Element) -> tuple[int, int] | None:
    track = _first_track(root)
    if track is None:
        return None
    # The master time signature is an EnumEvent inside the track's automation.
    # Take the earliest event (project start = the sentinel time ~ -63072000).
    events = list(track.iter("EnumEvent"))
    if not events:
        return None
    events.sort(key=lambda e: _to_float(e.get("Time")) or 0.0)
    value = events[0].get("Value")
    if value is None:
        return None
    try:
        return decode_time_signature(int(value))
    except ValueError:
        return None


def _extract_scale(root: ET.Element) -> tuple[int | None, int | None]:
    """Return (root_index, scale_index) from the global ScaleInformation, if any."""
    si = root.find("LiveSet/ScaleInformation")
    if si is None:
        return None, None
    root_el = si.find("Root")
    name_el = si.find("Name")
    root_idx = _to_int(root_el.get("Value")) if root_el is not None else None
    scale_idx = _to_int(name_el.get("Value")) if name_el is not None else None
    return root_idx, scale_idx


def _prefers_flats(root: ET.Element) -> bool:
    el = root.find("LiveSet/PreferFlatRootNote")
    return el is not None and el.get("Value") == "true"


# --- Public API ------------------------------------------------------------

def parse_als(als_path: str | Path) -> ProjectInfo:
    """Parse a Live Set and return its :class:`ProjectInfo`.

    Raises :class:`AlsParseError` for unreadable/invalid files. Individual
    missing fields (e.g. no scale set) come back as ``None`` rather than raising.
    """
    path = Path(als_path)
    root = _load_root(path)

    bpm = _extract_tempo(root)
    if bpm is None:
        raise AlsParseError(
            f"Could not locate a tempo in {path.name}. The Live version's XML "
            "layout may differ from what this tool understands."
        )

    ts = _extract_time_signature(root)
    ts_str = f"{ts[0]}/{ts[1]}" if ts else None

    root_idx, scale_idx = _extract_scale(root)
    prefer_flat = _prefers_flats(root)
    root_name = root_note_name(root_idx, prefer_flat)
    scale_str = scale_name(scale_idx)
    key = f"{root_name} {scale_str}".strip() if root_name and scale_str else None

    return ProjectInfo(
        project=path.stem,
        bpm=bpm,
        time_signature=ts_str,
        key=key,
        scale=scale_str,
        time_signature_numerator=ts[0] if ts else None,
        time_signature_denominator=ts[1] if ts else None,
        root_note=root_idx,
        scale_index=scale_idx,
        ableton_version=root.get("Creator"),
    )


# --- small helpers ---------------------------------------------------------

def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None

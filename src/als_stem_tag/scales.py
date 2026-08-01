"""Root-note and scale-name enum tables for Ableton Live's ScaleInformation.

Live stores the global scale as two integers under ``LiveSet/ScaleInformation``:
a ``Root`` (0-11, chromatic, C=0) and a ``Name`` (index into Live's scale list).
These tables translate those indices into human-readable names.

The scale-name order matches Live 11/12's scale dropdown. Live could reorder or
extend this list in a future version, so lookups fall back to a numeric label
(e.g. ``"Scale#37"``) rather than guessing wrong.
"""

from __future__ import annotations

# Chromatic root names. Live exposes a "prefer flats" spelling preference, so we
# keep both and choose based on the project's PreferFlatRootNote flag.
ROOT_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ROOT_NAMES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# Scale names in Live 11/12 dropdown order.
SCALE_NAMES = [
    "Major",             # 0
    "Minor",             # 1
    "Dorian",            # 2
    "Mixolydian",        # 3
    "Lydian",            # 4
    "Phrygian",          # 5
    "Locrian",           # 6
    "Whole Tone",        # 7
    "Half-whole Dim.",   # 8
    "Whole-half Dim.",   # 9
    "Minor Blues",       # 10
    "Minor Pentatonic",  # 11
    "Major Pentatonic",  # 12
    "Harmonic Minor",    # 13
    "Harmonic Major",    # 14
    "Dorian #4",         # 15
    "Phrygian Dominant", # 16
    "Melodic Minor",     # 17
    "Lydian Augmented",  # 18
    "Lydian Dominant",   # 19
    "Super Locrian",     # 20
    "8-Tone Spanish",    # 21
    "Bhairav",           # 22
    "Hungarian Minor",   # 23
    "Hirajoshi",         # 24
    "In-Sen",            # 25
    "Iwato",             # 26
    "Kumoi",             # 27
    "Pelog",             # 28
    "Spanish",           # 29
]


def root_note_name(root_index: int | None, prefer_flat: bool = False) -> str | None:
    """Return the note name for a chromatic root index (0-11), or None."""
    if root_index is None:
        return None
    table = ROOT_NAMES_FLAT if prefer_flat else ROOT_NAMES_SHARP
    if 0 <= root_index < len(table):
        return table[root_index]
    return f"Root#{root_index}"


def scale_name(scale_index: int | None) -> str | None:
    """Return the scale name for a Live scale index, or None."""
    if scale_index is None:
        return None
    if 0 <= scale_index < len(SCALE_NAMES):
        return SCALE_NAMES[scale_index]
    return f"Scale#{scale_index}"


_SCALE_INDEX_BY_NAME = {name.lower(): i for i, name in enumerate(SCALE_NAMES)}


def scale_index_from_name(name: str | None) -> int | None:
    """Reverse lookup: a scale name string (e.g. "Lydian") -> its index, or None.

    Live 12.0 beta stored the scale as a literal name string rather than an
    index; this maps those back to the canonical index when it recognises them.
    """
    if not name:
        return None
    return _SCALE_INDEX_BY_NAME.get(name.strip().lower())

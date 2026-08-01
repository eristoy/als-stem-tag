"""Shared test fixtures: synthetic .als and audio files (no real project needed)."""

from __future__ import annotations

import gzip
import struct
import wave
from pathlib import Path

import pytest

# A minimal Live-Set-shaped XML mirroring the real Live 12.4.1 layout this tool
# targets: MainTrack tempo, a time-signature EnumEvent (201 -> 4/4), and a global
# ScaleInformation (Root=0 -> C, Name=1 -> Minor).
_ALS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Ableton MajorVersion="5" MinorVersion="12.0_12402" Creator="Ableton Live 12.4.1">
  <LiveSet>
    <MainTrack>
      <DeviceChain>
        <Mixer>
          <Tempo>
            <Manual Value="84" />
          </Tempo>
        </Mixer>
      </DeviceChain>
      <AutomationEnvelopes>
        <Envelopes>
          <AutomationEnvelope>
            <Automation>
              <Events>
                <EnumEvent Id="0" Time="-63072000" Value="201" />
              </Events>
            </Automation>
          </AutomationEnvelope>
        </Envelopes>
      </AutomationEnvelopes>
    </MainTrack>
    <ScaleInformation>
      <Root Value="0" />
      <Name Value="1" />
    </ScaleInformation>
    <InKey Value="true" />
    <PreferFlatRootNote Value="false" />
  </LiveSet>
</Ableton>
"""


@pytest.fixture
def als_file(tmp_path: Path) -> Path:
    """A gzip-compressed synthetic .als on disk."""
    path = tmp_path / "Test Project.als"
    path.write_bytes(gzip.compress(_ALS_XML.encode("utf-8")))
    return path


@pytest.fixture
def wav_file(tmp_path: Path) -> Path:
    """A tiny but valid 1-frame mono 44.1k WAV."""
    path = tmp_path / "kick.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(struct.pack("<h", 0))
    return path


@pytest.fixture
def stems_dir(tmp_path: Path, wav_file: Path) -> Path:
    """A folder containing the wav plus a non-audio file (to test filtering)."""
    (tmp_path / "notes.txt").write_text("ignore me")
    return tmp_path

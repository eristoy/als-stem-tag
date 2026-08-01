import struct
import wave
from pathlib import Path

from als_stem_tag.parser import ProjectInfo
from als_stem_tag.tagging import tag_aiff, tag_file, tag_wav


def _info() -> ProjectInfo:
    return ProjectInfo(
        project="Test Project",
        bpm=84.0,
        time_signature="4/4",
        key="C Minor",
        scale="Minor",
        time_signature_numerator=4,
        time_signature_denominator=4,
        root_note=0,
        scale_index=1,
        ableton_version="Ableton Live 12.4.1",
    )


def _riff_chunk_ids(path: Path) -> list[bytes]:
    raw = path.read_bytes()
    body, i, ids = raw[12:], 0, []
    while i + 8 <= len(body):
        cid = body[i : i + 4]
        (size,) = struct.unpack("<I", body[i + 4 : i + 8])
        ids.append(cid)
        i += 8 + size + (size & 1)
    return ids


def test_wav_gets_chunks_and_stays_valid(wav_file: Path):
    tag_wav(wav_file, _info())
    ids = _riff_chunk_ids(wav_file)
    assert b"bext" in ids and b"iXML" in ids and b"acid" in ids
    # Still a readable WAV afterwards.
    with wave.open(str(wav_file), "rb") as w:
        assert w.getframerate() == 44100


def test_wav_tagging_is_idempotent(wav_file: Path):
    tag_wav(wav_file, _info())
    tag_wav(wav_file, _info())
    ids = _riff_chunk_ids(wav_file)
    assert ids.count(b"bext") == 1
    assert ids.count(b"acid") == 1
    assert ids.count(b"iXML") == 1


def test_acid_chunk_encodes_tempo(wav_file: Path):
    tag_wav(wav_file, _info())
    raw = wav_file.read_bytes()
    idx = raw.find(b"acid")
    (size,) = struct.unpack("<I", raw[idx + 4 : idx + 8])
    data = raw[idx + 8 : idx + 8 + size]
    fields = struct.unpack("<IHHfIHHf", data)
    assert fields[7] == 84.0        # tempo
    assert fields[6] == 4           # numerator
    assert fields[1] == 60          # root note C -> MIDI 60


def _minimal_aiff(path: Path) -> None:
    # Hand-built AIFF (COMM + SSND). Avoids the stdlib `aifc` module, which was
    # removed in Python 3.13. tag_aiff only needs a valid FORM/AIFF container.
    rate80 = b"\x40\x0e\xac\x44\x00\x00\x00\x00\x00\x00"  # 80-bit float 44100
    comm = struct.pack(">hIh", 1, 1, 16) + rate80
    ssnd = struct.pack(">II", 0, 0) + struct.pack(">h", 0)
    body = b"AIFF"
    body += b"COMM" + struct.pack(">I", len(comm)) + comm
    body += b"SSND" + struct.pack(">I", len(ssnd)) + ssnd + b"\x00"  # word-align
    path.write_bytes(b"FORM" + struct.pack(">I", len(body)) + body)


def test_aiff_gets_annotation(tmp_path: Path):
    path = tmp_path / "snare.aiff"
    _minimal_aiff(path)
    tag_aiff(path, _info())
    raw = path.read_bytes()
    assert b"ANNO" in raw and b"BPM=84" in raw


def test_tag_file_skips_unsupported(tmp_path: Path):
    mp3 = tmp_path / "bass.mp3"
    mp3.write_bytes(b"\x00\x00")
    assert tag_file(mp3, _info()) is False

import gzip
from pathlib import Path

import pytest

from als_stem_tag.parser import AlsParseError, decode_time_signature, parse_als


def test_parses_core_fields(als_file: Path):
    info = parse_als(als_file)
    assert info.project == "Test Project"
    assert info.bpm == 84.0
    assert info.time_signature == "4/4"
    assert info.key == "C Minor"
    assert info.scale == "Minor"
    assert info.root_note == 0
    assert "12.4.1" in (info.ableton_version or "")


@pytest.mark.parametrize(
    "value,expected",
    [(201, (4, 4)), (200, (3, 4)), (302, (6, 8)), (99, (1, 2))],
)
def test_time_signature_decode(value, expected):
    assert decode_time_signature(value) == expected


def test_missing_scale_is_none(tmp_path: Path):
    xml = (
        '<?xml version="1.0"?><Ableton Creator="Ableton Live 11">'
        "<LiveSet><MasterTrack><DeviceChain><Mixer><Tempo>"
        '<Manual Value="120" /></Tempo></Mixer></DeviceChain></MasterTrack>'
        "</LiveSet></Ableton>"
    )
    path = tmp_path / "NoScale.als"
    path.write_bytes(gzip.compress(xml.encode()))
    info = parse_als(path)
    assert info.bpm == 120.0
    assert info.key is None
    assert info.scale is None


def test_beta_schema_string_scale(tmp_path: Path):
    # Live 12.0 beta stored RootNote (not Root) and a scale-name string.
    xml = (
        '<?xml version="1.0"?><Ableton Creator="Ableton Live 12.0b29">'
        "<LiveSet><MainTrack><DeviceChain><Mixer><Tempo>"
        '<Manual Value="128" /></Tempo></Mixer></DeviceChain></MainTrack>'
        '<ScaleInformation><RootNote Value="5" /><Name Value="Lydian" />'
        "</ScaleInformation></LiveSet></Ableton>"
    )
    path = tmp_path / "Beta.als"
    path.write_bytes(gzip.compress(xml.encode()))
    info = parse_als(path)
    assert info.root_note == 5
    assert info.key == "F Lydian"
    assert info.scale == "Lydian"
    assert info.scale_index == 4  # reverse-mapped from the name


def test_not_gzip_raises(tmp_path: Path):
    path = tmp_path / "bad.als"
    path.write_bytes(b"this is not gzip")
    with pytest.raises(AlsParseError):
        parse_als(path)


def test_wrong_root_element_raises(tmp_path: Path):
    path = tmp_path / "wrong.als"
    path.write_bytes(gzip.compress(b"<NotAbleton/>"))
    with pytest.raises(AlsParseError):
        parse_als(path)


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(AlsParseError):
        parse_als(tmp_path / "nope.als")

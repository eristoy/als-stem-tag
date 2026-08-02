# als-stem-tag

Ableton Live's stem/audio export has no way to attach project metadata — BPM,
key/scale, time signature — to the exported files. `als-stem-tag` reads that
metadata straight out of your `.als` project and either writes a manifest
alongside your stems or embeds it into the audio files themselves.

- **Zero dependencies.** Pure Python standard library (parsing, RIFF/AIFF chunk
  writing). Targets macOS, Python 3.11+.
- **Non-destructive by default.** Writes a `stems-info.json` next to your stems.
  File embedding is strictly opt-in (`--tag-files`).
- **Version-aware parsing.** Verified against Ableton Live 12.4.1; falls back
  across known layout differences (e.g. Live 12 renamed `MasterTrack` →
  `MainTrack`) and fails with a clear message rather than a wrong value.

## Install

**As a standalone command (recommended).** Because the tool is pure standard
library, `install.sh` bundles it into a single self-contained executable
(a [zipapp](https://docs.python.org/3/library/zipapp.html)) — no venv, no pip:

```bash
./install.sh            # -> ~/.local/bin/als-stem-tag
./install.sh /path/foo  # or a custom destination
```

`~/.local/bin` is on most `$PATH`s already. Re-run `install.sh` after pulling
changes to refresh the command. It only needs `python3.14` on your PATH.

**As an editable package (for development):**

```bash
pip install -e ".[dev]"
```

## Usage

```bash
als-stem-tag export --als "MyProject.als" --stems-dir "./Stems" \
    [--tag-files] [--format json|txt|both]
```

| Flag | Description |
| --- | --- |
| `--als` | Path to the `.als` project file (required). |
| `--stems-dir` | Folder of exported stems to describe (required). |
| `--format` | Manifest format: `json` (default), `txt`, or `both`. |
| `--tag-files` | Also embed metadata into WAV/AIFF files **in place**. |
| `-v`, `--verbose` | Print every extracted field, including raw scale indices. |

### Example

```bash
als-stem-tag export --als "Distaint Static.als" --stems-dir "./Stems" --format both
```

Produces `./Stems/stems-info.json`:

```json
{
  "project": "Distaint Static",
  "bpm": 84.0,
  "time_signature": "4/4",
  "key": "C Major",
  "scale": "Major",
  "exported_at": "2026-08-01T18:59:00-07:00",
  "ableton_version": "Ableton Live 12.4.1",
  "file_list": [
    "Bass.wav",
    "Drums.wav",
    "Lead.wav"
  ]
}
```

## Embedding metadata into files (`--tag-files`)

With `--tag-files`, each **WAV** file gets three chunks and each **AIFF** file
gets an annotation:

| Format | What's written | Why |
| --- | --- | --- |
| WAV | `bext` (Broadcast Wave) | Human-readable summary line. |
| WAV | `iXML` | Structured `<STEMINFO>` block with individual fields. |
| WAV | `acid` | Tempo + root note that many DAWs (incl. Ableton) auto-detect. |
| AIFF | `ANNO` | Text annotation with the same summary line. |

Tagging is **idempotent** — re-running replaces the tool's own chunks instead of
duplicating them, and leaves the audio data untouched.

> **MP3 is not supported.** ID3 tagging would require a third-party library
> (`mutagen`); this tool is deliberately dependency-free. MP3 files are listed
> in the manifest and skipped by `--tag-files`.

### Verifying the tags

You can confirm the embedded metadata with any independent audio-metadata tool
— you don't have to trust `als-stem-tag`'s own output.

[**ExifTool**](https://exiftool.org/) (`brew install exiftool`) is the most
complete: it reads all three chunks, including decoding the tempo and root note
back out of the `acid` chunk.

```bash
exiftool -Description -Tempo -Meter -RootNote -"Bwfxml Steminfo Key" "file.wav"
```

```
Description             : PROJECT=Distaint Static;BPM=84;KEY=C Major;TSIG=4/4
Tempo                   : 84
Meter                   : 4/4
Root Note               : C
Bwfxml Steminfo Key     : C Major
```

For a quick check with a tool you may already have, `ffprobe` (from FFmpeg)
surfaces the `bext` summary line as the `comment` tag:

```bash
ffprobe -v error -show_entries format_tags -of default=noprint_wrappers=1 "file.wav"
```

| Tool | `bext` | `iXML` | `acid` |
| --- | :--: | :--: | :--: |
| ExifTool | ✅ | ✅ | ✅ |
| bwfmetaedit (BWF reference tool) | ✅ | ✅ | — |
| ffprobe | ✅ | — | — |
| mediainfo | ✅ | partial | — |

> ExifTool labels the `acid` root note by octave (MIDI 60 shows as "High C").
> The pitch class is what matters for key metadata; the octave label is just a
> naming convention.

## What gets extracted

| Field | Source in the `.als` XML |
| --- | --- |
| `bpm` | `LiveSet/MainTrack/DeviceChain/Mixer/Tempo/Manual` (fallback: `MasterTrack`, then any `Tempo/Manual`). |
| `time_signature` | Master-track time-signature `EnumEvent` (Ableton packed enum, e.g. `201` → `4/4`). |
| `key` / `scale` | `LiveSet/ScaleInformation` `Root` (0–11) + `Name` (scale index). Absent if the project isn't using Scale mode. |
| `project` | The `.als` filename (Live doesn't store a project name in the XML). |

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests use a synthetic in-memory `.als` and hand-built WAV/AIFF files, so they
don't depend on a real Ableton project.

## License

MIT

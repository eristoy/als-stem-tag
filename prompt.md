Build a Python CLI tool called `als-stem-tag` that solves this problem:
Ableton Live's stem/audio export has no way to attach project metadata
(BPM, key/scale, time signature) to the exported files.

REQUIREMENTS:

1. Parse an Ableton Live .als file (it's gzip-compressed XML):
   - Extract Tempo (BPM)
   - Extract Time Signature (numerator/denominator)
   - Extract Scale/Key info if present (Live 11+ stores this under
     ScaleInformation — RootNote + Name, e.g. "C Minor"). Handle
     gracefully if the project doesn't use Scale mode.
   - Extract the Live Set name / project name.

2. Generate a manifest alongside a folder of exported stems:
   - Default: write a `stems-info.json` (and optionally `.txt`) in the
     export folder with { project, bpm, time_signature, key, scale,
     exported_at, file_list }.

3. Optionally embed the metadata directly into the exported audio files:
   - WAV/AIFF: write BWF/iXML chunks (via `wavinfo` or manual RIFF chunk
     writing) so BPM/key travel with the file itself.
   - MP3: write ID3v2 TBPM (BPM) and TKEY (key) frames via `mutagen`.
   - Make this an opt-in flag (--tag-files) since it modifies the audio
     files in place.

4. CLI interface (use `click` or `argparse`):
   als-stem-tag export --als "MyProject.als" --stems-dir "./Stems" [--tag-files] [--format json|txt|both]

5. Structure as a proper installable project:
   - pyproject.toml, src/ layout
   - README.md explaining usage, with an example of the manifest output
   - Basic pytest tests using a small fixture .als (or mocked XML) so
     tests don't depend on a real Ableton project
   - Target macOS (Python 3.11+), no external non-Python dependencies

6. Key implementation notes:
   - .als files are gzip; use `gzip.open()` then `xml.etree.ElementTree`
   - Tempo lives under LiveSet > MasterTrack > ... > Tempo > Manual
     (verify actual path against a real .als — ask me for a sample if
     the schema differs by Live version)
   - Be defensive: Live version differences mean XML paths can shift;
     fail with a clear error message rather than a silent wrong value

Set this up as its own git repo with a sensible .gitignore for Python.

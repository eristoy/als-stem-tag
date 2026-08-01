"""als-stem-tag: attach Ableton Live project metadata to exported stems."""

from .parser import ProjectInfo, AlsParseError, parse_als

__version__ = "0.1.0"
__all__ = ["ProjectInfo", "AlsParseError", "parse_als", "__version__"]

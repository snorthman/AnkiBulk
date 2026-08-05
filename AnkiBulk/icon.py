"""SVG icon loader with dark mode support.

Icons live in ``svg/`` as ``.svg`` files.  Access them by stem name::

    from AnkiBulk.icon import icon
    button.setIcon(icon("clipboard-copy"))

Icons use ``currentColor`` for strokes, which is resolved to a theme-
appropriate color at load time.  Icons are cached per (name, dark_mode).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from aqt.qt import QIcon

_DIR = Path(__file__).parent / "svg"
_cache: dict[tuple[str, bool], QIcon] = {}
_tmp_dir: Path | None = None


def icon(name: str) -> QIcon:
    """Return a QIcon for the given SVG stem name (without extension)."""
    from aqt.theme import theme_manager
    dark = theme_manager.night_mode
    key = (name, dark)
    if key not in _cache:
        svg = (_DIR / f"{name}.svg").read_text(encoding="utf-8")
        color = "#C8C8C8" if dark else "#333333"
        svg = svg.replace("currentColor", color)

        global _tmp_dir
        if _tmp_dir is None:
            _tmp_dir = Path(tempfile.mkdtemp(prefix="ankibulk_icons_"))

        suffix = "-dark" if dark else "-light"
        tmp = _tmp_dir / f"{name}{suffix}.svg"
        tmp.write_text(svg, encoding="utf-8")
        _cache[key] = QIcon(str(tmp))
    return _cache[key]

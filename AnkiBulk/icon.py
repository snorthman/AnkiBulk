"""SVG icon loader.

Icons live in ``svg/`` as ``.svg`` files. Access them by stem name::

    from AnkiBulk.icon import icon
    button.setIcon(icon("clipboard-copy"))

Icons are cached after first load.
"""

from __future__ import annotations

from pathlib import Path

from aqt.qt import QIcon

_DIR = Path(__file__).parent / "svg"
_cache: dict[str, QIcon] = {}


def icon(name: str) -> QIcon:
    """Return a QIcon for the given SVG stem name (without extension)."""
    if name not in _cache:
        path = _DIR / f"{name}.svg"
        _cache[name] = QIcon(str(path))
    return _cache[name]

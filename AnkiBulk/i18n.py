"""Lightweight YAML-based i18n with live locale switching.

Translation files live under ``i18n/<locale>/ankibulk.yaml``.  The locale
comes from ``anki.lang.current_lang`` and falls back to en-US for any
missing keys (or any unknown locale).

Simple strings use ``{var}`` interpolation::

    table-updated-example-rows: "Updated example rows, using {name} notetype"
    →  tr("table-updated-example-rows", name="Basic")

Plurals use a dict with ``one`` / ``other`` keys (selected by ``n``)::

    table-added-rows:
      one: "Added 1 row"
      other: "Added {n} rows"
    →  tr("table-added-rows", n=5)

A module-level binding ``tr = i18n().tr`` is provided for convenient import::

    from AnkiBulk.i18n import tr
    label.setText(tr("some-key", count=5))
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from anki.lang import current_lang

_VAR_RE = re.compile(r'\{(\w+)\}')


def _load_catalog(path: Path) -> dict[str, str | dict[str, str]]:
    """Load a YAML translation file.  Returns {} on any error."""
    try:
        with open(path, encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _format(template: str, kwargs: dict[str, object]) -> str:
    """Replace {var} placeholders with keyword arguments."""

    def _sub(m: re.Match[str]) -> str:
        key = m.group(1)
        return str(kwargs[key]) if key in kwargs else m.group(0)

    return _VAR_RE.sub(_sub, template)


class i18n:
    """YAML-based i18n with live locale switching."""

    def __init__(self) -> None:
        self._base = Path(__file__).parent / 'i18n'
        self._locale: str | None = None
        self._catalog: dict[str, str | dict[str, str]] = {}
        self._fallback_catalog = _load_catalog(self._base / self.fallback / 'ankibulk.yaml')

    @property
    def fallback(self) -> str:
        return 'en-US'

    def sync(self) -> bool:
        new_locale = current_lang.replace('_', '-')
        if new_locale == self._locale:
            return False

        if new_locale == self.fallback:
            self._catalog = self._fallback_catalog
        else:
            self._catalog = _load_catalog(self._base / new_locale / 'ankibulk.yaml')

        self._locale = new_locale
        return True

    def tr(self, key: str, **kwargs: object) -> str:
        self.sync()
        entry = self._catalog.get(key) or self._fallback_catalog.get(key)

        if entry is None:
            return key

        # Plural form: dict with one/other keys
        if isinstance(entry, dict):
            n = kwargs.get('n', 0)
            form = 'one' if n == 1 else 'other'
            template = entry.get(form) or entry.get('other') or key
        else:
            template = str(entry)

        return _format(template, kwargs)


tr = i18n().tr

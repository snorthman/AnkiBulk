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


# noinspection PyPep8Naming
class i18n:
    def __init__(self) -> None:
        self._locale = self.fallback
        self._fallback_catalog = self.load_catalog(self.base / self.fallback / 'ankibulk.yaml')
        self._catalog = self._fallback_catalog.copy()
        self._re = re.compile(r'\{(\w+)}')

    def __getitem__(self, key: str) -> str | dict[str, str] | None:
        return self._catalog.get(key) or self._fallback_catalog.get(key)

    def __iter__(self):
        for key in self._catalog.keys():
            yield key

    @property
    def base(self) -> Path:
        return Path(__file__).parent / 'i18n'

    @property
    def fallback(self) -> str:
        return 'en-US'

    @property
    def get_locale(self) -> str:
        return current_lang.replace('_', '-')

    def sync(self) -> bool:
        new_locale = self.get_locale
        if new_locale == self._locale:
            return False

        if new_locale == self.fallback:
            self._catalog = self._fallback_catalog
        else:
            self._catalog = self.load_catalog(self.base / new_locale / 'ankibulk.yaml')

        self._locale = new_locale
        return True

    def tr(self, key: str, **kwargs) -> str:
        self.sync()
        entry = self[key]

        if entry is None:
            return key

        if isinstance(entry, dict):
            n = kwargs.get('n', 0)
            form = 'one' if n == 1 else 'other'
            template = entry.get(form) or entry.get('other') or key
        else:
            template = str(entry)

        return self.format(template, **kwargs)

    def format(self, template: str, **kwargs) -> str:
        """Replace {var} placeholders with keyword arguments."""

        def _sub(m: re.Match[str]) -> str:
            key = m.group(1)
            return str(kwargs[key]) if key in kwargs else m.group(0)

        return self._re.sub(_sub, template)

    @staticmethod
    def load_catalog(path: Path) -> dict[str, str | dict[str, str]]:
        """Load a YAML translation file.  Returns {} on any error."""
        try:
            with open(path, encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}


tr = i18n().tr

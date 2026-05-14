"""Fluent-based i18n with live locale switching.

Mirrors Anki's own approach (Mozilla Fluent, ``.ftl`` files), so translators
who already work on Anki recognize the format. Translation files live under
``i18n/<locale>/ankibulk.ftl``; locale comes from ``anki.lang.current_lang``
and falls back to en-US for any missing keys (or any unknown locale).

The ``i18n`` class lazily rebuilds its ``FluentLocalization`` whenever
``current_lang`` changes. ``sync()`` compares the current locale against the
cached one and reconstructs the localization object only when they differ.
``tr(key, **kwargs)`` calls ``sync()`` on every invocation, so any string
rendered after a language change reads from the new catalog automatically.

A module-level binding ``tr = i18n().tr`` is provided for convenient import::

    from AnkiBulk.i18n import tr
    label.setText(tr("some-key", count=5))

All AnkiBulk UI widgets are ephemeral (created fresh each time the dialog
opens), so there is no need for a locale-change listener — ``tr()`` always
returns the up-to-date translation.

The pure-Python ``fluent.runtime`` is vendored under ``internal/`` (Anki's
bundled Python doesn't ship it). See ``__init__.py``.
"""

from pathlib import Path

from anki.lang import current_lang

from fluent.runtime import FluentLocalization, FluentResourceLoader


class i18n:
    """Anki i18n with live locale switching."""
    def __init__(self) -> None:
        self._loader = FluentResourceLoader(str(Path(__file__).parent / 'i18n' / '{locale}'))
        self._locale: str | None = None
        self._l10n: FluentLocalization | None = None

    @property
    def fallback(self) -> str:
        return 'en-US'

    def sync(self) -> bool:
        new_locale = current_lang.replace('_', '-')
        if new_locale == self._locale and self._l10n is not None:
            return False

        locales = [new_locale] if new_locale == self.fallback else [new_locale, self.fallback]
        self._l10n = FluentLocalization(locales, ['ankibulk.ftl'], self._loader)
        self._locale = new_locale
        return True

    def tr(self, key: str, **kwargs) -> str:
        self.sync()
        return self._l10n.format_value(key, kwargs)  # type: ignore[union-attr]

tr = i18n().tr

from __future__ import annotations

from typing import Callable

from anki.decks import DeckId
from anki.models import NotetypeId
from aqt import AnkiQt
from aqt.deckchooser import DeckChooser
from aqt.notetypechooser import NotetypeChooser
from aqt.qt import QHBoxLayout, QWidget


class Chooser(QWidget):
    """Row of Type / Deck choosers.  The notetype button is disabled
    when the browser selection determines it, enabled otherwise."""

    def __init__(self, mw: AnkiQt, starting_notetype_id: NotetypeId, starting_deck_id: DeckId,
                 on_notetype_changed: Callable[[NotetypeId], None]) -> None:
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._notetype_widget = QWidget()
        self._notetype_chooser = NotetypeChooser(
            mw=mw, widget=self._notetype_widget,
            starting_notetype_id=starting_notetype_id,
            on_notetype_changed=on_notetype_changed,
        )
        self._notetype_chooser.button.setEnabled(False)
        layout.addWidget(self._notetype_widget)

        self._deck_widget = QWidget()
        self._deck_chooser = DeckChooser(mw, self._deck_widget, starting_deck_id=starting_deck_id)
        layout.addWidget(self._deck_widget)

    # ---- public API ------------------------------------------------------

    @property
    def notetype_id(self) -> NotetypeId:
        return self._notetype_chooser.selected_notetype_id

    @notetype_id.setter
    def notetype_id(self, value: NotetypeId) -> None:
        self._notetype_chooser.selected_notetype_id = value

    @property
    def deck_id(self) -> DeckId:
        return self._deck_chooser.selected_deck_id

    @deck_id.setter
    def deck_id(self, value: DeckId) -> None:
        self._deck_chooser.selected_deck_id = value

    def set_notetype_enabled(self, enabled: bool) -> None:
        """Enable or disable the notetype chooser button."""
        self._notetype_chooser.button.setEnabled(enabled)

    def cleanup(self) -> None:
        self._notetype_chooser.cleanup()
        self._deck_chooser.cleanup()

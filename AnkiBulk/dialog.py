from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path

from anki.decks import DeckId
from anki.models import NotetypeId
from aqt import AnkiQt
from aqt.qt import (
    QAbstractItemView,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QKeySequence,
    QLabel,
    QMessageBox,
    QPushButton,
    QShortcut,
    QStackedWidget,
    QVBoxLayout,
    Qt,
    qconnect,
)
from aqt.utils import restoreGeom, saveGeom, tooltip

from .chooser import Chooser
from .config import AnkiBulkConfig
from .i18n import tr
from .toggle import ToggleSwitch
from .text import TextGroup
from .table import TableGroup

if TYPE_CHECKING:
    from aqt.browser import Browser


STYLESHEET = Path(__file__).with_name("style.css").read_text(encoding="utf-8")


class Dialog(QDialog):
    def __init__(self, browser: Browser, mw: AnkiQt) -> None:
        super().__init__(browser)
        self.browser = browser
        self.mw = mw

        self._notetype_changing = False
        self.setWindowTitle(tr("dialog-title"))
        self.setMinimumSize(700, 500)
        flags = Qt.WindowType.Window | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint
        self.setWindowFlags(flags)

        root = QVBoxLayout()
        self.setLayout(root)

        # Initial notetype/deck — will be overridden by load_from_selection
        # if the browser has a selection.
        defaults = self.mw.col.defaults_for_adding(current_review_card=self.mw.reviewer.card)

        # -- Row 1: Type / Deck choosers --
        chooser_args = self.mw, NotetypeId(defaults.notetype_id), DeckId(defaults.deck_id), self._on_notetype_changed
        self.chooser = Chooser(*chooser_args)
        root.addWidget(self.chooser)

        # -- Row 2: Stacked content inside a group box --
        self.setStyleSheet(STYLESHEET)

        self.toggle = ToggleSwitch()

        group = QGroupBox()
        group.setObjectName("contentGroup")
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(0, 0, 0, 0)
        group.setLayout(group_layout)

        self._stack = QStackedWidget()
        group_layout.addWidget(self._stack)

        # ---- Page 0: Table group ----
        self.table_group = TableGroup(self.toggle, mw, browser=self.browser, chooser=self.chooser)

        self._hint = None
        if AnkiBulkConfig.first_time_use.value:
            self._hint = QLabel(tr("hint-first-time"))
            self._hint.setObjectName("firstTimeHint")
            self._hint.setWordWrap(True)
            self.table_group.layout().insertWidget(1, self._hint)

        self.table_group.load_from_selection()
        self._stack.addWidget(self.table_group)

        # ---- Page 1: Text group ----
        self.text_group = TextGroup(self.toggle, self.table)
        self._stack.addWidget(self.text_group)

        root.addWidget(group, stretch=1)
        self._prev_group = self.table_group.index

        qconnect(self.toggle.toggled, self._on_toggle_changed)
        self.toggle.set_labels(self.table_group.name, self.text_group.name)

        # -- Row 4: Buttons --
        button_row = QHBoxLayout()

        help_button = QPushButton(tr("menu-help"))
        help_button.setAutoDefault(False)
        qconnect(help_button.clicked, self._on_help)
        button_row.addWidget(help_button)

        button_row.addStretch()

        self.add_button = QPushButton(tr("btn-bulk-add"))
        self.add_button.setAutoDefault(False)
        qconnect(self.add_button.clicked, self._on_bulk_add)
        button_row.addWidget(self.add_button)

        cancel_button = QPushButton(tr("btn-cancel"))
        cancel_button.setAutoDefault(False)
        qconnect(cancel_button.clicked, self.close)
        button_row.addWidget(cancel_button)

        root.addLayout(button_row)

        # -- Shortcuts (only active on the relevant page) --
        update_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        qconnect(update_shortcut.activated,
                 lambda: self.table_group._on_update_from_selection() if self._prev_group == self.table_group.index else None)

        copy_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        qconnect(copy_shortcut.activated,
                 lambda: self.text_group._on_copy_to_clipboard() if self._prev_group == self.text_group.index else None)

        paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
        qconnect(paste_shortcut.activated, self._on_paste)

        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        qconnect(undo_shortcut.activated, self._on_undo)

        redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        qconnect(redo_shortcut.activated, self._on_redo)

        restoreGeom(self, __name__, default_size=(900, 600))

    @property
    def table(self):
        return self.table_group.table

    def _on_notetype_changed(self, notetype_id: NotetypeId) -> None:
        if self._notetype_changing:
            return
        self._notetype_changing = True
        try:
            if not self.table_group.confirm_discard(tr("btn-ok")):
                # Revert the chooser to the current notetype
                self.chooser.notetype_id = NotetypeId(self.table.notetype_id)
                return
            if deck_id := self.mw.col.default_deck_for_notetype(notetype_id):
                self.chooser.deck_id = deck_id
            self.table.notetype_id = notetype_id
            self.table.rebuild()
            self.table.insert_row(self.table.rowCount())
        finally:
            self._notetype_changing = False

    def _set_page(self, index: int) -> None:
        """Switch the stacked widget without re-triggering the toggle signal."""
        self._stack.setCurrentIndex(index)

    def _set_toggle(self, checked: bool) -> None:
        """Set the toggle state without triggering _on_toggle_changed."""
        self.toggle.blockSignals(True)
        self.toggle.checked = checked
        self.toggle.blockSignals(False)

    def _on_toggle_changed(self, checked: bool) -> None:
        """Toggle between Table (False/left) and Text (True/right)."""
        if checked:
            # Switching to Text — always allowed
            if self._hint is not None:
                self._hint.hide()
                self._hint = None
                AnkiBulkConfig.first_time_use = False

            existing_yaml, new_yaml = self.table.to_yaml()
            self.text_group.populate(existing_yaml, new_yaml)
            self._prev_group = self.text_group.index
            self._set_page(self.text_group.index)
            return

        # Switching to Table — validate YAML first.
        # The toggle already animated to Table; revert it while we validate.
        self._set_toggle(True)

        if not self.text_group.linter.validate_yaml():
            box = QMessageBox(self)
            box.setWindowTitle(tr("dialog-invalid-yaml-title"))
            box.setText(tr("dialog-invalid-yaml-body"))
            box.addButton(tr("btn-cancel"), QMessageBox.ButtonRole.RejectRole)
            discard = box.addButton(tr("dialog-discard"), QMessageBox.ButtonRole.AcceptRole)
            box.exec()
            if box.clickedButton() != discard:
                return
        else:
            text = self.text_group.editables_as_text()
            if not self.table.from_yaml(text):
                box = QMessageBox(self)
                box.setWindowTitle(tr("dialog-invalid-yaml-title"))
                box.setText(tr("dialog-invalid-yaml-body"))
                box.addButton(tr("btn-cancel"), QMessageBox.ButtonRole.RejectRole)
                discard = box.addButton(tr("dialog-discard"), QMessageBox.ButtonRole.AcceptRole)
                box.exec()
                if box.clickedButton() != discard:
                    return

        # Either YAML applied successfully or user chose Discard
        self._prev_group = self.table_group.index
        self._set_toggle(False)
        self._set_page(self.table_group.index)

    @property
    def _table_not_editing(self) -> bool:
        """True when on the Table page and no cell editor is open."""
        return (self._prev_group == self.table_group.index
                and self.table.state() != QAbstractItemView.State.EditingState)

    def _on_paste(self) -> None:
        if self._table_not_editing:
            self.table_group._on_insert_clipboard()

    def _on_undo(self) -> None:
        if self._prev_group == self.text_group.index:
            self.text_group.text_editables.undo()
        elif self._table_not_editing:
            self.table_group._on_undo()

    def _on_redo(self) -> None:
        if self._prev_group == self.text_group.index:
            self.text_group.text_editables.redo()
        elif self._table_not_editing:
            self.table_group._on_redo()

    def _on_help(self) -> None:
        from .help import Dialog as HelpDialog
        HelpDialog(self).exec()

    def _on_bulk_add(self) -> None:
        # If on the text view, apply YAML back to table first
        if self._prev_group == self.text_group.index:
            if not self.text_group.linter.validate_yaml():
                tooltip(tr("bulk-add-invalid-yaml"), parent=self)
                return
            text = self.text_group.editables_as_text()
            if not self.table.from_yaml(text):
                tooltip(tr("bulk-add-invalid-yaml"), parent=self)
                return

        table = self.table
        if not table.has_editable_content:
            tooltip(tr("bulk-add-no-content"))
            return

        col = self.mw.col
        notetype = table.current_notetype
        deck_id = self.chooser.deck_id
        field_names = [f["name"] for f in notetype["flds"]]
        tags_col = table.tags_col
        n_fields = len(field_names)

        added_nids: list[int] = []
        failures: list[str] = []

        for row in range(table.first_editable_row, table.rowCount()):
            sort_item = table.item(row, table.sort_col)
            if not sort_item or not sort_item.text().strip():
                continue

            note = col.new_note(notetype)
            for i in range(n_fields):
                item = table.item(row, i)
                note.fields[i] = item.text() if item else ""

            tags_item = table.item(row, tags_col)
            if tags_item and tags_item.text().strip():
                note.tags = col.tags.split(tags_item.text().strip())

            try:
                col.add_note(note, deck_id)
                added_nids.append(note.id)
            except Exception as e:
                sort_val = sort_item.text().strip()
                failures.append(f"{sort_val}: {e}")

        if not added_nids and not failures:
            tooltip(tr("bulk-add-no-notes"))
            return

        if failures:
            box = QMessageBox(self)
            box.setWindowTitle(tr("dialog-title"))
            box.setText(tr("bulk-add-failed", n=len(failures)))
            box.setDetailedText("\n".join(failures))
            box.addButton(tr("btn-ok"), QMessageBox.ButtonRole.AcceptRole)
            box.exec()

        if not added_nids:
            return

        n = len(added_nids)
        tooltip(tr("bulk-add-added", n=n), parent=self.browser)

        # Reset the table — remove added editable rows, leave one blank
        for r in range(table.rowCount() - 1, table.first_editable_row - 1, -1):
            table.removeRow(r)
        table.add_row()

        # Search for the newly added notes in the browser
        nid_query = " OR ".join(f"nid:{nid}" for nid in added_nids)
        self.browser.search_for(nid_query)

        self.mw.reset()
        self.close()

    def closeEvent(self, evt):
        if not self.table_group.confirm_discard(tr("btn-close")):
            evt.ignore()
            return
        saveGeom(self, __name__)
        self.chooser.cleanup()

        from . import main as _main
        _main._dialog = None

        super().closeEvent(evt)

from __future__ import annotations

from typing import TYPE_CHECKING

from anki.decks import DeckId
from anki.models import NotetypeId
from aqt import AnkiQt
from aqt.qt import (
    QApplication,
    QMessageBox,
    Qt,
    qconnect,
)
from aqt.utils import tooltip

if TYPE_CHECKING:
    from aqt.browser import Browser

from ..chooser import Chooser
from ..i18n import tr
from .table import Table
from ..toggle import ToggleSwitch
from ..group import Group
from . import context as _ctx


class TableGroup(Group):
    """The Table group: icon toolbar + Table widget."""
    def __init__(self, toggle: ToggleSwitch, mw: AnkiQt, browser: Browser, chooser: Chooser) -> None:
        super().__init__(toggle)
        self.setObjectName("tableGroup")

        self.col = mw.col
        self.browser = browser
        self.chooser = chooser

        # ---- Icon toolbar (top row, right of toggle) ----
        self._copy_button = self._add_icon_button("clipboard-copy", tr("table-copy-tooltip"), self._on_copy)
        self._paste_button = self._add_icon_button("clipboard-plus", tr("table-paste-tooltip"), self._on_paste)
        self._add_icon_button("row-clear", tr("table-clear-tooltip"), self._on_clear)

        self._add_separator()

        self._undo_button = self._add_icon_button("undo", tr("table-undo-tooltip"), self._on_undo)
        self._redo_button = self._add_icon_button("redo", tr("table-redo-tooltip"), self._on_redo)
        self._undo_button.setEnabled(False)
        self._redo_button.setEnabled(False)

        self._add_separator()

        self._add_icon_button("row-insert", tr("table-row-insert-tooltip"), self._on_insert_row)
        self._add_icon_button("row-remove", tr("table-row-remove-tooltip"), self._on_remove_row)

        self._add_separator()

        self._add_icon_button("reload", tr("table-update-from-selection-tooltip"), self._on_update_from_selection)

        # Clipboard monitoring for paste button state
        self._update_paste_button()
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            qconnect(clipboard.dataChanged, self._update_paste_button)
            qconnect(self.destroyed, lambda: clipboard.dataChanged.disconnect(self._update_paste_button))

        # ---- Table ----
        layout = self.layout()
        self.table = Table(mw)
        self.table.undo_changed = self._update_undo_buttons
        layout.addWidget(self.table, stretch=1)

        # Context menu on table
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        qconnect(self.table.customContextMenuRequested, lambda pos: _ctx.show_context_menu(self.table, pos, self))

    @property
    def index(self) -> int:
        return 0

    @property
    def name(self) -> str:
        return tr("group-table")

    # ---- confirmation ----------------------------------------------------

    def confirm_discard(self, action_label: str, message: str | None = None) -> bool:
        """Show a confirmation dialog if editable rows have content.
        *action_label* is the text for the confirm button ('Close' or 'Update').
        *message* overrides the default dialog text.
        Returns True if the user confirms or there's nothing to lose."""
        if not self.table.has_editable_content:
            return True
        box = QMessageBox(self)
        box.setWindowTitle(tr("table-unsaved-title"))
        box.setText(message or tr("table-unsaved-body"))
        box.addButton(tr("btn-cancel"), QMessageBox.ButtonRole.RejectRole)
        confirm = box.addButton(action_label, QMessageBox.ButtonRole.AcceptRole)
        box.setDefaultButton(confirm)
        box.exec()
        return box.clickedButton() == confirm

    # ---- copy / paste / clear --------------------------------------------

    def _on_copy(self) -> None:
        _ctx.copy(self.table)

    def _on_paste(self) -> None:
        _ctx.paste(self.table)

    def _on_clear(self) -> None:
        _ctx.clear(self.table)

    def _update_paste_button(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        text = clipboard.text()
        self._paste_button.setEnabled(bool(text and text.strip()))

    # ---- undo / redo -----------------------------------------------------

    def _update_undo_buttons(self) -> None:
        self._undo_button.setEnabled(self.table.can_undo)
        self._redo_button.setEnabled(self.table.can_redo)

    def _on_undo(self) -> None:
        self.table.undo()
        self._update_undo_buttons()

    def _on_redo(self) -> None:
        self.table.redo()
        self._update_undo_buttons()

    # ---- row management --------------------------------------------------

    def _on_insert_row(self) -> None:
        table = self.table
        col = table.currentColumn()
        row = table.currentRow()
        if row < table.first_editable_row:
            insert_at = table.first_editable_row
        else:
            insert_at = row + 1
        if insert_at >= table.rowCount():
            last = table.rowCount() - 1
            if last >= table.first_editable_row and not table._row_has_content(last):
                table.setCurrentCell(last, col)
                return
        table.push_undo()
        table.insert_row(insert_at)
        table.setCurrentCell(insert_at, col)
        self._update_undo_buttons()

    def _on_remove_row(self) -> None:
        table = self.table
        row = table.currentRow()
        col = table.currentColumn()
        if row < table.first_editable_row:
            return
        table.push_undo()
        table.removeRow(row)
        if (table.rowCount() - table.first_editable_row) < 1:
            table.add_row()
        table.setCurrentCell(min(row, table.rowCount() - 1), col)
        self._update_undo_buttons()

    # ---- selection -------------------------------------------------------

    def load_from_selection(self) -> None:
        """Populate the table from the browser's current card selection.
        The 0th card determines the notetype; cards whose notes don't
        match that notetype are silently skipped.
        Appends one empty editable row at the end."""
        selected = list(self.browser.selected_cards())
        if not selected:
            # No selection — use the chooser's default notetype, enable
            # the notetype button so the user can pick one manually.
            self.table.notetype_id = self.chooser.notetype_id
            self.chooser.set_notetype_enabled(True)
            self.table.rebuild()
            self.table.add_row()
            return

        # Resolve the notetype from the first card
        first_card = self.col.get_card(selected[0])
        target_mid = first_card.note().mid

        # Update choosers to match — lock the notetype button since
        # the selection determines the notetype.
        self.chooser.notetype_id = NotetypeId(target_mid)
        self.chooser.deck_id = DeckId(first_card.did)
        self.chooser.set_notetype_enabled(False)

        # Rebuild columns for this notetype (clears existing rows)
        self.table.notetype_id = target_mid
        self.table.rebuild()

        # Collect unique notes that match the target notetype.
        seen_nids: set[int] = set()
        for cid in selected:
            card = self.col.get_card(cid)
            note = card.note()
            if note.mid != target_mid:
                continue
            if note.id in seen_nids:
                continue
            seen_nids.add(note.id)
            self.table.add_row(*(note.fields + [" ".join(note.tags)]), editable=False)

        # Mark where editable rows begin
        self.table.first_editable_row = self.table.rowCount()

        # Always end with one empty editable row
        self.table.add_row()

    def _on_update_from_selection(self) -> None:
        """Re-read the browser selection and repopulate the table.
        If the notetype changes, ask for confirmation first.
        If the notetype stays the same, preserve editable rows."""
        selected = list(self.browser.selected_cards())

        if not selected:
            # No selection — remove example rows, keep editable rows,
            # keep current notetype, enable notetype chooser.
            self.chooser.set_notetype_enabled(True)
            for r in range(self.table.first_editable_row - 1, -1, -1):
                self.table.removeRow(r)
            self.table.first_editable_row = 0

            tooltip(tr("table-updated-example-rows", name=self.table.current_notetype["name"]))
            return

        # Determine target notetype from selection
        target_mid = self.col.get_card(selected[0]).note().mid

        same_notetype = target_mid == self.chooser.notetype_id

        if same_notetype:
            # Preserve editable rows, just refresh the data rows
            editable_snapshot = self.table.snapshot()
            # Strip trailing empty rows from the snapshot
            sort_col = self.table.sort_col
            while editable_snapshot and not editable_snapshot[-1][sort_col].strip():
                editable_snapshot.pop()
            self.load_from_selection()
            # Restore editable rows on top of the new data rows
            # (remove the default empty row that load_from_selection added)
            for r in range(self.table.rowCount() - 1, self.table.first_editable_row - 1, -1):
                self.table.removeRow(r)
            for row_data in editable_snapshot:
                self.table.add_row(*row_data)
            # Ensure there's always a trailing empty row
            self.table.add_row()
        else:
            old_name = self.table.current_notetype["name"]
            new_nt = self.col.models.get(NotetypeId(target_mid))
            new_name = new_nt["name"] if new_nt else "Unknown"
            msg = tr("table-update-notetype-change", old=old_name, new=new_name)
            if not self.confirm_discard(tr("btn-confirm"), msg):
                return
            self.load_from_selection()

        tooltip(tr("table-updated-example-rows", name=self.table.current_notetype["name"]))

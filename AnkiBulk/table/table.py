from __future__ import annotations

from typing import Callable

from aqt import AnkiQt
from aqt.qt import (
    QAbstractItemDelegate,
    QAbstractItemView,
    QHeaderView,
    QKeyEvent,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    qconnect,
)

from ..config import AnkiBulkConfig
from ..i18n import tr
from .cell import TableCellDelegate
from .menu import TableMenu
from .undo import UndoStack

TAGS_COL_NAME = "Tags"


class Table(QTableWidget):
    """QTableWidget subclass that owns the table data model, column
    visibility, undo/redo, and key-event handling for editable rows."""

    def __init__(self, mw: AnkiQt) -> None:
        super().__init__()
        self.setObjectName("table")

        self.mw = mw
        self._notetype_id: int = 0

        self._first_editable_row = 0
        self._sort_col = 0

        self._undo = UndoStack[list[list[str]]]()
        self._editing_saved = False
        self.undo_changed: Callable | None = None

        # Visual setup
        self.setRowCount(0)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setItemDelegate(TableCellDelegate(self))

        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setHighlightSections(False)
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        qconnect(header.customContextMenuRequested, self._on_header_context_menu)
        qconnect(header.sectionDoubleClicked, self._resize_column_to_header)

    @property
    def first_editable_row(self) -> int:
        return self._first_editable_row

    @first_editable_row.setter
    def first_editable_row(self, value: int) -> None:
        self._first_editable_row = value

    @property
    def notetype_id(self) -> int:
        return self._notetype_id

    @notetype_id.setter
    def notetype_id(self, value: int) -> None:
        self._notetype_id = value

    @property
    def current_notetype(self):
        return self.mw.col.models.get(self._notetype_id)

    @property
    def sort_col(self) -> int:
        return self._sort_col

    @property
    def tags_col(self) -> int:
        return len(self.column_names) - 1

    @property
    def tags_col_name(self) -> str:
        """Return a unique name for the synthetic Tags column,
        avoiding collisions with notetype field names."""
        field_names = {f["name"] for f in self.current_notetype["flds"]}
        name = TAGS_COL_NAME
        while name in field_names:
            name = f"_{name}"
        return name

    @property
    def column_names(self) -> list[str]:
        """Return all table column names: notetype fields + Tags."""
        field_names = [f["name"] for f in self.current_notetype["flds"]]
        return field_names + [self.tags_col_name]

    @property
    def has_editable_content(self) -> bool:
        """Return True if any editable row has non-empty content."""
        for r in range(self.first_editable_row, self.rowCount()):
            for c in range(self.columnCount()):
                item = self.item(r, c)
                if item and item.text():
                    return True
        return False

    @property
    def visible_columns(self) -> list[tuple[int, str]]:
        """Return (col_index, column_name) for all visible columns."""
        columns = self.column_names
        return [(c, columns[c]) for c in range(len(columns)) if not self.isColumnHidden(c)]

    def rebuild(self) -> None:
        """Reset table columns and clear all rows."""
        nt = self.current_notetype
        if not nt:
            return

        columns = self.column_names
        self._sort_col = nt["sortf"]

        self.clear()
        self.setColumnCount(len(columns))
        self.setRowCount(0)
        headers = list(columns)
        headers[self._sort_col] += f" {tr('sort-field-suffix')}"
        self.setHorizontalHeaderLabels(headers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self._first_editable_row = 0
        self._undo.clear()

        hidden = AnkiBulkConfig.column_visibility.value.get(str(nt["id"]), [])
        for col, name in enumerate(self.column_names):
            hide = name in hidden and col != self.sort_col
            self._toggle_column(col, not hide, False)

    def insert_row(self, row: int, *args: str, editable: bool = True) -> int:
        """Insert a row at *row* with optional cell values.
        When *editable* is True every column is editable;
        when False every column is read-only.  Append by passing
        ``self.rowCount()`` as *row*."""
        self.insertRow(row)
        n = self.columnCount()
        for col in range(n):
            item = QTableWidgetItem(args[col] if col < len(args) else "")
            if not editable:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.setItem(row, col, item)
        return row

    def add_row(self, *args: str, editable: bool = True) -> int:
        return self.insert_row(self.rowCount(), *args, editable=editable)

    def from_yaml(self, text: str) -> bool:
        """Parse YAML *text* and replace editable rows.
        Returns True on success (including empty text), False if invalid."""
        import yaml

        # Empty text — just clear editable rows
        if not text.strip():
            self.push_undo()
            for r in range(self.rowCount() - 1, self.first_editable_row - 1, -1):
                self.removeRow(r)
            self.add_row()
            return True

        # Try parsing
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError:
            return False

        # Structural check
        if not isinstance(doc, list) or not all(isinstance(e, dict) for e in doc):
            return False

        visible_names = {name for _, name in self.visible_columns}

        for entry in doc:
            if set(entry.keys()) - visible_names:
                return False
            for val in entry.values():
                if val is not None and not isinstance(val, str):
                    return False

        # Valid — apply to table
        self.push_undo()

        # Remove existing editable rows
        for r in range(self.rowCount() - 1, self.first_editable_row - 1, -1):
            self.removeRow(r)

        # Add rows from YAML
        for entry in doc:
            values = [str(entry.get(col, "") or "") for col in self.column_names]
            self.add_row(*values)

        # Ensure at least one editable row
        if self.rowCount() <= self.first_editable_row:
            self.add_row()

        return True

    def to_yaml(self) -> tuple[str, str]:
        """Serialize table rows to two YAML strings: (existing, new).
        Only includes visible (checked) columns."""
        import yaml

        visible = self.visible_columns

        data_rows: list[dict[str, str]] = []
        editable_rows: list[dict[str, str]] = []

        for r in range(self.rowCount()):
            row_dict: dict[str, str] = {}
            for c, name in visible:
                item = self.item(r, c)
                row_dict[name] = item.text() if item else ""
            if r < self.first_editable_row:
                data_rows.append(row_dict)
            else:
                if any(v for v in row_dict.values()):
                    editable_rows.append(row_dict)

        dump = lambda rows: yaml.dump(
            rows, allow_unicode=True, default_flow_style=False,
            sort_keys=False, default_style="'",
        ) if rows else ""

        return dump(data_rows), dump(editable_rows)

    # ---- column visibility -----------------------------------------------

    def _on_header_context_menu(self, pos) -> None:
        """Show a context menu with checkboxes for each column.
        The menu stays open when toggling checkboxes."""
        menu = TableMenu(self, self.column_names, self.sort_col, self._toggle_column)
        menu.exec(self.horizontalHeader().mapToGlobal(pos))

    def _toggle_column(self, col: int, visible: bool, persist: bool = True) -> None:
        """Show or hide a table column, and maybe persist the choice."""
        nt = self.current_notetype
        if visible:
            self.showColumn(col)
        else:
            self.hideColumn(col)
        if persist and nt:
            columns = self.column_names
            col_vis = AnkiBulkConfig.column_visibility.value
            col_vis[str(nt["id"])] = [columns[c] for c in range(len(columns)) if self.isColumnHidden(c)]
            AnkiBulkConfig.column_visibility = col_vis

    def _resize_column_to_header(self, logical_index: int) -> None:
        """Double-click on header: resize column to fit header text."""
        header = self.horizontalHeader()
        fm = header.fontMetrics()
        text = self.horizontalHeaderItem(logical_index).text()
        text_width = fm.horizontalAdvance(text) + 24
        self.setColumnWidth(logical_index, text_width)

    # ---- undo helpers ----------------------------------------------------

    def snapshot(self) -> list[list[str]]:
        """Capture current editable rows as a list of row values."""
        n_cols = self.columnCount()
        rows: list[list[str]] = []
        for r in range(self.first_editable_row, self.rowCount()):
            row_data: list[str] = []
            for c in range(n_cols):
                item = self.item(r, c)
                row_data.append(item.text() if item else "")
            rows.append(row_data)
        return rows

    @property
    def can_undo(self) -> bool:
        return self._undo.can_undo

    @property
    def can_redo(self) -> bool:
        return self._undo.can_redo

    def push_undo(self) -> None:
        """Save current editable state onto the undo stack, clear redo."""
        self._undo.push(self.snapshot())
        self._notify_undo_changed()

    def _notify_undo_changed(self) -> None:
        if self.undo_changed is not None:
            self.undo_changed()

    def _do(self, f: Callable):
        snapshot = f(self.snapshot())
        if snapshot is not None:
            for r in range(self.rowCount() - 1, self.first_editable_row - 1, -1):
                self.removeRow(r)
            for row_data in snapshot:
                self.add_row(*row_data)
        self._notify_undo_changed()

    def undo(self) -> None:
        self._do(self._undo.undo)

    def redo(self) -> None:
        self._do(self._undo.redo)

    def edit(self, index, trigger=None, event=None):
        """Override to save undo state when cell editing begins."""
        if trigger is None:
            return super().edit(index)

        row = index.row()

        if not self._editing_saved and row >= self.first_editable_row:
            self.push_undo()
            self._editing_saved = True
        return super().edit(index, trigger, event)

    def closeEditor(self, editor, hint):
        """Reset editing flag when editor closes."""
        super().closeEditor(editor, hint)
        self._editing_saved = False

    def keyPressEvent(self, evt: QKeyEvent | None) -> None:
        if evt is None:
            return
        key = evt.key()
        row = self.currentRow()
        col = self.currentColumn()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Insert):
            if row >= self.first_editable_row:
                if self.state() == QAbstractItemView.State.EditingState:
                    editor = self.indexWidget(self.currentIndex())
                    if editor is not None:
                        delegate = self.itemDelegate()
                        delegate.commitData.emit(editor)
                        delegate.closeEditor.emit(editor, QAbstractItemDelegate.EndEditHint.NoHint)

                sort_col = self.sort_col
                item = self.item(row, sort_col)
                next_row = row + 1
                if next_row >= self.rowCount():
                    if item is not None and item.text():
                        self.push_undo()
                        self.add_row()
                        self.setCurrentCell(next_row, sort_col)
                    return
                self.setCurrentCell(next_row, sort_col)
                return

        if key == Qt.Key.Key_Delete:
            if row >= self.first_editable_row:
                self.push_undo()
                self.removeRow(row)
                if (self.rowCount() - self.first_editable_row) > 1:
                    self.setCurrentCell(min(row, self.rowCount() - 1), col)
                else:
                    self.add_row()
                    self.setCurrentCell(row, col)
                return

        if key == Qt.Key.Key_Backspace:
            if row >= self.first_editable_row:
                sort_item = self.item(row, self.sort_col)
                if sort_item and sort_item.text():
                    # Clear the sort field
                    self.push_undo()
                    sort_item.setText("")
                    return
                # Sort field already empty — delete the row
                if (self.rowCount() - self.first_editable_row) > 1:
                    self.push_undo()
                    self.removeRow(row)
                    self.setCurrentCell(min(row, self.rowCount() - 1), col)
                    return

        super().keyPressEvent(evt)

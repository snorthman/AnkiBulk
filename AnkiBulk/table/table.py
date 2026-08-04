from __future__ import annotations

from typing import Callable

from aqt import AnkiQt
from aqt.qt import (
    QAbstractItemDelegate,
    QAbstractItemView,
    QEvent,
    QHeaderView,
    QKeyEvent,
    QTableWidget,
    QTableWidgetItem,
    QTimer,
    Qt,
    qconnect,
)

from ..config import AnkiBulkConfig
from ..i18n import tr
from .cell import TableCellDelegate
from . import context as _ctx
from . import yaml as _yaml
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
        self._pending_snapshot: list[list[str]] | None = None
        self.undo_changed: Callable | None = None
        self._selection_anchor: tuple[int, int] = (0, 0)

        # Visual setup
        self.setRowCount(0)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setItemDelegate(TableCellDelegate(self))

        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setHighlightSections(False)
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        qconnect(header.customContextMenuRequested, self._on_header_context_menu)
        qconnect(header.sectionDoubleClicked, self._resize_column_to_header)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        qconnect(self.customContextMenuRequested, lambda pos: _ctx.show_context_menu(self, pos))

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

    @property
    def anchor(self) -> tuple[int, int]:
        if len(self.selectedIndexes()) <= 1:
            return (self.currentRow(), self.currentColumn())
        return self._selection_anchor

    def mousePressEvent(self, event):
        if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            index = self.indexAt(event.pos())
            if index.isValid():
                self._selection_anchor = (index.row(), index.column())
        super().mousePressEvent(event)

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
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

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
        return _yaml.from_yaml(self, text)

    def to_yaml(self) -> tuple[str, str]:
        return _yaml.to_yaml(self)

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
        row, col = self.currentRow(), self.currentColumn()
        snapshot = f(self.snapshot())
        if snapshot is not None:
            for r in range(self.rowCount() - 1, self.first_editable_row - 1, -1):
                self.removeRow(r)
            for row_data in snapshot:
                self.add_row(*row_data)
        self._notify_undo_changed()
        self.setCurrentCell(min(row, self.rowCount() - 1), col)

    def undo(self) -> None:
        self._do(self._undo.undo)

    def redo(self) -> None:
        self._do(self._undo.redo)

    def edit(self, index, trigger=None, event=None):
        """Override to capture a pending snapshot when cell editing begins.
        The snapshot is only pushed to the undo stack if data changes."""
        if trigger is None:
            result = super().edit(index)
        else:
            row = index.row()
            if not self._editing_saved and row >= self.first_editable_row:
                self._pending_snapshot = self.snapshot()
                self._editing_saved = True
            result = super().edit(index, trigger, event)

        editor = self.indexWidget(index)
        if editor is not None:
            editor.installEventFilter(self)

        return result

    def closeEditor(self, editor, hint):
        super().closeEditor(editor, hint)
        if self._editing_saved and self._pending_snapshot is not None:
            if self.snapshot() != self._pending_snapshot:
                self._undo.push(self._pending_snapshot)
                self._notify_undo_changed()
            self._pending_snapshot = None
        self._editing_saved = False

    def _visible_cols(self) -> list[int]:
        return [c for c in range(self.columnCount()) if not self.isColumnHidden(c)]

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.Type.KeyPress
                and isinstance(event, QKeyEvent)
                and self.state() == QAbstractItemView.State.EditingState
                and hasattr(obj, 'cursorPosition') and hasattr(obj, 'text')):
            key = event.key()
            move = None
            if key == Qt.Key.Key_Left and obj.cursorPosition() == 0:
                move = -1
            elif key == Qt.Key.Key_Right and obj.cursorPosition() == len(obj.text()):
                move = 1
            if move is not None:
                delegate = self.itemDelegate()
                delegate.commitData.emit(obj)
                delegate.closeEditor.emit(obj, QAbstractItemDelegate.EndEditHint.NoHint)
                row, col = self.currentRow(), self.currentColumn()
                visible = self._visible_cols()
                target_cell = None
                if visible:
                    try:
                        idx = visible.index(col)
                    except ValueError:
                        idx = 0
                    t = idx + move
                    if 0 <= t < len(visible):
                        target_cell = (row, visible[t])
                    elif move == -1 and row - 1 >= 0:
                        target_cell = (row - 1, visible[-1])
                    elif move == 1 and row + 1 < self.rowCount():
                        target_cell = (row + 1, visible[0])
                if target_cell is not None:
                    r, c = target_cell
                    QTimer.singleShot(0, lambda r=r, c=c: self.setCurrentCell(r, c))
                return True
        return super().eventFilter(obj, event)

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

                next_row = row + 1
                if next_row >= self.rowCount():
                    if any(self.item(row, c) and self.item(row, c).text() for c in range(self.columnCount())):
                        self.push_undo()
                        self.add_row()
                        self.setCurrentCell(next_row, col)
                    return
                self.setCurrentCell(next_row, col)
                return

        if key == Qt.Key.Key_Delete:
            _ctx.clear(self)
            indexes = self.selectedIndexes()
            rows = set(idx.row() for idx in indexes)
            if len(rows) == 1:
                r = next(iter(rows))
                if (r >= self.first_editable_row
                        and self.rowCount() - self.first_editable_row > 1
                        and all(not (self.item(r, c) and self.item(r, c).text()) for c in range(self.columnCount()))):
                    self.removeRow(r)
                    self.setCurrentCell(min(r, self.rowCount() - 1), col)
            return

        if key == Qt.Key.Key_Backspace:
            r, c = self.anchor
            if r >= self.first_editable_row:
                item = self.item(r, c)
                if item and item.flags() & Qt.ItemFlag.ItemIsEditable:
                    self.push_undo()
                    item.setText("")
                    self.setCurrentCell(r, c)
                    self.editItem(item)
            return

        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            if self.state() == QAbstractItemView.State.EditingState:
                editor = self.indexWidget(self.currentIndex())
                if editor is not None:
                    delegate = self.itemDelegate()
                    delegate.commitData.emit(editor)
                    delegate.closeEditor.emit(editor, QAbstractItemDelegate.EndEditHint.NoHint)
            visible = self._visible_cols()
            if visible:
                try:
                    idx = visible.index(col)
                except ValueError:
                    idx = 0
                if key == Qt.Key.Key_Tab:
                    if idx + 1 < len(visible):
                        self.setCurrentCell(row, visible[idx + 1])
                    elif row + 1 < self.rowCount():
                        self.setCurrentCell(row + 1, visible[0])
                else:
                    if idx - 1 >= 0:
                        self.setCurrentCell(row, visible[idx - 1])
                    elif row - 1 >= 0:
                        self.setCurrentCell(row - 1, visible[-1])
            return

        super().keyPressEvent(evt)

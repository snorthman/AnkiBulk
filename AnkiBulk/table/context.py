from __future__ import annotations

from typing import TYPE_CHECKING

from aqt.qt import QApplication, QMenu, Qt

from ..i18n import tr

if TYPE_CHECKING:
    from .table import Table


def show_context_menu(table: Table, pos) -> None:
    menu = QMenu(table)

    copy_action = menu.addAction(tr("context-copy"))
    paste_action = menu.addAction(tr("context-paste"))
    clear_action = menu.addAction(tr("context-clear"))

    selected = table.selectedIndexes()
    has_selection = bool(selected)
    has_editable = any(idx.row() >= table.first_editable_row for idx in selected)

    copy_action.setEnabled(has_selection)
    clear_action.setEnabled(has_editable)

    clipboard = QApplication.clipboard()
    clipboard_text = clipboard.text() if clipboard else ""
    paste_action.setEnabled(
        bool(clipboard_text and clipboard_text.strip())
        and table.currentRow() >= table.first_editable_row
    )

    action = menu.exec(table.mapToGlobal(pos))
    if action == copy_action:
        copy(table)
    elif action == paste_action:
        paste(table)
    elif action == clear_action:
        clear(table)


def copy(table: Table) -> None:
    indexes = table.selectedIndexes()
    if not indexes:
        return
    rows = sorted(set(idx.row() for idx in indexes))
    cols = sorted(set(idx.column() for idx in indexes))
    selected_set = {(idx.row(), idx.column()) for idx in indexes}

    lines: list[str] = []
    for r in rows:
        cells: list[str] = []
        for c in cols:
            if (r, c) in selected_set:
                item = table.item(r, c)
                cells.append(item.text() if item else "")
            else:
                cells.append("")
        lines.append("\t".join(cells))

    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText("\n".join(lines))


def paste(table: Table) -> None:
    clipboard = QApplication.clipboard()
    if clipboard is None:
        return
    text = clipboard.text()
    if not text or not text.strip():
        return

    grid = [line.split("\t") for line in text.split("\n") if line]
    if not grid:
        return

    selected = table.selectedIndexes()
    if selected:
        start_row = min(idx.row() for idx in selected)
        start_col = min(idx.column() for idx in selected)
    else:
        start_row = table.currentRow()
        start_col = table.currentColumn()

    if start_row < table.first_editable_row:
        start_row = table.first_editable_row

    visible = [c for c in range(table.columnCount()) if not table.isColumnHidden(c)]

    try:
        col_offset = visible.index(start_col)
    except ValueError:
        col_offset = 0

    table.push_undo()
    end_row = start_row
    end_col = start_col
    for dr, row_data in enumerate(grid):
        r = start_row + dr
        while r >= table.rowCount():
            table.add_row()
        if r < table.first_editable_row:
            continue
        for dc, value in enumerate(row_data):
            vi = col_offset + dc
            if vi >= len(visible):
                break
            c = visible[vi]
            item = table.item(r, c)
            if item and item.flags() & Qt.ItemFlag.ItemIsEditable:
                item.setText(value)
                end_row = r
                end_col = c

    table.clearSelection()
    for dr, row_data in enumerate(grid):
        r = start_row + dr
        if r < table.first_editable_row or r >= table.rowCount():
            continue
        for dc in range(len(row_data)):
            vi = col_offset + dc
            if vi >= len(visible):
                break
            c = visible[vi]
            table.selectionModel().select(
                table.model().index(r, c),
                table.selectionModel().SelectionFlag.Select,
            )
    table.setCurrentCell(end_row, end_col)


def clear(table: Table) -> None:
    indexes = [idx for idx in table.selectedIndexes() if idx.row() >= table.first_editable_row]
    if not indexes:
        return
    table.push_undo()
    for idx in indexes:
        item = table.item(idx.row(), idx.column())
        if item and item.flags() & Qt.ItemFlag.ItemIsEditable:
            item.setText("")

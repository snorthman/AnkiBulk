from __future__ import annotations

from typing import TYPE_CHECKING

from aqt.qt import QApplication, QMenu, Qt

from ..i18n import tr

if TYPE_CHECKING:
    from .group import TableGroup
    from .table import Table


def show_context_menu(table: Table, pos, group: TableGroup | None = None) -> None:
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

    undo_action = redo_action = None
    insert_action = delete_action = update_action = None

    if group is not None:
        menu.addSeparator()
        undo_action = menu.addAction(tr("context-undo"))
        redo_action = menu.addAction(tr("context-redo"))
        undo_action.setEnabled(table.can_undo)
        redo_action.setEnabled(table.can_redo)

        menu.addSeparator()
        insert_action = menu.addAction(tr("context-insert-row"))
        delete_action = menu.addAction(tr("context-delete-row"))
        delete_action.setEnabled(table.currentRow() >= table.first_editable_row)

        menu.addSeparator()
        update_action = menu.addAction(tr("context-update-selection"))

    action = menu.exec(table.mapToGlobal(pos))
    if action is None:
        return
    if action == copy_action:
        copy(table)
    elif action == paste_action:
        paste(table)
    elif action == clear_action:
        clear(table)
    elif action == undo_action:
        group._on_undo()
    elif action == redo_action:
        group._on_redo()
    elif action == insert_action:
        group._on_insert_row()
    elif action == delete_action:
        group._on_remove_row()
    elif action == update_action:
        group._on_update_from_selection()


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
    has_content = any(
        (item := table.item(idx.row(), idx.column())) is not None
        and item.flags() & Qt.ItemFlag.ItemIsEditable
        and item.text()
        for idx in indexes
    )
    if not has_content:
        return
    table.push_undo()
    for idx in indexes:
        item = table.item(idx.row(), idx.column())
        if item and item.flags() & Qt.ItemFlag.ItemIsEditable:
            item.setText("")

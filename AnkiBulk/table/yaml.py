from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from .table import Table


def from_yaml(table: Table, text: str) -> bool:
    """Parse YAML *text* and replace editable rows.
    Returns True on success (including empty text), False if invalid."""
    if not text.strip():
        table.push_undo()
        for r in range(table.rowCount() - 1, table.first_editable_row - 1, -1):
            table.removeRow(r)
        table.add_row()
        return True

    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        return False

    if not isinstance(doc, list) or not all(isinstance(e, dict) for e in doc):
        return False

    visible_names = {name for _, name in table.visible_columns}

    for entry in doc:
        if set(entry.keys()) - visible_names:
            return False
        for val in entry.values():
            if val is not None and not isinstance(val, str):
                return False

    table.push_undo()

    for r in range(table.rowCount() - 1, table.first_editable_row - 1, -1):
        table.removeRow(r)

    for entry in doc:
        values = [str(entry.get(col, "") or "") for col in table.column_names]
        table.add_row(*values)

    if table.rowCount() <= table.first_editable_row:
        table.add_row()

    return True


def to_yaml(table: Table) -> tuple[str, str]:
    """Serialize table rows to two YAML strings: (existing, new).
    Only includes visible (checked) columns."""
    visible = table.visible_columns

    data_rows: list[dict[str, str]] = []
    editable_rows: list[dict[str, str]] = []

    for r in range(table.rowCount()):
        row_dict: dict[str, str] = {}
        for c, name in visible:
            item = table.item(r, c)
            row_dict[name] = item.text() if item else ""
        if r < table.first_editable_row:
            data_rows.append(row_dict)
        else:
            if any(v for v in row_dict.values()):
                editable_rows.append(row_dict)

    dump = lambda rows: yaml.dump(
        rows, allow_unicode=True, default_flow_style=False,
        sort_keys=False, default_style="'",
    ) if rows else ""

    return dump(data_rows), dump(editable_rows)

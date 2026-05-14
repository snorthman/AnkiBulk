from __future__ import annotations

from aqt.qt import (
    QApplication,
    QDialog,
    QLabel,
    QPlainTextEdit,
    Qt,
    qconnect,
)
from aqt.utils import tooltip

from AnkiBulk.group import Group
from AnkiBulk.i18n import tr
from AnkiBulk.table import Table
from AnkiBulk.text.linter import Linter
from AnkiBulk.toggle import ToggleSwitch


class TextGroup(Group):
    def __init__(self, toggle: ToggleSwitch, table: Table) -> None:
        super().__init__(toggle)
        self.setObjectName("textGroup")
        self.table = table

        # ---- Icon toolbar (top row, right of toggle) ----
        self._add_icon_button("undo", tr("text-undo-tooltip"), self._on_undo)
        self._add_icon_button("redo", tr("text-redo-tooltip"), self._on_redo)

        self._add_separator()

        self._add_icon_button("clipboard-copy", tr("text-copy-to-clipboard-tooltip"), self._on_copy_to_clipboard)
        self._add_icon_button("clipboard-settings", tr("text-options-tooltip"), self._on_options)

        layout = self.layout()

        # ---- Existing notes (read-only) ----
        self.text_examples = QPlainTextEdit()
        self.text_examples.setObjectName("textExamples")
        self.text_examples.setPlaceholderText(tr("text-examples-placeholder"))
        self.text_examples.setReadOnly(True)
        layout.addWidget(self.text_examples, stretch=1)

        # ---- New notes (editable) ----
        self.text_editables = QPlainTextEdit()
        self.text_editables.setObjectName("textEditables")
        self.text_editables.setPlaceholderText(tr("text-editables-placeholder"))
        layout.addWidget(self.text_editables, stretch=1)

        # ---- Status label ----
        self.text_status = QLabel()
        self.text_status.setObjectName("textStatus")
        self.text_status.setWordWrap(True)
        self.text_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.text_status)

        # ---- Debounced YAML validation ----
        self.linter = Linter(self.text_editables, self.text_status, table)
        qconnect(self.text_editables.textChanged, self.linter.schedule)

    @property
    def index(self) -> int:
        return 1

    @property
    def name(self) -> str:
        return tr("group-text")

    # ---- public API ------------------------------------------------------

    def populate(self, existing_yaml: str, new_yaml: str) -> None:
        """Set the text of both editors and clear the undo history."""
        self.text_examples.setPlainText(existing_yaml)
        self.text_editables.setPlainText(new_yaml)
        self.text_editables.document().clearUndoRedoStacks()

    def examples_as_text(self) -> str:
        """Return the existing (read-only) YAML text."""
        return self.text_examples.toPlainText()

    def editables_as_text(self) -> str:
        """Return the editable YAML text."""
        return self.text_editables.toPlainText()

    # ---- undo/redo -------------------------------------------------------

    def _on_undo(self) -> None:
        self.text_editables.undo()

    def _on_redo(self) -> None:
        self.text_editables.redo()

    # ---- options dialog --------------------------------------------------

    def _on_options(self) -> None:
        """Show options dialog for the Raw tab, with per-notetype presets."""
        from .options import Dialog

        dlg = Dialog(self, self.table.notetype_id, self.table.mw.col)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.save_presets()

    # ---- copy to clipboard -----------------------------------------------

    def _on_copy_to_clipboard(self) -> None:
        """Copy table content to clipboard, respecting preset options."""
        import csv
        import io
        import json
        import xml.etree.ElementTree as ET

        import yaml
        from AnkiBulk.config import AnkiBulkConfig

        preset = AnkiBulkConfig.get_preset(self.table.notetype_id)

        # Gather data from the YAML text boxes
        existing_text = self.text_examples.toPlainText().strip()
        new_text = self.text_editables.toPlainText().strip()

        existing_data: list[dict] = []
        new_data: list[dict] = []
        try:
            if existing_text and preset.include_examples:
                existing_data = yaml.safe_load(existing_text) or []
            if new_text:
                new_data = yaml.safe_load(new_text) or []
        except yaml.YAMLError:
            tooltip(tr("text-copy-yaml-error", format=preset.copy_format))
            return

        # Validate structure: must be list[dict]
        for data in (existing_data, new_data):
            if not isinstance(data, list) or any(not isinstance(e, dict) for e in data):
                tooltip(tr("text-copy-yaml-error", format=preset.copy_format))
                return

        # Apply mark examples tag (only when tags column is visible)
        tags_visible = not self.table.isColumnHidden(self.table.tags_col)
        if preset.include_examples and preset.mark_examples and existing_data and tags_visible:
            mark_tag = preset.mark_tag or tr("options-mark-tag-placeholder")
            tags_col_name = self.table.tags_col_name
            for entry in existing_data:
                if tags_col_name in entry:
                    existing_tags = entry[tags_col_name].strip()
                    if existing_tags:
                        entry[tags_col_name] = f"{existing_tags} {mark_tag}"
                    else:
                        entry[tags_col_name] = mark_tag
                else:
                    entry[tags_col_name] = mark_tag

        all_data = existing_data + new_data

        # Convert to the chosen format
        fmt = preset.copy_format
        match fmt:
            case 'JSON':
                output = json.dumps(all_data, ensure_ascii=False, indent=2)
            case 'XML':
                root = ET.Element("notes")
                for row in all_data:
                    note_el = ET.SubElement(root, "note")
                    for key, val in row.items():
                        field_el = ET.SubElement(note_el, "field", name=key)
                        field_el.text = str(val) if val else ""
                ET.indent(root)
                output = ET.tostring(root, encoding="unicode", xml_declaration=True)
            case 'CSV' | 'TSV':
                delimiter = "\t" if fmt == "TSV" else ","
                buf = io.StringIO()
                headers = list(all_data[0].keys()) if all_data else []
                writer = csv.writer(buf, delimiter=delimiter)
                writer.writerow(headers)
                for row in all_data:
                    writer.writerow(row.get(h, "") for h in headers)
                output = buf.getvalue().strip()
            case 'YAML':
                output = yaml.dump(
                    all_data, allow_unicode=True,
                    default_flow_style=False, sort_keys=False,
                    default_style="'",
                ) if all_data else ""
            case _:
                raise NotImplementedError(f'Unknown format: {fmt}')

        # Append additional text
        if preset.additional_text.strip():
            output = output + "\n\n" + preset.additional_text.strip()

        clipboard = QApplication.clipboard()
        if clipboard is None:
            return

        clipboard.setText(output)
        tooltip(tr("text-copied"))

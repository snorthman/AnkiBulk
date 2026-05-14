from __future__ import annotations

from copy import deepcopy

from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    qconnect,
)

from aqt.utils import tooltip

from ..config import AnkiBulkConfig, Preset
from ..i18n import tr


class Dialog(QDialog):
    """Per-notetype preset options for the Raw tab."""

    def __init__(self, parent: QWidget, current_notetype_id: int, col) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("options-title"))
        self.setMinimumWidth(400)

        self._current_note_id = current_notetype_id
        self._col = col

        # Gather all notetypes for the preset dropdown
        self._all_notetypes: list[tuple[int, str]] = [(nt["id"], nt["name"]) for nt in col.models.all()]
        self._all_notetypes.sort(key=lambda x: x[1].lower())

        # Clone presets so changes are only saved on OK
        self._draft_presets: dict[int, Preset] = {}
        for note_id, _ in self._all_notetypes:
            self._draft_presets[note_id] = deepcopy(AnkiBulkConfig.get_preset(note_id))

        self._prev_note_id = current_notetype_id
        self._build_ui()
        self._load_preset(current_notetype_id)

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        self.setLayout(layout)

        # --- Preset selector ---
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel(tr("options-preset")))
        self._preset_combo = QComboBox()
        for note_id, name in self._all_notetypes:
            self._preset_combo.addItem(name, note_id)
        for i, (note_id, _) in enumerate(self._all_notetypes):
            if note_id == self._current_note_id:
                self._preset_combo.setCurrentIndex(i)
                break
        preset_row.addWidget(self._preset_combo, stretch=1)
        layout.addLayout(preset_row)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # --- Copy format ---
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel(tr("options-copy-as")))
        self._format_combo = QComboBox()
        for fmt in Preset.FORMATS:
            self._format_combo.addItem(fmt, fmt)
        format_row.addWidget(self._format_combo, stretch=1)
        qconnect(self._format_combo.currentIndexChanged, self._on_format_changed)
        layout.addLayout(format_row)

        # --- Checkboxes ---
        self._include_cb = QCheckBox(tr("options-include-examples"))
        layout.addWidget(self._include_cb)

        mark_row = QHBoxLayout()
        self._mark_cb = QCheckBox(tr("options-mark-examples"))
        mark_row.addWidget(self._mark_cb)
        self._mark_tag_edit = QLineEdit()
        self._mark_tag_edit.setPlaceholderText(tr("options-mark-tag-placeholder"))
        mark_row.addWidget(self._mark_tag_edit, stretch=1)
        layout.addLayout(mark_row)

        qconnect(self._include_cb.toggled, self._on_include_changed)
        qconnect(self._mark_cb.toggled, self._on_mark_changed)

        # --- Additional text ---
        layout.addWidget(QLabel(tr("options-additional-text")))
        self._additional_edit = QPlainTextEdit()
        self._additional_edit.setPlaceholderText(tr("options-additional-text-placeholder"))
        self._additional_edit.setMinimumHeight(100)
        layout.addWidget(self._additional_edit, stretch=1)

        qconnect(self._preset_combo.currentIndexChanged, self._on_preset_changed)

        # --- Buttons ---
        button_row = QHBoxLayout()
        button_row.addStretch()

        ok_button = QPushButton(tr("btn-ok"))
        ok_button.setAutoDefault(True)
        qconnect(ok_button.clicked, self.accept)
        button_row.addWidget(ok_button)

        cancel_button = QPushButton(tr("btn-cancel"))
        cancel_button.setAutoDefault(False)
        qconnect(cancel_button.clicked, self.reject)
        button_row.addWidget(cancel_button)

        layout.addLayout(button_row)

    def _on_format_changed(self, index: int) -> None:
        fmt = self._format_combo.currentData()
        if fmt != "YAML":
            tooltip(tr("options-non-yaml-warning"), period=8000, parent=self)

    def _on_include_changed(self, checked: bool) -> None:
        self._mark_cb.setEnabled(checked)
        self._mark_tag_edit.setEnabled(checked and self._mark_cb.isChecked())

    def _on_mark_changed(self, checked: bool) -> None:
        self._mark_tag_edit.setEnabled(checked)

    def _save_form_to_draft(self, note_id: int | None = None) -> None:
        target = note_id if note_id is not None else self._prev_note_id
        self._draft_presets[target] = Preset(
            copy_format=self._format_combo.currentData(),
            include_examples=self._include_cb.isChecked(),
            mark_examples=self._mark_cb.isChecked(),
            mark_tag=self._mark_tag_edit.text() or tr("options-mark-tag-placeholder"),
            additional_text=self._additional_edit.toPlainText(),
        )

    def _load_preset(self, note_id: int) -> None:
        p = self._draft_presets[note_id]
        idx = Preset.FORMATS.index(p.copy_format) if p.copy_format in Preset.FORMATS else 0
        self._format_combo.setCurrentIndex(idx)
        self._include_cb.setChecked(p.include_examples)
        self._mark_cb.setChecked(p.mark_examples)
        self._mark_tag_edit.setText(p.mark_tag)
        self._additional_edit.setPlainText(p.additional_text)
        self._on_include_changed(p.include_examples)

    def _on_preset_changed(self, index: int) -> None:
        self._save_form_to_draft(self._prev_note_id)
        new_note_id = self._preset_combo.itemData(index)
        self._load_preset(new_note_id)
        self._prev_note_id = new_note_id

    def save_presets(self) -> None:
        """Save the current form state and persist all draft presets."""
        self._save_form_to_draft()
        for note_id, preset in self._draft_presets.items():
            AnkiBulkConfig.save_preset(note_id, preset)
